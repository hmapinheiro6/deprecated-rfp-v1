"""
API-based RFP scraper - replaces web scraping with official APIs
This is much more reliable and performant than BeautifulSoup scraping
"""

import os
import sys
import time
import json
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from config import KEYWORDS
from utils import (
    logger,
    load_seen_rfps,
    save_seen_rfps,
    filter_new_rfps,
    is_relevant,
    create_rfp_dict,
)

# API Configuration
SAM_GOV_API_URL = "https://api.sam.gov/opportunities/v2/search"
SAM_GOV_API_KEY = os.environ.get('SAM_GOV_API_KEY', '')  # Optional but recommended

UNDP_API_URL = "https://procurement-notices.undp.org/api/notices"

# Request settings
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2


def scrape_sam_gov_api() -> List[Dict]:
    """
    Scrape SAM.gov using the official Opportunities API
    API Docs: https://open.gsa.gov/api/opportunities-api/

    Returns:
        List of RFP dictionaries
    """
    source_name = "SAM.gov"
    logger.info(f"Scraping {source_name} via API...")
    rfps = []

    try:
        # Build search query
        # Search for opportunities posted in last 30 days
        posted_from = (datetime.utcnow() - timedelta(days=30)).strftime('%m/%d/%Y')

        params = {
            'postedFrom': posted_from,
            'ptype': 'o',  # Opportunities (not awards)
            'limit': 100,   # Max results per request
        }

        headers = {
            'Accept': 'application/json',
            'User-Agent': 'RFP-Scraper-Sword-Health/1.0'
        }

        # Add API key if available (not required but increases rate limits)
        if SAM_GOV_API_KEY:
            headers['X-Api-Key'] = SAM_GOV_API_KEY
            logger.debug("Using SAM.gov API key")

        logger.debug(f"API Request: {SAM_GOV_API_URL}")
        logger.debug(f"Params: {params}")

        response = requests.get(
            SAM_GOV_API_URL,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )

        logger.info(f"SAM.gov API response status: {response.status_code}")

        if response.status_code == 401:
            logger.warning("SAM.gov API returned 401. API key may be invalid or required.")
            logger.warning("Get a free API key at: https://open.gsa.gov/api/opportunities-api/")
            return rfps

        response.raise_for_status()

        data = response.json()

        # Parse opportunities
        opportunities = data.get('opportunitiesData', [])
        logger.info(f"SAM.gov API returned {len(opportunities)} opportunities")

        for opp in opportunities:
            try:
                title = opp.get('title', '')
                description = opp.get('description', '')

                # Check relevance
                combined_text = f"{title} {description}"
                if not is_relevant(combined_text):
                    continue

                # Extract details
                notice_id = opp.get('noticeId', '')
                url = f"https://sam.gov/opp/{notice_id}/view" if notice_id else ""

                publish_date = opp.get('postedDate', 'N/A')
                deadline = opp.get('responseDeadLine', 'N/A')

                # Create snippet from description
                snippet = description[:300] if description else ""

                rfp = create_rfp_dict(
                    title=title,
                    url=url,
                    source=source_name,
                    publish_date=publish_date,
                    deadline=deadline,
                    snippet=snippet
                )
                rfps.append(rfp)
                logger.info(f"Found relevant RFP: {title[:50]}...")

            except Exception as e:
                logger.debug(f"Error parsing SAM.gov opportunity: {e}")
                continue

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP error scraping {source_name}: {e}")
    except Exception as e:
        logger.error(f"Error scraping {source_name}: {e}")

    logger.info(f"Found {len(rfps)} relevant RFPs from {source_name}")
    return rfps


def scrape_undp_api() -> List[Dict]:
    """
    Scrape UNDP using their procurement notices API

    Returns:
        List of RFP dictionaries
    """
    source_name = "UNDP Procurement"
    logger.info(f"Scraping {source_name} via API...")
    rfps = []

    try:
        params = {
            'limit': 100,
            'offset': 0,
            'sort': '-published_date'
        }

        headers = {
            'Accept': 'application/json',
            'User-Agent': 'RFP-Scraper-Sword-Health/1.0'
        }

        logger.debug(f"API Request: {UNDP_API_URL}")

        response = requests.get(
            UNDP_API_URL,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )

        logger.info(f"UNDP API response status: {response.status_code}")
        response.raise_for_status()

        data = response.json()

        # Parse notices
        notices = data.get('results', []) if isinstance(data, dict) else data
        logger.info(f"UNDP API returned {len(notices)} notices")

        for notice in notices:
            try:
                title = notice.get('title', '') or notice.get('notice_title', '')
                description = notice.get('description', '') or notice.get('summary', '')

                # Check relevance
                combined_text = f"{title} {description}"
                if not is_relevant(combined_text):
                    continue

                # Extract details
                notice_id = notice.get('id', '') or notice.get('notice_id', '')
                url = f"https://procurement-notices.undp.org/view_notice.cfm?notice_id={notice_id}" if notice_id else ""

                publish_date = notice.get('published_date', 'N/A')
                deadline = notice.get('deadline', 'N/A') or notice.get('submission_date', 'N/A')

                snippet = description[:300] if description else ""

                rfp = create_rfp_dict(
                    title=title,
                    url=url,
                    source=source_name,
                    publish_date=publish_date,
                    deadline=deadline,
                    snippet=snippet
                )
                rfps.append(rfp)
                logger.info(f"Found relevant RFP: {title[:50]}...")

            except Exception as e:
                logger.debug(f"Error parsing UNDP notice: {e}")
                continue

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP error scraping {source_name}: {e}")
    except Exception as e:
        logger.error(f"Error scraping {source_name}: {e}")

    logger.info(f"Found {len(rfps)} relevant RFPs from {source_name}")
    return rfps


def scrape_ungm_api() -> List[Dict]:
    """
    Scrape UNGM using their public notices endpoint

    Returns:
        List of RFP dictionaries
    """
    source_name = "UNGM"
    logger.info(f"Scraping {source_name} via API...")
    rfps = []

    try:
        # UNGM has a public data API
        api_url = "https://www.ungm.org/Public/Notice/Search"

        params = {
            'Page': 1,
            'PageSize': 50,
            'SortField': 'PUBLISHED_DATE',
            'SortOrder': 'DESC'
        }

        headers = {
            'Accept': 'application/json',
            'User-Agent': 'RFP-Scraper-Sword-Health/1.0'
        }

        logger.debug(f"API Request: {api_url}")

        response = requests.post(  # UNGM uses POST for search
            api_url,
            json=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )

        logger.info(f"UNGM API response status: {response.status_code}")

        if response.status_code != 200:
            logger.warning(f"UNGM API returned non-200 status. May need different approach.")
            return rfps

        data = response.json()

        # Parse notices
        notices = data.get('Notices', []) if isinstance(data, dict) else []
        logger.info(f"UNGM API returned {len(notices)} notices")

        for notice in notices:
            try:
                title = notice.get('Title', '')
                description = notice.get('Description', '') or notice.get('Subject', '')

                # Check relevance
                combined_text = f"{title} {description}"
                if not is_relevant(combined_text):
                    continue

                # Extract details
                notice_id = notice.get('ReferenceNumber', '') or notice.get('NoticeId', '')
                url = f"https://www.ungm.org/Public/Notice/{notice_id}" if notice_id else ""

                publish_date = notice.get('PublishedDate', 'N/A')
                deadline = notice.get('SubmissionDeadline', 'N/A') or notice.get('Deadline', 'N/A')

                snippet = description[:300] if description else ""

                rfp = create_rfp_dict(
                    title=title,
                    url=url,
                    source=source_name,
                    publish_date=publish_date,
                    deadline=deadline,
                    snippet=snippet
                )
                rfps.append(rfp)
                logger.info(f"Found relevant RFP: {title[:50]}...")

            except Exception as e:
                logger.debug(f"Error parsing UNGM notice: {e}")
                continue

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP error scraping {source_name}: {e}")
    except Exception as e:
        logger.error(f"Error scraping {source_name}: {e}")

    logger.info(f"Found {len(rfps)} relevant RFPs from {source_name}")
    return rfps


def scrape_all_sources_api() -> List[Dict]:
    """
    Scrape all sources using their APIs

    Returns:
        Combined list of all RFPs from all sources
    """
    all_rfps = []

    # SAM.gov API
    try:
        rfps = scrape_sam_gov_api()
        all_rfps.extend(rfps)
    except Exception as e:
        logger.error(f"Critical error in SAM.gov API scraper: {e}")

    # UNDP API
    try:
        rfps = scrape_undp_api()
        all_rfps.extend(rfps)
    except Exception as e:
        logger.error(f"Critical error in UNDP API scraper: {e}")

    # UNGM API
    try:
        rfps = scrape_ungm_api()
        all_rfps.extend(rfps)
    except Exception as e:
        logger.error(f"Critical error in UNGM API scraper: {e}")

    logger.info(f"Total RFPs found across all API sources: {len(all_rfps)}")
    return all_rfps


# Import notification functions from main scraper
from scraper import send_to_slack, append_to_google_sheets_webhook, append_to_google_sheets_api


def main():
    """
    Main execution function using API-based scraping
    """
    logger.info("=" * 60)
    logger.info("Starting API-based RFP Scraper for Sword Health")
    logger.info(f"Timestamp: {datetime.utcnow().isoformat()}")
    logger.info("=" * 60)

    # Get dedup storage path
    storage_path = os.environ.get('DEDUP_STORAGE_PATH', 'data/seen_rfps.json')

    # Load previously seen RFP IDs
    seen_ids = load_seen_rfps(storage_path)

    # Scrape all sources using APIs
    all_rfps = scrape_all_sources_api()

    # Filter out previously seen RFPs
    new_rfps = filter_new_rfps(all_rfps, seen_ids)

    # Update seen IDs
    for rfp in all_rfps:
        seen_ids.add(rfp['id'])

    # Save updated seen IDs
    save_seen_rfps(storage_path, seen_ids)

    # Send results
    logger.info("=" * 60)
    logger.info(f"Processing {len(new_rfps)} new RFPs (Total scraped: {len(all_rfps)})")
    logger.info("=" * 60)

    # Send to Slack (always send, even if 0 new RFPs)
    if len(new_rfps) == 0:
        logger.info("No new RFPs found - sending empty notification to Slack")
    else:
        logger.info(f"Found {len(new_rfps)} new RFPs - sending to Slack")

    slack_success = send_to_slack(new_rfps)

    # Append to Google Sheets (always send to update Activity Log)
    logger.info("")
    sheets_success = append_to_google_sheets_webhook(new_rfps)
    if not sheets_success:
        logger.info("Webhook failed, trying API method...")
        sheets_success = append_to_google_sheets_api(new_rfps)

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("SCRAPER RUN SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total RFPs scraped: {len(all_rfps)}")
    logger.info(f"New RFPs found: {len(new_rfps)}")
    logger.info(f"Slack notification: {'✓ SENT' if slack_success else '✗ FAILED (check logs above)'}")
    logger.info(f"Google Sheets update: {'✓ SENT' if sheets_success else '✗ FAILED (check logs above)'}")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
