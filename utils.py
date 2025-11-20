"""
Utility functions for RFP scraper
Handles deduplication, parsing, logging, and data storage
"""

import json
import os
import logging
import hashlib
from datetime import datetime
from typing import List, Dict, Set
from config import KEYWORDS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def setup_data_directory(path: str) -> None:
    """
    Ensure the data directory exists

    Args:
        path: Path to the deduplication storage file
    """
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")


def load_seen_rfps(storage_path: str) -> Set[str]:
    """
    Load previously seen RFP IDs from storage

    Args:
        storage_path: Path to JSON file storing seen RFP IDs

    Returns:
        Set of RFP IDs that have been seen before
    """
    if not os.path.exists(storage_path):
        logger.info(f"No existing dedup file found at {storage_path}, starting fresh")
        return set()

    try:
        with open(storage_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            seen_ids = set(data.get('seen_ids', []))
            logger.info(f"Loaded {len(seen_ids)} previously seen RFP IDs")
            return seen_ids
    except Exception as e:
        logger.error(f"Error loading seen RFPs: {e}")
        return set()


def save_seen_rfps(storage_path: str, seen_ids: Set[str]) -> None:
    """
    Save seen RFP IDs to storage

    Args:
        storage_path: Path to JSON file for storing seen RFP IDs
        seen_ids: Set of RFP IDs to save
    """
    try:
        setup_data_directory(storage_path)
        data = {
            'seen_ids': list(seen_ids),
            'last_updated': datetime.utcnow().isoformat(),
            'total_count': len(seen_ids)
        }
        with open(storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(seen_ids)} seen RFP IDs to {storage_path}")
    except Exception as e:
        logger.error(f"Error saving seen RFPs: {e}")


def generate_rfp_id(url: str, title: str = "") -> str:
    """
    Generate a unique ID for an RFP based on its URL and title

    Args:
        url: RFP URL
        title: RFP title (optional)

    Returns:
        MD5 hash of the URL and title
    """
    # Use URL as primary identifier, title as secondary
    identifier = f"{url}|{title}".encode('utf-8')
    return hashlib.md5(identifier).hexdigest()


def is_relevant(text: str) -> bool:
    """
    Check if text contains any of the relevant keywords

    Args:
        text: Text to check (title or description)

    Returns:
        True if any keyword is found (case-insensitive)
    """
    if not text:
        return False

    text_lower = text.lower()
    for keyword in KEYWORDS:
        if keyword.lower() in text_lower:
            logger.debug(f"Matched keyword '{keyword}' in text")
            return True
    return False


def filter_new_rfps(rfps: List[Dict], seen_ids: Set[str]) -> List[Dict]:
    """
    Filter out RFPs that have been seen before

    Args:
        rfps: List of RFP dictionaries
        seen_ids: Set of previously seen RFP IDs

    Returns:
        List of new RFPs only
    """
    new_rfps = [rfp for rfp in rfps if rfp.get('id') not in seen_ids]
    logger.info(f"Filtered {len(rfps)} RFPs down to {len(new_rfps)} new ones")
    return new_rfps


def clean_text(text: str, max_length: int = None) -> str:
    """
    Clean and normalize text

    Args:
        text: Text to clean
        max_length: Maximum length to truncate to

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Remove extra whitespace
    cleaned = ' '.join(text.split())

    # Truncate if needed
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "..."

    return cleaned


def parse_date(date_str: str) -> str:
    """
    Parse and normalize date strings

    Args:
        date_str: Date string in various formats

    Returns:
        Normalized date string or original if parsing fails
    """
    if not date_str:
        return "N/A"

    # Common date formats to try
    date_formats = [
        '%Y-%m-%d',
        '%d-%m-%Y',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%B %d, %Y',
        '%b %d, %Y',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%SZ'
    ]

    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    # If no format matches, return cleaned original
    return clean_text(date_str)


def create_rfp_dict(
    title: str,
    url: str,
    source: str,
    publish_date: str = "N/A",
    deadline: str = "N/A",
    snippet: str = ""
) -> Dict:
    """
    Create a standardized RFP dictionary

    Args:
        title: RFP title
        url: RFP URL
        source: Source name
        publish_date: Publication date
        deadline: Submission deadline
        snippet: Description snippet

    Returns:
        Standardized RFP dictionary
    """
    rfp_id = generate_rfp_id(url, title)

    return {
        'id': rfp_id,
        'title': clean_text(title, max_length=200),
        'url': url,
        'source': source,
        'publish_date': parse_date(publish_date),
        'deadline': parse_date(deadline) if deadline else "N/A",
        'snippet': clean_text(snippet, max_length=300)
    }


def safe_get_text(element, default: str = "") -> str:
    """
    Safely extract text from a BeautifulSoup element

    Args:
        element: BeautifulSoup element or None
        default: Default value if element is None

    Returns:
        Text content or default
    """
    if element is None:
        return default
    try:
        return element.get_text(strip=True)
    except Exception:
        return default


def safe_get_attr(element, attr: str, default: str = "") -> str:
    """
    Safely extract an attribute from a BeautifulSoup element

    Args:
        element: BeautifulSoup element or None
        attr: Attribute name
        default: Default value if element is None or attribute missing

    Returns:
        Attribute value or default
    """
    if element is None:
        return default
    try:
        return element.get(attr, default)
    except Exception:
        return default


def save_debug_html(content: str, scraper_name: str, success: bool = False) -> str:
    """
    Save HTML content for debugging scraper issues

    Args:
        content: HTML content to save
        scraper_name: Name of the scraper (for filename)
        success: Whether the scrape was successful (adds to filename)

    Returns:
        Path to saved file
    """
    try:
        # Create debug directory if it doesn't exist
        debug_dir = "debug_html"
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)

        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        status = "success" if success else "failed"
        filename = f"{scraper_name}_{status}_{timestamp}.html"
        filepath = os.path.join(debug_dir, filename)

        # Save content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"📄 Debug HTML saved to: {filepath}")
        return filepath

    except Exception as e:
        logger.error(f"Failed to save debug HTML: {e}")
        return ""
