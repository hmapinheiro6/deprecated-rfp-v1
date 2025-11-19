"""
Base scraper class with common functionality
All scrapers inherit from this to ensure consistent behavior
"""

import time
import logging
from typing import List, Dict, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Abstract base class for all procurement scrapers

    Provides:
    - Retry logic with exponential backoff
    - Standardized error handling
    - Consistent return format
    - Logging
    """

    def __init__(self, name: str, enabled: bool = True):
        """
        Initialize base scraper

        Args:
            name: Display name for this scraper (e.g., "SAM.gov")
            enabled: Whether this scraper is enabled in config
        """
        self.name = name
        self.enabled = enabled
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    @abstractmethod
    def _scrape(self) -> List[Dict]:
        """
        Internal scraping logic - must be implemented by subclasses

        Returns:
            List of RFP dictionaries with standard format
        """
        pass

    def scrape(self) -> List[Dict]:
        """
        Public scrape method with error handling and retry logic

        Returns:
            List of RFP dictionaries, empty list on failure
        """
        if not self.enabled:
            logger.info(f"{self.name} scraper is disabled in config")
            return []

        logger.info(f"Starting scraper: {self.name}")

        for attempt in range(self.max_retries):
            try:
                rfps = self._scrape()
                logger.info(f"✓ {self.name}: Found {len(rfps)} relevant RFPs")
                return rfps

            except Exception as e:
                logger.error(f"✗ {self.name} (attempt {attempt + 1}/{self.max_retries}): {e}")

                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"✗ {self.name}: All retry attempts failed")
                    return []

        return []

    def validate_rfp(self, rfp: Dict) -> bool:
        """
        Validate that an RFP dictionary has required fields

        Args:
            rfp: RFP dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        required_fields = ['source', 'title', 'url', 'publish_date', 'deadline']

        for field in required_fields:
            if field not in rfp or not rfp[field]:
                logger.warning(f"RFP missing required field '{field}': {rfp.get('title', 'Unknown')}")
                return False

        return True

    def create_rfp(
        self,
        title: str,
        url: str,
        publish_date: str,
        deadline: str,
        description: str = "",
        matched_keywords: List[str] = None
    ) -> Dict:
        """
        Create a standardized RFP dictionary

        Args:
            title: RFP title
            url: Full URL to RFP
            publish_date: Publication date (YYYY-MM-DD format preferred)
            deadline: Response deadline (YYYY-MM-DD format preferred)
            description: RFP description (max 500 chars)
            matched_keywords: List of keywords that matched

        Returns:
            Standardized RFP dictionary
        """
        # Truncate description to 500 chars
        if description and len(description) > 500:
            description = description[:497] + "..."

        # Format matched keywords
        keywords_str = ", ".join(matched_keywords) if matched_keywords else ""

        rfp = {
            'source': self.name,
            'title': title.strip() if title else "",
            'description': description.strip() if description else "",
            'posted_date': publish_date.strip() if publish_date else "N/A",
            'response_date': deadline.strip() if deadline else "N/A",
            'url': url.strip() if url else "",
            'matched_keyword': keywords_str
        }

        return rfp
