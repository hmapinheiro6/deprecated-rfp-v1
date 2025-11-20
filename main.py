"""
Main orchestrator for RFP scraper
Coordinates all scrapers and notifications
"""

import os
import sys
import logging
import argparse
from typing import List, Dict
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Import configuration
from config import SCRAPERS

# Import scrapers
from scrapers import SamGovScraper, UndpScraper, UngmScraper, SourcewellScraper, GaviScraper

# Import notifications
from notifications import send_to_slack, send_to_google_sheets

# Import utilities (deduplication, etc.)
from utils import (
    load_seen_rfps,
    save_seen_rfps,
    generate_rfp_id,
)


def filter_new_rfps(rfps: List[Dict], seen_ids: set) -> List[Dict]:
    """
    Filter out RFPs that have been seen before

    Args:
        rfps: List of RFP dictionaries
        seen_ids: Set of previously seen RFP IDs

    Returns:
        List of new RFPs only
    """
    new_rfps = []

    for rfp in rfps:
        # Generate ID from URL and title
        rfp_id = generate_rfp_id(rfp.get('url', ''), rfp.get('title', ''))

        # Add ID to RFP for tracking
        rfp['id'] = rfp_id

        # Check if new
        if rfp_id not in seen_ids:
            new_rfps.append(rfp)

    logger.info(f"Filtered {len(rfps)} RFPs down to {len(new_rfps)} new ones")
    return new_rfps


def run_scrapers(filter_scraper: str = None) -> List[Dict]:
    """
    Run all enabled scrapers and aggregate results

    Args:
        filter_scraper: If provided, only run this specific scraper

    Returns:
        List of all RFPs found across all scrapers
    """
    all_rfps = []

    # Map scraper names to classes
    scraper_classes = {
        'sam_gov': SamGovScraper,
        'undp': UndpScraper,
        'ungm': UngmScraper,
        'sourcewell': SourcewellScraper,
        'gavi': GaviScraper,
    }

    for scraper_key, config in SCRAPERS.items():
        # If filter_scraper specified, only run that one
        if filter_scraper and scraper_key != filter_scraper:
            continue

        if not config.get('enabled', False):
            if filter_scraper == scraper_key:
                logger.warning(f"{config.get('name', scraper_key)} is disabled in config, but running anyway due to --scraper flag")
            else:
                logger.info(f"Skipping {config.get('name', scraper_key)} (disabled in config)")
                continue

        # Get scraper class
        scraper_class = scraper_classes.get(scraper_key)

        if not scraper_class:
            logger.warning(f"Scraper {scraper_key} is enabled but not implemented yet")
            continue

        # Instantiate and run scraper
        try:
            logger.info(f"Running scraper: {config.get('name', scraper_key)}")
            scraper = scraper_class(enabled=True)
            rfps = scraper.scrape()
            all_rfps.extend(rfps)

        except Exception as e:
            logger.error(f"Critical error running {scraper_key} scraper: {e}", exc_info=True)
            continue

    logger.info(f"Total RFPs found across all scrapers: {len(all_rfps)}")
    return all_rfps


def main():
    """
    Main execution function
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='RFP Scraper for Sword Health')
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode - run scrapers but skip sending notifications'
    )
    parser.add_argument(
        '--scraper',
        type=str,
        help='Test only specific scraper (e.g., "sam_gov", "undp", "ungm", "sourcewell", "gavi")'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode (saves HTML for inspection, verbose logging)'
    )
    args = parser.parse_args()

    test_mode = args.test
    single_scraper = args.scraper
    debug_mode = args.debug

    # Set debug HTML environment variable if debug mode
    if debug_mode:
        os.environ['SAVE_DEBUG_HTML'] = 'true'
        logger.info("Debug mode enabled - HTML will be saved to debug_html/ directory")

    # Log startup
    logger.info("=" * 60)
    logger.info("Starting RFP Scraper for Sword Health")
    logger.info(f"Timestamp: {datetime.utcnow().isoformat()}")
    logger.info(f"Mode: {'TEST' if test_mode else 'PRODUCTION'}")
    if single_scraper:
        logger.info(f"Running single scraper: {single_scraper}")
    if debug_mode:
        logger.info(f"Debug mode: ENABLED")
    logger.info("=" * 60)

    # Get dedup storage path
    storage_path = os.environ.get('DEDUP_STORAGE_PATH', 'data/seen_rfps.json')

    # Load previously seen RFP IDs
    seen_ids = load_seen_rfps(storage_path)

    # Run scrapers (all enabled, or just one if --scraper specified)
    all_rfps = run_scrapers(filter_scraper=single_scraper)

    # Validate single_scraper if specified
    if single_scraper and len(all_rfps) == 0:
        logger.warning(f"Scraper '{single_scraper}' found 0 RFPs. This might be normal or indicate an issue.")
        logger.warning(f"Valid scraper names: sam_gov, undp, ungm, sourcewell, gavi")

    # Filter out previously seen RFPs
    new_rfps = filter_new_rfps(all_rfps, seen_ids)

    # Update seen IDs
    for rfp in all_rfps:
        if 'id' in rfp:
            seen_ids.add(rfp['id'])

    # Save updated seen IDs
    save_seen_rfps(storage_path, seen_ids)

    # Send results
    logger.info("=" * 60)
    logger.info(f"Processing {len(new_rfps)} new RFPs (Total scraped: {len(all_rfps)})")
    logger.info("=" * 60)

    # Send to Slack (always send, even if 0 new RFPs)
    if len(new_rfps) == 0:
        logger.info("No new RFPs found - sending empty notification")
    else:
        logger.info(f"Found {len(new_rfps)} new RFPs - sending notifications")

    slack_success = send_to_slack(new_rfps, test_mode=test_mode)

    # Send to Google Sheets (always send to update Activity Log)
    logger.info("")
    sheets_success = send_to_google_sheets(new_rfps, test_mode=test_mode)

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("SCRAPER RUN SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total RFPs scraped: {len(all_rfps)}")
    logger.info(f"New RFPs found: {len(new_rfps)}")

    if test_mode:
        logger.info("Slack notification: SKIPPED (test mode)")
        logger.info("Google Sheets update: SKIPPED (test mode)")
    else:
        logger.info(f"Slack notification: {'✓ SENT' if slack_success else '✗ FAILED (check logs above)'}")
        logger.info(f"Google Sheets update: {'✓ SENT' if sheets_success else '✗ FAILED (check logs above)'}")

    logger.info("=" * 60)

    # Exit with appropriate code
    if test_mode:
        logger.info("Test run completed successfully!")
        sys.exit(0)
    elif slack_success or sheets_success:
        logger.info("Production run completed successfully!")
        sys.exit(0)
    else:
        logger.error("Production run completed but notifications failed!")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nScraper interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
