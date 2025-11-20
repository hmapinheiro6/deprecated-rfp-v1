"""
UNDP Procurement Scraper
Scrapes UNDP procurement notices via HTML parsing
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import os

from .base import BaseScraper, logger
from config import KEYWORDS


class UndpScraper(BaseScraper):
    """
    Scraper for UNDP Procurement Notices using HTML parsing

    URL: https://procurement-notices.undp.org/
    """

    URL = "https://procurement-notices.undp.org/"

    def __init__(self, enabled: bool = True):
        super().__init__(name="UNDP Procurement", enabled=enabled)
        self.timeout = 30
        self.save_debug = os.environ.get('SAVE_DEBUG_HTML', 'false').lower() == 'true'

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
        Scrape UNDP website for procurement notices using HTML parsing

        Returns:
            List of RFP dictionaries
        """
        rfps = []

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }

            logger.info(f"{self.name}: Fetching HTML from {self.URL}")

            response = requests.get(
                self.URL,
                headers=headers,
                timeout=self.timeout
            )

            logger.info(f"{self.name}: Response status: {response.status_code}")

            if response.status_code != 200:
                logger.warning(f"{self.name}: Non-200 status code, aborting")
                return rfps

            html_content = response.text

            # Save debug HTML if enabled
            if self.save_debug or len(html_content) < 5000:
                from utils import save_debug_html
                save_debug_html(html_content, "undp", success=len(html_content) > 5000)

            soup = BeautifulSoup(html_content, 'html.parser')

            # UNDP uses anchor tags with href containing 'view_negotiation.cfm' or 'view_notice.cfm'
            # Each notice is a single <a> tag with multiple <div> children
            notices = []

            # Find all anchor tags that link to notice/negotiation pages
            notice_links = soup.find_all('a', href=lambda x: x and ('view_negotiation.cfm' in x or 'view_notice.cfm' in x))
            if notice_links:
                notices = notice_links
                logger.debug(f"{self.name}: Found {len(notices)} notice links")

            logger.info(f"{self.name}: Found {len(notices)} potential notice elements")

            if not notices:
                logger.warning(f"{self.name}: No notice elements found - page structure may have changed")
                logger.warning(f"{self.name}: Check debug_html/undp_*.html to inspect page structure")
                return rfps

            # Parse each notice
            parsed_count = 0
            for notice in notices[:50]:  # Limit to first 50 to avoid processing too much
                try:
                    # Extract all divs from the anchor tag
                    divs = notice.find_all('div')

                    # Skip if not enough divs
                    if len(divs) < 4:
                        continue

                    # Extract data from divs (based on UNDP structure)
                    # Div 0: Title
                    # Div 1: Reference number
                    # Div 2: Office/Country
                    # Div 3: Process type
                    # Div 4: Deadline
                    # Div 5: Posted date

                    title = divs[0].get_text(strip=True) if len(divs) > 0 else ''
                    ref_number = divs[1].get_text(strip=True) if len(divs) > 1 else ''
                    office = divs[2].get_text(strip=True) if len(divs) > 2 else ''
                    process_type = divs[3].get_text(strip=True) if len(divs) > 3 else ''
                    deadline = divs[4].get_text(strip=True) if len(divs) > 4 else 'N/A'
                    publish_date = divs[5].get_text(strip=True) if len(divs) > 5 else 'N/A'

                    # Get the link URL
                    link = notice.get('href', '')
                    if link and not link.startswith('http'):
                        link = f"https://procurement-notices.undp.org/{link}"

                    # Skip if no title or link
                    if not title or not link:
                        continue

                    # Create description from available fields
                    description = f"{process_type} - {office} - Ref: {ref_number}"

                    # Check if relevant
                    combined_text = f"{title} {description}"
                    matched_keywords = self._check_relevance(combined_text)

                    if not matched_keywords:
                        continue

                    # Create RFP
                    rfp = self.create_rfp(
                        title=title,
                        url=link,
                        publish_date=publish_date,
                        deadline=deadline,
                        description=description[:500],
                        matched_keywords=matched_keywords
                    )

                    if self.validate_rfp(rfp):
                        rfps.append(rfp)
                        parsed_count += 1
                        logger.debug(f"{self.name}: Found relevant RFP: {title[:50]}...")

                except Exception as e:
                    logger.debug(f"{self.name}: Error parsing notice: {e}")
                    continue

            logger.info(f"{self.name}: Successfully parsed {parsed_count} relevant RFPs")

        except requests.exceptions.RequestException as e:
            logger.error(f"{self.name}: HTTP error - {e}")
        except Exception as e:
            logger.error(f"{self.name}: Unexpected error - {e}", exc_info=True)

        return rfps
