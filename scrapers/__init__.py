"""
Scrapers package - modular procurement scrapers

Each scraper is independent and can be enabled/disabled via config
"""

from .sam_gov import SamGovScraper
from .undp import UndpScraper
from .ungm import UngmScraper

__all__ = [
    'SamGovScraper',
    'UndpScraper',
    'UngmScraper',
]
