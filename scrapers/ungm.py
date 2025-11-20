"""
UNGM (UN Global Marketplace) Scraper
Scrapes UNGM procurement notices via HTML parsing
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import os

from .base import BaseScraper, logger
from config import KEYWORDS


class UngmScraper(BaseScraper):
    """
    Scraper for UNGM/UN Procurement Notices using HTML parsing

    URL: https://www.ungm.org/Public/Notice
    """

    URL = "https://www.ungm.org/Public/Notice"

    def __init__(self, enabled: bool = True):
        super().__init__(name="UNGM", enabled=enabled)
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
        Scrape UNGM website for procurement notices using HTML parsing

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
                save_debug_html(html_content, "ungm", success=len(html_content) > 5000)

            soup = BeautifulSoup(html_content, 'html.parser')

            # Try multiple possible selectors for UNGM notices
            notices = []

            # Strategy 1: Look for table rows in results table
            table = soup.find('table', class_='ungm-results') or soup.find('table', id='results')
            if table:
                notices = table.find_all('tr', class_='') or table.find_all('tr')[1:]
                logger.debug(f"{self.name}: Found {len(notices)} rows in results table")

            # Strategy 2: Look for list items
            if not notices:
                notices = soup.find_all('li', class_='notice') or soup.find_all('li', class_='result-item')
                logger.debug(f"{self.name}: Found {len(notices)} list item notices")

            # Strategy 3: Look for div containers with notice/result in class
            if not notices:
                notices = soup.find_all('div', class_=lambda x: x and ('notice' in x.lower() or 'result' in x.lower()))
                logger.debug(f"{self.name}: Found {len(notices)} div elements")

            # Strategy 4: Look for any tbody > tr elements (common table structure)
            if not notices:
                tbody = soup.find('tbody')
                if tbody:
                    notices = tbody.find_all('tr')
                    logger.debug(f"{self.name}: Found {len(notices)} tbody rows")

            logger.info(f"{self.name}: Found {len(notices)} potential notice elements")

            if not notices:
                logger.warning(f"{self.name}: No notice elements found - page structure may have changed")
                logger.warning(f"{self.name}: Check debug_html/ungm_*.html to inspect page structure")
                return rfps

            # Parse each notice
            parsed_count = 0
            for notice in notices[:50]:  # Limit to first 50
                try:
                    # Try to extract title - multiple strategies
                    title_elem = (
                        notice.find('td', class_='title') or
                        notice.find('div', class_='title') or
                        notice.find('span', class_='title') or
                        notice.find('h3') or
                        notice.find('h4') or
                        notice.find('a')
                    )
                    title = title_elem.get_text(strip=True) if title_elem else ''

                    # Try to find link
                    link_elem = notice.find('a', href=True)
                    link = link_elem.get('href', '') if link_elem else ''
                    if link:
                        # Handle relative URLs
                        if link.startswith('/'):
                            link = f"https://www.ungm.org{link}"
                        elif not link.startswith('http'):
                            link = f"https://www.ungm.org/Public/Notice/{link}"

                    # Skip if no title or link
                    if not title or not link:
                        continue

                    # Try to extract description
                    desc_elem = (
                        notice.find('td', class_='description') or
                        notice.find('div', class_='description') or
                        notice.find('span', class_='description') or
                        notice.find('p')
                    )
                    description = desc_elem.get_text(strip=True) if desc_elem else ''

                    # Check if relevant
                    combined_text = f"{title} {description}"
                    matched_keywords = self._check_relevance(combined_text)

                    if not matched_keywords:
                        continue

                    # Try to extract dates - UNGM typically has published and deadline dates
                    date_cells = notice.find_all('td', class_='date') or notice.find_all('span', class_='date')
                    publish_date = 'N/A'
                    deadline = 'N/A'

                    if len(date_cells) >= 1:
                        publish_date = date_cells[0].get_text(strip=True)
                    if len(date_cells) >= 2:
                        deadline = date_cells[1].get_text(strip=True)

                    # Alternative: Look for specific date fields
                    if publish_date == 'N/A':
                        pub_elem = notice.find(class_=lambda x: x and 'publish' in x.lower())
                        if pub_elem:
                            publish_date = pub_elem.get_text(strip=True)

                    if deadline == 'N/A':
                        dead_elem = notice.find(class_=lambda x: x and 'deadline' in x.lower())
                        if dead_elem:
                            deadline = dead_elem.get_text(strip=True)

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
