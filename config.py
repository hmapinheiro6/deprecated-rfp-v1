"""
Configuration file for RFP scraper
Contains keywords for filtering and scraper configuration
"""

import os

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
    "chronic pain",
    "Transportation Services Payment Solutions",
    "Fleet Leasing and Vehicle Management Services",
    
]

# Webhook URLs (from environment)
SLACK_WEBHOOK = os.getenv('SLACK_WEBHOOK_URL')
GOOGLE_SHEETS_WEBHOOK = os.getenv('GOOGLE_SHEETS_WEBHOOK_URL')
SAM_GOV_API_KEY = os.getenv('SAM_GOV_API_KEY')

# Scraper enable/disable config
# method: 'api' = API-based, 'selenium' = Selenium scraping, 'scrape' = BeautifulSoup
SCRAPERS = {
    'sam_gov': {
        'enabled': True,  # ONLY SAM.gov enabled for now
        'method': 'api',
        'name': 'SAM.gov'
    },
    'undp': {
        'enabled': False,  # DISABLED - will enable after SAM.gov works
        'method': 'api',
        'name': 'UNDP Procurement'
    },
    'ungm': {
        'enabled': False,  # DISABLED - will enable after SAM.gov works
        'method': 'api',
        'name': 'UNGM'
    },
    'sourcewell': {
        'enabled': False,  # DISABLED - will enable after SAM.gov works
        'method': 'selenium',
        'name': 'Sourcewell'
    },
    'gavi': {
        'enabled': False,  # DISABLED - will enable after SAM.gov works
        'method': 'selenium',
        'name': 'Gavi'
    }
}

# Legacy SOURCES config (kept for backward compatibility with old scripts)
SOURCES = {
    "sam_gov": {
        "name": "SAM.gov",
        "url": "https://sam.gov/search/?index=opp&keywords=digital%20health",
        "enabled": True
    },
    "undp": {
        "name": "UNDP Procurement",
        "url": "https://procurement-notices.undp.org/",
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
        "enabled": False
    },
    "gavi": {
        "name": "Gavi",
        "url": "https://www.gavi.org/our-alliance/work-us/rfps-eois-and-consulting-opportunities",
        "enabled": False
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
