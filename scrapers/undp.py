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

    URL: https://procurement-notices.undp.org/view_notices
    """

    URL = "https://procurement-notices.undp.org/view_notices"

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

            # Try multiple possible selectors for UNDP notices
            # These are common patterns - may need adjustment after inspecting actual HTML
            notices = []

            # Strategy 1: Look for table rows with notice data
            table = soup.find('table', class_='notices') or soup.find('table', id='notices-table')
            if table:
                notices = table.find_all('tr')[1:]  # Skip header row
                logger.debug(f"{self.name}: Found {len(notices)} rows in notices table")

            # Strategy 2: Look for div containers
            if not notices:
                notices = soup.find_all('div', class_='notice') or soup.find_all('div', class_='notice-item')
                logger.debug(f"{self.name}: Found {len(notices)} notice divs")

            # Strategy 3: Look for article elements
            if not notices:
                notices = soup.find_all('article', class_='notice') or soup.find_all('article')
                logger.debug(f"{self.name}: Found {len(notices)} article elements")

            # Strategy 4: Look for any elements with 'notice' in class name
            if not notices:
                notices = soup.find_all(class_=lambda x: x and 'notice' in x.lower())
                logger.debug(f"{self.name}: Found {len(notices)} elements with 'notice' in class")

            logger.info(f"{self.name}: Found {len(notices)} potential notice elements")

            if not notices:
                logger.warning(f"{self.name}: No notice elements found - page structure may have changed")
                logger.warning(f"{self.name}: Check debug_html/undp_*.html to inspect page structure")
                return rfps

            # Parse each notice
            parsed_count = 0
            for notice in notices[:50]:  # Limit to first 50 to avoid processing too much
                try:
                    # Try to extract title - multiple strategies
                    title_elem = (
                        notice.find('td', class_='title') or
                        notice.find('div', class_='title') or
                        notice.find('h2') or
                        notice.find('h3') or
                        notice.find('a')
                    )
                    title = title_elem.get_text(strip=True) if title_elem else ''

                    # Try to extract description
                    desc_elem = (
                        notice.find('td', class_='description') or
                        notice.find('div', class_='description') or
                        notice.find('p')
                    )
                    description = desc_elem.get_text(strip=True) if desc_elem else ''

                    # Try to find link
                    link_elem = notice.find('a')
                    link = link_elem.get('href', '') if link_elem else ''
                    if link and not link.startswith('http'):
                        link = f"https://procurement-notices.undp.org{link}"

                    # Skip if no title or link
                    if not title or not link:
                        continue

                    # Check if relevant
                    combined_text = f"{title} {description}"
                    matched_keywords = self._check_relevance(combined_text)

                    if not matched_keywords:
                        continue

                    # Try to extract dates
                    date_elems = notice.find_all('td', class_='date') or notice.find_all('span', class_='date')
                    publish_date = 'N/A'
                    deadline = 'N/A'
                    if len(date_elems) >= 1:
                        publish_date = date_elems[0].get_text(strip=True)
                    if len(date_elems) >= 2:
                        deadline = date_elems[1].get_text(strip=True)

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
