"""
Slack notification module
Handles sending RFP digests to Slack via webhooks
Supports both Slack Workflows and traditional Incoming Webhooks
"""

import os
import requests
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def build_slack_workflow_payload(rfps: List[Dict]) -> Dict:
    """
    Build Slack Workflow webhook payload from RFP list
    This format is for Slack Workflows with webhook triggers

    Args:
        rfps: List of RFP dictionaries

    Returns:
        Simple key-value payload for Slack Workflows
    """
    if not rfps:
        return {
            "count": 0,
            "message": "No new relevant RFPs found today.",
            "rfps": []
        }

    # Build a formatted text summary
    rfp_list = []
    for rfp in rfps:
        rfp_list.append({
            "title": rfp.get("title", "Untitled RFP"),
            "url": rfp.get("url", ""),
            "source": rfp.get("source", "Unknown"),
            "published": rfp.get("posted_date", "N/A"),
            "deadline": rfp.get("response_date", "N/A")
        })

    # Create a text summary for the workflow
    summary = f"Found {len(rfps)} new relevant RFP(s) for Sword Health:\n\n"
    for i, rfp in enumerate(rfps[:10], 1):  # Limit to 10 in summary
        summary += f"{i}. {rfp.get('title', 'Untitled')} ({rfp.get('source', 'Unknown')})\n"
        summary += f"   Deadline: {rfp.get('response_date', 'N/A')}\n"
        summary += f"   {rfp.get('url', '')}\n\n"

    if len(rfps) > 10:
        summary += f"... and {len(rfps) - 10} more RFPs"

    return {
        "count": len(rfps),
        "message": summary,
        "rfps": rfp_list
    }


def build_slack_blocks_payload(rfps: List[Dict]) -> Dict:
    """
    Build Slack message payload with blocks (for traditional Incoming Webhooks)

    Args:
        rfps: List of RFP dictionaries

    Returns:
        Slack-formatted payload with blocks
    """
    if not rfps:
        text = "No new relevant RFPs found today."
        return {
            "text": text,
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": text}
                }
            ]
        }

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Daily RFP Digest – Sword Health",
                "emoji": True
            }
        },
        {"type": "divider"}
    ]

    for rfp in rfps:
        title = rfp.get("title", "Untitled RFP")
        url = rfp.get("url", "")
        source = rfp.get("source", "Unknown source")
        publish_date = rfp.get("posted_date", "N/A")
        deadline = rfp.get("response_date", "N/A")

        text = (
            f"*<{url}|{title}>*\n"
            f"*Source:* {source}\n"
            f"*Published:* {publish_date}   •   *Deadline:* {deadline}"
        )

        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text
                }
            }
        )
        blocks.append({"type": "divider"})

    return {
        "text": "Daily RFP Digest – Sword Health",
        "blocks": blocks
    }


def send_to_slack(rfps: List[Dict], test_mode: bool = False) -> bool:
    """
    Send RFP digest to Slack via webhook
    Auto-detects Slack Workflow webhooks vs traditional Incoming Webhooks

    Args:
        rfps: List of RFP dictionaries
        test_mode: If True, skip actual sending (for testing)

    Returns:
        True if successful, False otherwise
    """
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL', '').strip()

    if not webhook_url:
        logger.warning("SLACK_WEBHOOK_URL not set, skipping Slack notification")
        logger.warning("Set SLACK_WEBHOOK_URL environment variable to enable Slack notifications")
        return False

    if test_mode:
        logger.info("TEST MODE: Would send Slack notification but skipping")
        logger.info(f"  RFPs: {len(rfps)}")
        logger.info(f"  Webhook: {webhook_url[:50]}...")
        return True

    logger.info(f"Attempting to send Slack notification (RFP count: {len(rfps)})")
    logger.debug(f"Webhook URL starts with: {webhook_url[:50]}...")

    try:
        # Detect webhook type by URL pattern
        # Slack Workflow webhooks contain '/workflows/' in the URL
        is_workflow = '/workflows/' in webhook_url

        if is_workflow:
            logger.info("Detected Slack Workflow webhook, using simple payload format")
            payload = build_slack_workflow_payload(rfps)
        else:
            logger.info("Detected traditional Slack webhook, using blocks format")
            payload = build_slack_blocks_payload(rfps)

        logger.debug(f"Payload size: {len(str(payload))} characters")

        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10
        )

        logger.info(f"Slack API response status: {response.status_code}")
        logger.debug(f"Slack API response: {response.text[:200]}")

        response.raise_for_status()
        logger.info(f"✓ Successfully sent notification with {len(rfps)} RFPs to Slack")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"✗ HTTP error sending to Slack: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text[:500]}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error sending to Slack: {e}")
        return False
