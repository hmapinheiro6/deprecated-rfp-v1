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
        self.api_key = os.environ.get('SAM_GOV_API_KEY', '')
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

        Returns:
            List of RFP dictionaries
        """
        rfps = []

        # Build search query - last 30 days
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

        # Add API key if available (increases rate limits)
        if self.api_key:
            headers['X-Api-Key'] = self.api_key
            logger.debug(f"{self.name}: Using API key")
        else:
            logger.warning(f"{self.name}: No API key set. Get free key at https://open.gsa.gov/api/opportunities-api/")

        logger.debug(f"{self.name}: Request URL: {self.API_URL}")
        logger.debug(f"{self.name}: Params: {params}")

        # Make API request
        response = requests.get(
            self.API_URL,
            params=params,
            headers=headers,
            timeout=self.timeout
        )

        logger.info(f"{self.name}: API response status: {response.status_code}")

        # Handle 401 (missing/invalid API key)
        if response.status_code == 401:
            logger.error(f"{self.name}: 401 Unauthorized - API key may be invalid or required")
            logger.error("Get a free API key at: https://open.gsa.gov/api/opportunities-api/")
            return rfps

        response.raise_for_status()

        data = response.json()

        # Parse opportunities
        opportunities = data.get('opportunitiesData', [])
        logger.info(f"{self.name}: API returned {len(opportunities)} total opportunities")

        for opp in opportunities:
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
