"""
SAM.gov API Scraper
Uses official Opportunities API for US Government procurement
API Docs: https://open.gsa.gov/api/opportunities-api/
"""

import os
import requests
from typing import List, Dict
from datetime import datetime, timedelta

from .base import BaseScraper, logger
from config import KEYWORDS


class SamGovScraper(BaseScraper):
    """
    Scraper for SAM.gov using their official API

    Requires: SAM_GOV_API_KEY environment variable (free, recommended)
    """

    API_URL = "https://api.sam.gov/opportunities/v2/search"

    def __init__(self, enabled: bool = True):
        super().__init__(name="SAM.gov", enabled=enabled)
        self.api_key = os.environ.get('SAM_GOV_API_KEY', '').strip()
        self.timeout = 30

    def _check_relevance(self, text: str) -> List[str]:
        """
        Check if text matches any keywords

        Args:
            text: Text to check

        Returns:
            List of matched keywords
        """
        if not text:
            return []

        text_lower = text.lower()
        matched = []

        for keyword in KEYWORDS:
            if keyword.lower() in text_lower:
                matched.append(keyword)

        return matched

    def _scrape(self) -> List[Dict]:
        """
        Scrape SAM.gov API for procurement opportunities
        Uses keyword-based search for better targeting

        Returns:
            List of RFP dictionaries
        """
        rfps = []
        all_opportunities = []

        # Check if API key is set
        if not self.api_key:
            logger.error(f"{self.name}: ========================================")
            logger.error(f"{self.name}: SAM_GOV_API_KEY environment variable is NOT SET!")
            logger.error(f"{self.name}: SAM.gov API requires an API key for ALL requests.")
            logger.error(f"{self.name}: ")
            logger.error(f"{self.name}: To fix:")
            logger.error(f"{self.name}: 1. Get free API key: https://open.gsa.gov/api/opportunities-api/")
            logger.error(f"{self.name}: 2. Add to GitHub Secrets as: SAM_GOV_API_KEY")
            logger.error(f"{self.name}: 3. Restart the workflow")
            logger.error(f"{self.name}: ========================================")
            return rfps

        logger.info(f"{self.name}: API key found: {self.api_key[:10]}...")

        # Strategy: Search by each keyword separately to find relevant opportunities
        # This avoids date format issues and gets better targeted results
        # Limit keywords to conserve daily API quota (free tier has daily limits)
        max_keywords = 3  # Reduced to 3 to conserve quota
        keywords_to_search = KEYWORDS[:max_keywords]
        logger.info(f"{self.name}: Searching by {len(keywords_to_search)} keywords (out of {len(KEYWORDS)} total)")
        logger.info(f"{self.name}: Keywords: {keywords_to_search}")

        for keyword in keywords_to_search:
            try:
                params = {
                    'keyword': keyword,  # Correct parameter for v2 API
                    'size': 50,          # Limit per keyword (v2 uses 'size')
                    'latest': 'true',    # Get latest records only
                    'api_key': self.api_key  # Required for all requests
                }

                headers = {
                    'Accept': 'application/json',
                    'User-Agent': 'RFP-Scraper-Sword-Health/1.0'
                }

                logger.info(f"{self.name}: Searching for keyword: '{keyword}'")

                # Make API request
                response = requests.get(
                    self.API_URL,
                    params=params,
                    headers=headers,
                    timeout=self.timeout
                )

                # DETAILED LOGGING FOR DEBUGGING
                logger.info(f"{self.name}: ========== REQUEST DETAILS ==========")
                logger.info(f"{self.name}: Full URL: {response.url}")
                logger.info(f"{self.name}: Response Status: {response.status_code}")
                logger.info(f"{self.name}: Response Headers: {dict(response.headers)}")
                logger.info(f"{self.name}: Response Text (first 1000 chars):")
                logger.info(f"{self.name}: {response.text[:1000]}")
                logger.info(f"{self.name}: =====================================")

                # Handle 401 (missing/invalid API key)
                if response.status_code == 401:
                    logger.error(f"{self.name}: 401 Unauthorized - API key invalid or required")
                    logger.error("Get a free API key at: https://open.gsa.gov/api/opportunities-api/")
                    break  # Stop trying other keywords

                # Handle 429 (rate limit / quota exceeded)
                if response.status_code == 429:
                    try:
                        error_data = response.json()
                        if 'nextAccessTime' in error_data:
                            logger.error(f"{self.name}: ========================================")
                            logger.error(f"{self.name}: Daily API quota exceeded!")
                            logger.error(f"{self.name}: Message: {error_data.get('message', 'N/A')}")
                            logger.error(f"{self.name}: Next access time: {error_data.get('nextAccessTime', 'N/A')}")
                            logger.error(f"{self.name}: ")
                            logger.error(f"{self.name}: The SAM.gov API will work again after the quota resets.")
                            logger.error(f"{self.name}: Your scheduled daily run should work fine tomorrow.")
                            logger.error(f"{self.name}: ========================================")
                        else:
                            logger.error(f"{self.name}: 429 Rate Limited: {response.text[:500]}")
                    except:
                        logger.error(f"{self.name}: 429 Rate Limited: {response.text[:500]}")
                    break  # Stop trying other keywords

                if response.status_code != 200:
                    logger.warning(f"{self.name}: Got status {response.status_code} for keyword '{keyword}'")
                    logger.warning(f"{self.name}: Response body: {response.text[:500]}")
                    continue  # Try next keyword

                data = response.json()
                logger.info(f"{self.name}: Response JSON keys: {list(data.keys())}")

                # Parse opportunities
                opportunities = data.get('opportunitiesData', [])
                logger.debug(f"{self.name}: Found {len(opportunities)} opportunities for '{keyword}'")
                all_opportunities.extend(opportunities)

            except Exception as e:
                logger.warning(f"{self.name}: Error searching keyword '{keyword}': {e}")
                continue

        # Deduplicate by notice ID
        seen_ids = set()
        unique_opportunities = []
        for opp in all_opportunities:
            notice_id = opp.get('noticeId', '')
            if notice_id and notice_id not in seen_ids:
                seen_ids.add(notice_id)
                unique_opportunities.append(opp)

        logger.info(f"{self.name}: Found {len(unique_opportunities)} unique opportunities after deduplication")

        # Parse unique opportunities
        for opp in unique_opportunities:
            try:
                title = opp.get('title', '')
                description = opp.get('description', '')

                # Check relevance against keywords
                combined_text = f"{title} {description}"
                matched_keywords = self._check_relevance(combined_text)

                if not matched_keywords:
                    continue

                # Extract details
                notice_id = opp.get('noticeId', '')
                url = f"https://sam.gov/opp/{notice_id}/view" if notice_id else ""

                publish_date = opp.get('postedDate', 'N/A')
                deadline = opp.get('responseDeadLine', 'N/A')

                # Create RFP with standardized format
                rfp = self.create_rfp(
                    title=title,
                    url=url,
                    publish_date=publish_date,
                    deadline=deadline,
                    description=description,
                    matched_keywords=matched_keywords
                )

                # Validate before adding
                if self.validate_rfp(rfp):
                    rfps.append(rfp)
                    logger.debug(f"{self.name}: Found relevant RFP: {title[:50]}...")

            except Exception as e:
                logger.debug(f"{self.name}: Error parsing opportunity: {e}")
                continue

        return rfps
