"""
Google Sheets notification module
Handles sending RFP data to Google Sheets via Apps Script webhook
Updates both RFPs sheet and Activity Log sheet
"""

import os
import requests
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def send_to_google_sheets(rfps: List[Dict], test_mode: bool = False) -> bool:
    """
    Append RFPs to Google Sheets via Apps Script webhook
    This is the SIMPLE method - no Google Cloud credentials needed!

    Note: This function ALWAYS sends data to update the Activity Log,
    even when there are 0 new RFPs.

    Args:
        rfps: List of RFP dictionaries
        test_mode: If True, skip actual sending (for testing)

    Returns:
        True if successful, False otherwise
    """
    webhook_url = os.environ.get('GOOGLE_SHEETS_WEBHOOK_URL', '').strip()

    if not webhook_url:
        logger.info("GOOGLE_SHEETS_WEBHOOK_URL not set, skipping Sheets update")
        logger.info("Set GOOGLE_SHEETS_WEBHOOK_URL environment variable to enable Google Sheets tracking")
        return False

    if test_mode:
        logger.info("TEST MODE: Would send to Google Sheets but skipping")
        logger.info(f"  RFPs: {len(rfps)}")
        logger.info(f"  Webhook: {webhook_url[:50]}...")
        return True

    logger.info(f"Attempting to update Google Sheets (RFP count: {len(rfps)})")
    logger.debug(f"Webhook URL starts with: {webhook_url[:50]}...")

    try:
        # Prepare payload
        # Always send, even with empty list, to update Activity Log
        # Map from new format to Google Sheets expected format
        payload = {
            'rfps': [
                {
                    'title': rfp.get('title', ''),
                    'url': rfp.get('url', ''),
                    'source': rfp.get('source', ''),
                    'publish_date': rfp.get('posted_date', 'N/A'),  # Map posted_date -> publish_date
                    'deadline': rfp.get('response_date', 'N/A'),     # Map response_date -> deadline
                    'snippet': rfp.get('description', '')[:300]       # Map description -> snippet (truncate)
                }
                for rfp in rfps
            ]
        }

        logger.debug(f"Payload size: {len(str(payload))} characters")

        response = requests.post(
            webhook_url,
            json=payload,
            timeout=30
        )

        logger.info(f"Google Sheets API response status: {response.status_code}")
        logger.debug(f"Google Sheets API response: {response.text[:200]}")

        response.raise_for_status()

        try:
            result = response.json()
            logger.debug(f"Response JSON: {result}")
        except:
            logger.debug("Response is not JSON")

        if len(rfps) > 0:
            logger.info(f"✓ Successfully appended {len(rfps)} RFPs to Google Sheets via webhook")
        else:
            logger.info("✓ Updated Google Sheets Activity Log (0 new RFPs)")

        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"✗ HTTP error sending to Google Sheets: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")

            # Provide helpful error messages based on status code
            if e.response.status_code == 404:
                logger.error("=" * 60)
                logger.error("❌ 404 Error - Apps Script webhook not found")
                logger.error("")
                logger.error("⚠️  ACTION REQUIRED - Setup Google Sheets Webhook:")
                logger.error("   1. Open your Google Sheet")
                logger.error("   2. Go to Extensions → Apps Script")
                logger.error("   3. Paste the webhook code from google-apps-script-webhook.js")
                logger.error("   4. Click Deploy → New deployment")
                logger.error("   5. Click gear icon ⚙️ → Select 'Web app'")
                logger.error("   6. Configure:")
                logger.error("      • Execute as: Me")
                logger.error("      • Who has access: Anyone")
                logger.error("   7. Click 'Deploy'")
                logger.error("   8. Copy the Web App URL (ends with /exec)")
                logger.error("   9. Add to GitHub Secrets: GOOGLE_SHEETS_WEBHOOK_URL")
                logger.error("")
                logger.error("⚠️  IMPORTANT: Use the /exec URL, NOT /dev URL")
                logger.error("=" * 60)
            elif e.response.status_code == 403:
                logger.error("=" * 60)
                logger.error("❌ 403 Forbidden - Permission denied")
                logger.error("Check that the Apps Script deployment:")
                logger.error("  • Has 'Who has access' set to 'Anyone'")
                logger.error("  • Is deployed (not just saved)")
                logger.error("=" * 60)
            else:
                logger.error(f"Response body: {e.response.text[:500]}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error appending to Google Sheets webhook: {e}")
        return False
