"""
Configuration file for RFP scraper
Contains keywords for filtering and source URLs
"""

# Keywords to filter RFPs (case-insensitive matching)
KEYWORDS = [
    "digital health",
    "telehealth",
    "virtual physical therapy",
    "musculoskeletal",
    "msk",
    "physical therapy",
    "employee wellness",
    "digital therapeutics",
    "chronic pain"
]

# Scraping sources configuration
SOURCES = {
    "sam_gov": {
        "name": "SAM.gov",
        "url": "https://sam.gov/search/?index=opp&keywords=digital%20health",
        "enabled": True
    },
    "undp": {
        "name": "UNDP Procurement",
        "url": "https://procurement-notices.undp.org/view_all_notices",
        "enabled": True
    },
    "ungm": {
        "name": "UNGM",
        "url": "https://www.ungm.org/Public/Notice",
        "enabled": True
    },
    "sourcewell": {
        "name": "Sourcewell",
        "url": "https://www.sourcewell-mn.gov/solicitations",
        "enabled": True
    },
    "gavi": {
        "name": "Gavi",
        "url": "https://www.gavi.org/news-resources/tenders-procurements",
        "enabled": True
    }
}

# Request headers to avoid being blocked
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

# Timeouts and retry settings
REQUEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
