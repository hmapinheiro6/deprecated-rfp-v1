"""
Main RFP scraper for Sword Health
Scrapes multiple procurement sources, filters by keywords, and sends daily digests
"""

import os
import sys
import time
import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime

# Import local modules
from config import SOURCES, HEADERS, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY
from utils import (
    logger,
    load_seen_rfps,
    save_seen_rfps,
    filter_new_rfps,
    is_relevant,
    create_rfp_dict,
    safe_get_text,
    safe_get_attr
)


def fetch_url(url: str, retries: int = MAX_RETRIES) -> Optional[BeautifulSoup]:
    """
    Fetch a URL with retry logic

    Args:
        url: URL to fetch
        retries: Number of retry attempts

    Returns:
        BeautifulSoup object or None if failed
    """
    for attempt in range(retries):
        try:
            logger.info(f"Fetching {url} (attempt {attempt + 1}/{retries})")
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True
            )
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                logger.error(f"Failed to fetch {url} after {retries} attempts")
                return None


def scrape_sam_gov() -> List[Dict]:
    """
    Scrape SAM.gov procurement notices

    Returns:
        List of RFP dictionaries
    """
    source_name = "SAM.gov"
    logger.info(f"Scraping {source_name}...")
    rfps = []

    soup = fetch_url(SOURCES['sam_gov']['url'])
    if not soup:
        return rfps

    try:
        # SAM.gov structure: Look for opportunity cards/listings
        # Note: SAM.gov may require API access or has dynamic content
        # This is a best-effort HTML scraping approach

        # Try to find results containers
        results = soup.find_all(['div', 'article', 'li'], class_=lambda x: x and any(
            term in str(x).lower() for term in ['result', 'opportunity', 'notice', 'listing']
        ))

        for result in results[:20]:  # Limit to first 20 results
            try:
                # Try to extract title
                title_elem = result.find(['h2', 'h3', 'h4', 'a'], class_=lambda x: x and 'title' in str(x).lower())
                if not title_elem:
                    title_elem = result.find(['h2', 'h3', 'h4'])

                if not title_elem:
                    continue

                title = safe_get_text(title_elem)

                # Extract URL
                link_elem = title_elem if title_elem.name == 'a' else result.find('a')
                url = safe_get_attr(link_elem, 'href')

                if url and not url.startswith('http'):
                    url = f"https://sam.gov{url}"

                # Get description/snippet
                snippet_elem = result.find(['p', 'div'], class_=lambda x: x and any(
                    term in str(x).lower() for term in ['description', 'snippet', 'summary']
                ))
                snippet = safe_get_text(snippet_elem)

                # Check relevance
                combined_text = f"{title} {snippet}"
                if not is_relevant(combined_text):
                    continue

                # Try to extract dates
                date_elem = result.find(['span', 'div', 'time'], class_=lambda x: x and any(
                    term in str(x).lower() for term in ['date', 'posted', 'published']
                ))
                publish_date = safe_get_text(date_elem)

                deadline_elem = result.find(['span', 'div', 'time'], class_=lambda x: x and any(
                    term in str(x).lower() for term in ['deadline', 'due', 'response']
                ))
                deadline = safe_get_text(deadline_elem)

                if title and url:
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
                logger.debug(f"Error parsing SAM.gov result: {e}")
                continue

    except Exception as e:
        logger.error(f"Error scraping {source_name}: {e}")

    logger.info(f"Found {len(rfps)} relevant RFPs from {source_name}")
    return rfps


def scrape_undp() -> List[Dict]:
    """
    Scrape UNDP procurement notices

    Returns:
        List of RFP dictionaries
    """
    source_name = "UNDP Procurement"
    logger.info(f"Scraping {source_name}...")
    rfps = []

    soup = fetch_url(SOURCES['undp']['url'])
    if not soup:
        return rfps

    try:
        # Look for notice listings
        notices = soup.find_all(['tr', 'div', 'article'], class_=lambda x: x and any(
            term in str(x).lower() for term in ['notice', 'tender', 'row', 'item']
        ))

        for notice in notices[:30]:
            try:
                # Extract title
                title_elem = notice.find(['a', 'h3', 'h4'])
                if not title_elem:
                    continue

                title = safe_get_text(title_elem)

                # Extract URL
                link_elem = title_elem if title_elem.name == 'a' else notice.find('a')
                url = safe_get_attr(link_elem, 'href')

                if url and not url.startswith('http'):
                    url = f"https://procurement-notices.undp.org{url}"

                # Get description
                desc_elem = notice.find(['p', 'td', 'div'], class_=lambda x: x and 'desc' in str(x).lower() if x else False)
                snippet = safe_get_text(desc_elem)

                # Check relevance
                combined_text = f"{title} {snippet}"
                if not is_relevant(combined_text):
                    continue

                # Extract dates
                date_cells = notice.find_all(['td', 'span', 'div'], class_=lambda x: x and 'date' in str(x).lower() if x else False)
                publish_date = safe_get_text(date_cells[0]) if len(date_cells) > 0 else "N/A"
                deadline = safe_get_text(date_cells[1]) if len(date_cells) > 1 else "N/A"

                if title and url:
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

    except Exception as e:
        logger.error(f"Error scraping {source_name}: {e}")

    logger.info(f"Found {len(rfps)} relevant RFPs from {source_name}")
    return rfps


def scrape_ungm() -> List[Dict]:
    """
    Scrape UNGM/WHO procurement notices

    Returns:
        List of RFP dictionaries
    """
    source_name = "UNGM"
    logger.info(f"Scraping {source_name}...")
    rfps = []

    soup = fetch_url(SOURCES['ungm']['url'])
    if not soup:
        return rfps

    try:
        # Look for notice rows in table
        notices = soup.find_all(['tr', 'div'], class_=lambda x: x and any(
            term in str(x).lower() for term in ['notice', 'row', 'item', 'tender']
        ))

        for notice in notices[:30]:
            try:
                # Extract title and link
                link_elem = notice.find('a')
                if not link_elem:
                    continue

                title = safe_get_text(link_elem)
                url = safe_get_attr(link_elem, 'href')

                if url and not url.startswith('http'):
                    url = f"https://www.ungm.org{url}"

                # Get additional details
                cells = notice.find_all(['td', 'div'])
                snippet = ""
                publish_date = "N/A"
                deadline = "N/A"

                for cell in cells:
                    text = safe_get_text(cell)
                    if len(text) > 50 and not snippet:
                        snippet = text
                    # Look for date patterns
                    if '/' in text or '-' in text:
                        if publish_date == "N/A":
                            publish_date = text
                        else:
                            deadline = text

                # Check relevance
                combined_text = f"{title} {snippet}"
                if not is_relevant(combined_text):
                    continue

                if title and url:
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

    except Exception as e:
        logger.error(f"Error scraping {source_name}: {e}")

    logger.info(f"Found {len(rfps)} relevant RFPs from {source_name}")
    return rfps


def scrape_sourcewell() -> List[Dict]:
    """
    Scrape Sourcewell solicitations

    Returns:
        List of RFP dictionaries
    """
    source_name = "Sourcewell"
    logger.info(f"Scraping {source_name}...")
    rfps = []

    soup = fetch_url(SOURCES['sourcewell']['url'])
    if not soup:
        return rfps

    try:
        # Look for solicitation listings
        solicitations = soup.find_all(['div', 'article', 'li'], class_=lambda x: x and any(
            term in str(x).lower() for term in ['solicitation', 'item', 'card', 'listing']
        ))

        for item in solicitations[:20]:
            try:
                # Extract title
                title_elem = item.find(['h2', 'h3', 'h4', 'a'])
                if not title_elem:
                    continue

                title = safe_get_text(title_elem)

                # Extract URL
                link_elem = title_elem if title_elem.name == 'a' else item.find('a')
                url = safe_get_attr(link_elem, 'href')

                if url and not url.startswith('http'):
                    url = f"https://www.sourcewell-mn.gov{url}"

                # Get description
                desc_elem = item.find(['p', 'div'], class_=lambda x: x and any(
                    term in str(x).lower() for term in ['description', 'summary', 'content']
                ))
                snippet = safe_get_text(desc_elem)

                # Check relevance
                combined_text = f"{title} {snippet}"
                if not is_relevant(combined_text):
                    continue

                # Try to extract dates
                date_elem = item.find(['span', 'div', 'time'], class_=lambda x: x and 'date' in str(x).lower() if x else False)
                publish_date = safe_get_text(date_elem)

                deadline_elem = item.find(['span', 'div', 'time'], class_=lambda x: x and any(
                    term in str(x).lower() for term in ['deadline', 'due', 'close']
                ) if x else False)
                deadline = safe_get_text(deadline_elem)

                if title and url:
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
                logger.debug(f"Error parsing Sourcewell solicitation: {e}")
                continue

    except Exception as e:
        logger.error(f"Error scraping {source_name}: {e}")

    logger.info(f"Found {len(rfps)} relevant RFPs from {source_name}")
    return rfps


def scrape_gavi() -> List[Dict]:
    """
    Scrape Gavi tenders and procurements

    Returns:
        List of RFP dictionaries
    """
    source_name = "Gavi"
    logger.info(f"Scraping {source_name}...")
    rfps = []

    soup = fetch_url(SOURCES['gavi']['url'])
    if not soup:
        return rfps

    try:
        # Look for tender listings
        tenders = soup.find_all(['div', 'article', 'li'], class_=lambda x: x and any(
            term in str(x).lower() for term in ['tender', 'procurement', 'card', 'item', 'listing']
        ))

        for tender in tenders[:20]:
            try:
                # Extract title
                title_elem = tender.find(['h2', 'h3', 'h4', 'a'])
                if not title_elem:
                    continue

                title = safe_get_text(title_elem)

                # Extract URL
                link_elem = title_elem if title_elem.name == 'a' else tender.find('a')
                url = safe_get_attr(link_elem, 'href')

                if url and not url.startswith('http'):
                    url = f"https://www.gavi.org{url}"

                # Get description
                desc_elem = tender.find(['p', 'div'], class_=lambda x: x and any(
                    term in str(x).lower() for term in ['description', 'summary', 'excerpt']
                ))
                snippet = safe_get_text(desc_elem)

                # Check relevance
                combined_text = f"{title} {snippet}"
                if not is_relevant(combined_text):
                    continue

                # Try to extract dates
                date_elem = tender.find(['span', 'div', 'time'], class_=lambda x: x and 'date' in str(x).lower() if x else False)
                publish_date = safe_get_text(date_elem)

                deadline_elem = tender.find(['span', 'div', 'time'], class_=lambda x: x and any(
                    term in str(x).lower() for term in ['deadline', 'closing', 'due']
                ) if x else False)
                deadline = safe_get_text(deadline_elem)

                if title and url:
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
                logger.debug(f"Error parsing Gavi tender: {e}")
                continue

    except Exception as e:
        logger.error(f"Error scraping {source_name}: {e}")

    logger.info(f"Found {len(rfps)} relevant RFPs from {source_name}")
    return rfps


def build_slack_workflow_payload(rfps: List[Dict]) -> Dict:
    """
    Build Slack Workflow webhook payload from RFP list
    This format is for Slack Workflows with webhook triggers

    Args:
        rfps: List of RFP dictionaries

    Returns:
        Simple key-value payload for Slack Workflows
    """
    if not rfps:
        return {
            "count": 0,
            "message": "No new relevant RFPs found today.",
            "rfps": []
        }

    # Build a formatted text summary
    rfp_list = []
    for rfp in rfps:
        rfp_list.append({
            "title": rfp.get("title", "Untitled RFP"),
            "url": rfp.get("url", ""),
            "source": rfp.get("source", "Unknown"),
            "published": rfp.get("publish_date", "N/A"),
            "deadline": rfp.get("deadline", "N/A")
        })

    # Create a text summary for the workflow
    summary = f"Found {len(rfps)} new relevant RFP(s) for Sword Health:\n\n"
    for i, rfp in enumerate(rfps[:10], 1):  # Limit to 10 in summary
        summary += f"{i}. {rfp.get('title', 'Untitled')} ({rfp.get('source', 'Unknown')})\n"
        summary += f"   Deadline: {rfp.get('deadline', 'N/A')}\n"
        summary += f"   {rfp.get('url', '')}\n\n"

    if len(rfps) > 10:
        summary += f"... and {len(rfps) - 10} more RFPs"

    return {
        "count": len(rfps),
        "message": summary,
        "rfps": rfp_list
    }


def build_slack_blocks_payload(rfps: List[Dict]) -> Dict:
    """
    Build Slack message payload with blocks (for traditional Incoming Webhooks)

    Args:
        rfps: List of RFP dictionaries

    Returns:
        Slack-formatted payload with blocks
    """
    if not rfps:
        text = "No new relevant RFPs found today."
        return {
            "text": text,
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": text}
                }
            ]
        }

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Daily RFP Digest – Sword Health",
                "emoji": True
            }
        },
        {"type": "divider"}
    ]

    for rfp in rfps:
        title = rfp.get("title", "Untitled RFP")
        url = rfp.get("url", "")
        source = rfp.get("source", "Unknown source")
        publish_date = rfp.get("publish_date", "N/A")
        deadline = rfp.get("deadline", "N/A")

        text = (
            f"*<{url}|{title}>*\n"
            f"*Source:* {source}\n"
            f"*Published:* {publish_date}   •   *Deadline:* {deadline}"
        )

        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text
                }
            }
        )
        blocks.append({"type": "divider"})

    return {
        "text": "Daily RFP Digest – Sword Health",
        "blocks": blocks
    }


def send_to_slack(rfps: List[Dict]) -> bool:
    """
    Send RFP digest to Slack via webhook
    Auto-detects Slack Workflow webhooks vs traditional Incoming Webhooks

    Args:
        rfps: List of RFP dictionaries

    Returns:
        True if successful, False otherwise
    """
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')

    if not webhook_url:
        logger.warning("SLACK_WEBHOOK_URL not set, skipping Slack notification")
        return False

    try:
        # Detect webhook type by URL pattern
        # Slack Workflow webhooks contain '/workflows/' in the URL
        is_workflow = '/workflows/' in webhook_url

        if is_workflow:
            logger.info("Detected Slack Workflow webhook, using simple payload format")
            payload = build_slack_workflow_payload(rfps)
        else:
            logger.info("Detected traditional Slack webhook, using blocks format")
            payload = build_slack_blocks_payload(rfps)

        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"Successfully sent {len(rfps)} RFPs to Slack")
        return True
    except Exception as e:
        logger.error(f"Error sending to Slack: {e}")
        return False


def append_to_google_sheets_webhook(rfps: List[Dict]) -> bool:
    """
    Append RFPs to Google Sheets via Apps Script webhook
    This is the SIMPLE method - no Google Cloud credentials needed!

    Note: This function ALWAYS sends data to update the Activity Log,
    even when there are 0 new RFPs.

    Args:
        rfps: List of RFP dictionaries

    Returns:
        True if successful, False otherwise
    """
    webhook_url = os.environ.get('GOOGLE_SHEETS_WEBHOOK_URL')

    if not webhook_url:
        logger.info("GOOGLE_SHEETS_WEBHOOK_URL not set, skipping Sheets update")
        return False

    try:
        # Prepare payload
        # Always send, even with empty list, to update Activity Log
        payload = {
            'rfps': [
                {
                    'title': rfp.get('title', ''),
                    'url': rfp.get('url', ''),
                    'source': rfp.get('source', ''),
                    'publish_date': rfp.get('publish_date', 'N/A'),
                    'deadline': rfp.get('deadline', 'N/A'),
                    'snippet': rfp.get('snippet', '')
                }
                for rfp in rfps
            ]
        }

        response = requests.post(
            webhook_url,
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        result = response.json()

        if len(rfps) > 0:
            logger.info(f"Successfully appended {len(rfps)} RFPs to Google Sheets via webhook")
        else:
            logger.info("Updated Google Sheets Activity Log (0 new RFPs)")

        return True

    except Exception as e:
        logger.error(f"Error appending to Google Sheets webhook: {e}")
        return False


def append_to_google_sheets_api(rfps: List[Dict]) -> bool:
    """
    Append RFPs to Google Sheets using Google API (requires Google Cloud setup)
    This is the COMPLEX method - only use if you need more control

    Args:
        rfps: List of RFP dictionaries

    Returns:
        True if successful, False otherwise
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        logger.warning("Google API libraries not available, skipping Sheets update")
        return False

    service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    sheet_id = os.environ.get('GOOGLE_SHEET_ID')

    if not service_account_json or not sheet_id:
        logger.info("Google Sheets API credentials not set, skipping API update")
        return False

    try:
        # Parse service account JSON
        import json
        credentials_dict = json.loads(service_account_json)

        # Create credentials
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )

        # Build service
        service = build('sheets', 'v4', credentials=credentials)

        # Prepare rows
        rows = []
        for rfp in rfps:
            row = [
                datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                rfp.get('title', ''),
                rfp.get('url', ''),
                rfp.get('source', ''),
                rfp.get('publish_date', 'N/A'),
                rfp.get('deadline', 'N/A'),
                rfp.get('snippet', '')
            ]
            rows.append(row)

        # Append to sheet
        body = {
            'values': rows
        }

        result = service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range='Sheet1!A:G',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()

        logger.info(f"Successfully appended {len(rfps)} RFPs to Google Sheets via API")
        return True

    except Exception as e:
        logger.error(f"Error appending to Google Sheets API: {e}")
        return False


def scrape_all_sources() -> List[Dict]:
    """
    Scrape all enabled sources

    Returns:
        Combined list of all RFPs from all sources
    """
    all_rfps = []

    scrapers = {
        'sam_gov': scrape_sam_gov,
        'undp': scrape_undp,
        'ungm': scrape_ungm,
        'sourcewell': scrape_sourcewell,
        'gavi': scrape_gavi
    }

    for source_key, scraper_func in scrapers.items():
        if SOURCES.get(source_key, {}).get('enabled', False):
            try:
                rfps = scraper_func()
                all_rfps.extend(rfps)
            except Exception as e:
                logger.error(f"Critical error in {source_key} scraper: {e}")
                continue

    logger.info(f"Total RFPs found across all sources: {len(all_rfps)}")
    return all_rfps


def main():
    """
    Main execution function
    """
    logger.info("=" * 60)
    logger.info("Starting RFP Scraper for Sword Health")
    logger.info(f"Timestamp: {datetime.utcnow().isoformat()}")
    logger.info("=" * 60)

    # Get dedup storage path
    storage_path = os.environ.get('DEDUP_STORAGE_PATH', 'data/seen_rfps.json')

    # Load previously seen RFP IDs
    seen_ids = load_seen_rfps(storage_path)

    # Scrape all sources
    all_rfps = scrape_all_sources()

    # Filter out previously seen RFPs
    new_rfps = filter_new_rfps(all_rfps, seen_ids)

    # Update seen IDs
    for rfp in all_rfps:
        seen_ids.add(rfp['id'])

    # Save updated seen IDs
    save_seen_rfps(storage_path, seen_ids)

    # Send results
    logger.info(f"Processing {len(new_rfps)} new RFPs")

    # Send to Slack (always send, even if 0 new RFPs)
    if len(new_rfps) == 0:
        logger.info("Sending 'no new RFPs' notification to Slack")
    send_to_slack(new_rfps)

    # Append to Google Sheets (always send to update Activity Log)
    sheets_success = append_to_google_sheets_webhook(new_rfps)
    if not sheets_success:
        append_to_google_sheets_api(new_rfps)

    logger.info("=" * 60)
    logger.info(f"Scraper completed successfully. Found {len(new_rfps)} new relevant RFPs.")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
