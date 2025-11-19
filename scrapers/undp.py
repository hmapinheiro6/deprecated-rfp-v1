"""
UNDP Procurement Scraper
Attempts to use UNDP procurement API (may not be public)
"""

import requests
from typing import List, Dict

from .base import BaseScraper, logger
from config import KEYWORDS


class UndpScraper(BaseScraper):
    """
    Scraper for UNDP Procurement Notices

    Note: UNDP may not have a public API. This is experimental.
    """

    API_URL = "https://procurement-notices.undp.org/api/notices"

    def __init__(self, enabled: bool = True):
        super().__init__(name="UNDP Procurement", enabled=enabled)
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
        Scrape UNDP API for procurement notices

        Returns:
            List of RFP dictionaries
        """
        rfps = []

        params = {
            'limit': 100,
            'offset': 0,
            'sort': '-published_date'
        }

        headers = {
            'Accept': 'application/json',
            'User-Agent': 'RFP-Scraper-Sword-Health/1.0'
        }

        logger.debug(f"{self.name}: Request URL: {self.API_URL}")

        response = requests.get(
            self.API_URL,
            params=params,
            headers=headers,
            timeout=self.timeout
        )

        logger.info(f"{self.name}: API response status: {response.status_code}")

        # If API doesn't exist or changed, return empty gracefully
        if response.status_code != 200:
            logger.warning(f"{self.name}: API returned non-200 status. May not have public API.")
            return rfps

        response.raise_for_status()

        data = response.json()

        # Parse notices (flexible structure)
        notices = data.get('results', []) if isinstance(data, dict) else data
        logger.info(f"{self.name}: API returned {len(notices)} notices")

        for notice in notices:
            try:
                # Try different field names (API structure unknown)
                title = notice.get('title', '') or notice.get('notice_title', '')
                description = notice.get('description', '') or notice.get('summary', '')

                # Check relevance
                combined_text = f"{title} {description}"
                matched_keywords = self._check_relevance(combined_text)

                if not matched_keywords:
                    continue

                # Extract details
                notice_id = notice.get('id', '') or notice.get('notice_id', '')
                url = f"https://procurement-notices.undp.org/view_notice.cfm?notice_id={notice_id}" if notice_id else ""

                publish_date = notice.get('published_date', 'N/A')
                deadline = notice.get('deadline', 'N/A') or notice.get('submission_date', 'N/A')

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
                logger.debug(f"{self.name}: Error parsing notice: {e}")
                continue

        return rfps
