"""
UNGM (UN Global Marketplace) Scraper
Attempts to use UNGM public API (may not exist)
"""

import requests
from typing import List, Dict

from .base import BaseScraper, logger
from config import KEYWORDS


class UngmScraper(BaseScraper):
    """
    Scraper for UNGM/WHO Procurement Notices

    Note: UNGM may not have a public API. This is experimental.
    """

    API_URL = "https://www.ungm.org/Public/Notice/Search"

    def __init__(self, enabled: bool = True):
        super().__init__(name="UNGM", enabled=enabled)
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
        Scrape UNGM API for procurement notices

        Returns:
            List of RFP dictionaries
        """
        rfps = []

        # UNGM may use POST for search
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

        logger.debug(f"{self.name}: Request URL: {self.API_URL}")

        try:
            # Try POST method (UNGM may use this for search)
            response = requests.post(
                self.API_URL,
                json=params,
                headers=headers,
                timeout=self.timeout
            )

            logger.info(f"{self.name}: API response status: {response.status_code}")

            # If API doesn't exist or changed, return empty gracefully
            if response.status_code != 200:
                logger.warning(f"{self.name}: API returned non-200 status. May not have public API.")
                return rfps

            data = response.json()

            # Parse notices (flexible structure)
            notices = data.get('Notices', []) if isinstance(data, dict) else []
            logger.info(f"{self.name}: API returned {len(notices)} notices")

            for notice in notices:
                try:
                    # Try different field names (API structure unknown)
                    title = notice.get('Title', '')
                    description = notice.get('Description', '') or notice.get('Subject', '')

                    # Check relevance
                    combined_text = f"{title} {description}"
                    matched_keywords = self._check_relevance(combined_text)

                    if not matched_keywords:
                        continue

                    # Extract details
                    notice_id = notice.get('ReferenceNumber', '') or notice.get('NoticeId', '')
                    url = f"https://www.ungm.org/Public/Notice/{notice_id}" if notice_id else ""

                    publish_date = notice.get('PublishedDate', 'N/A')
                    deadline = notice.get('SubmissionDeadline', 'N/A') or notice.get('Deadline', 'N/A')

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

        except requests.exceptions.RequestException as e:
            logger.warning(f"{self.name}: Request failed - {e}")
            logger.warning(f"{self.name}: May not have public API or endpoint changed")

        return rfps
