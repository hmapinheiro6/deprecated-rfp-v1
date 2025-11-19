"""
Gavi Scraper (Selenium-based)
Uses Selenium for JavaScript-rendered content
"""

import time
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from .base import BaseScraper, logger
from config import KEYWORDS


class GaviScraper(BaseScraper):
    """
    Scraper for Gavi tenders and procurements using Selenium

    Gavi uses JavaScript to load content, so we need Selenium
    to render the page before extracting data.
    """

    URL = "https://www.gavi.org/news-resources/tenders-procurements"

    def __init__(self, enabled: bool = True):
        super().__init__(name="Gavi", enabled=enabled)
        self.timeout = 30
        self.page_load_wait = 5  # Seconds to wait for JS to load

    def _get_chrome_options(self) -> Options:
        """
        Configure Chrome options for headless operation

        Returns:
            Configured Chrome options
        """
        chrome_options = Options()

        # Run in headless mode (no UI)
        chrome_options.add_argument('--headless=new')

        # Disable GPU (needed for headless in some environments)
        chrome_options.add_argument('--disable-gpu')

        # No sandbox mode (needed for Docker/CI environments)
        chrome_options.add_argument('--no-sandbox')

        # Disable shared memory (for stability in containers)
        chrome_options.add_argument('--disable-dev-shm-usage')

        # Set window size (some sites behave differently at small sizes)
        chrome_options.add_argument('--window-size=1920,1080')

        # Disable images for faster loading (optional)
        chrome_options.add_argument('--blink-settings=imagesEnabled=false')

        # User agent
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        return chrome_options

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
        Scrape Gavi tenders using Selenium

        Returns:
            List of RFP dictionaries
        """
        rfps = []
        driver = None

        try:
            logger.info(f"{self.name}: Initializing Chrome WebDriver...")

            # Set up Chrome driver with auto-download
            service = Service(ChromeDriverManager().install())
            chrome_options = self._get_chrome_options()
            driver = webdriver.Chrome(service=service, options=chrome_options)

            logger.info(f"{self.name}: Loading page: {self.URL}")
            driver.get(self.URL)

            # Wait for page to load and JavaScript to execute
            logger.debug(f"{self.name}: Waiting {self.page_load_wait}s for JavaScript to load...")
            time.sleep(self.page_load_wait)

            # Try to wait for tender listings to appear
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                logger.debug(f"{self.name}: Page loaded successfully")
            except Exception as e:
                logger.warning(f"{self.name}: Timeout waiting for page load: {e}")

            # Find tender elements
            # Note: Selectors may need adjustment based on actual HTML structure
            tender_selectors = [
                "div.tender",
                "div.procurement",
                "article.tender",
                "div[class*='tender']",
                "div[class*='procurement']",
                "div.card",
                "article"
            ]

            tenders = []
            for selector in tender_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and len(elements) > 2:  # Need at least a few elements
                        logger.debug(f"{self.name}: Found {len(elements)} elements with selector '{selector}'")
                        tenders = elements
                        break
                except Exception as e:
                    logger.debug(f"{self.name}: Selector '{selector}' failed: {e}")
                    continue

            if not tenders:
                logger.warning(f"{self.name}: No tenders found on page. Page may have changed structure.")
                logger.debug(f"{self.name}: Page source preview: {driver.page_source[:500]}...")
                return rfps

            logger.info(f"{self.name}: Processing {len(tenders)} tender elements...")

            for idx, element in enumerate(tenders[:20], 1):  # Limit to first 20
                try:
                    # Extract title (try multiple selectors)
                    title = ""
                    for title_selector in ["h2", "h3", "h4", ".title", "a"]:
                        try:
                            title_elem = element.find_element(By.CSS_SELECTOR, title_selector)
                            title = title_elem.text.strip()
                            if title and len(title) > 10:  # Ensure it's a real title
                                break
                        except:
                            continue

                    if not title:
                        logger.debug(f"{self.name}: Skipping element {idx} - no title found")
                        continue

                    # Extract URL
                    url = ""
                    try:
                        link_elem = element.find_element(By.TAG_NAME, "a")
                        url = link_elem.get_attribute("href")

                        # Make URL absolute if relative
                        if url and not url.startswith('http'):
                            url = f"https://www.gavi.org{url}"
                    except:
                        logger.debug(f"{self.name}: No URL found for: {title[:30]}")

                    # Extract description
                    description = ""
                    for desc_selector in ["p", ".description", ".summary", ".excerpt", "div"]:
                        try:
                            desc_elem = element.find_element(By.CSS_SELECTOR, desc_selector)
                            description = desc_elem.text.strip()
                            if description and len(description) > 30:
                                break
                        except:
                            continue

                    # Check relevance
                    combined_text = f"{title} {description}"
                    matched_keywords = self._check_relevance(combined_text)

                    if not matched_keywords:
                        continue

                    # Extract dates (try to find date elements)
                    publish_date = "N/A"
                    deadline = "N/A"

                    for date_selector in [".date", ".posted", "time", "span", ".deadline"]:
                        try:
                            date_elements = element.find_elements(By.CSS_SELECTOR, date_selector)
                            for date_elem in date_elements:
                                date_text = date_elem.text.strip()
                                # Try to identify if it's a published or deadline date
                                if any(word in date_text.lower() for word in ['posted', 'published', 'date']):
                                    publish_date = date_text
                                elif any(word in date_text.lower() for word in ['deadline', 'due', 'closing']):
                                    deadline = date_text
                                elif publish_date == "N/A" and len(date_text) > 5:
                                    publish_date = date_text
                                elif deadline == "N/A" and len(date_text) > 5:
                                    deadline = date_text
                        except:
                            continue

                    # Create RFP with standardized format
                    rfp = self.create_rfp(
                        title=title,
                        url=url if url else self.URL,
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
                    logger.debug(f"{self.name}: Error processing element {idx}: {e}")
                    continue

        except Exception as e:
            logger.error(f"{self.name}: Error during Selenium scraping: {e}")

        finally:
            # Always close the browser
            if driver:
                try:
                    driver.quit()
                    logger.debug(f"{self.name}: Chrome WebDriver closed")
                except:
                    pass

        return rfps
