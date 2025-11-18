"""
Debug script to test the scraper components
Run this to diagnose issues with the scraper
"""

import os
import sys
import json

# Check environment variables
print("=" * 60)
print("ENVIRONMENT VARIABLES CHECK")
print("=" * 60)

slack_url = os.environ.get('SLACK_WEBHOOK_URL')
sheets_url = os.environ.get('GOOGLE_SHEETS_WEBHOOK_URL')
dedup_path = os.environ.get('DEDUP_STORAGE_PATH', 'data/seen_rfps.json')

print(f"SLACK_WEBHOOK_URL: {'✓ SET' if slack_url else '✗ NOT SET'}")
if slack_url:
    print(f"  Type: {'Workflow' if '/workflows/' in slack_url else 'Traditional'}")
    print(f"  URL starts with: {slack_url[:50]}...")

print(f"GOOGLE_SHEETS_WEBHOOK_URL: {'✓ SET' if sheets_url else '✗ NOT SET'}")
if sheets_url:
    print(f"  URL starts with: {sheets_url[:50]}...")

print(f"DEDUP_STORAGE_PATH: {dedup_path}")
print()

# Check dedup file
print("=" * 60)
print("DEDUP FILE CHECK")
print("=" * 60)

if os.path.exists(dedup_path):
    try:
        with open(dedup_path, 'r') as f:
            dedup_data = json.load(f)
        seen_count = len(dedup_data.get('seen_ids', []))
        last_updated = dedup_data.get('last_updated', 'Unknown')
        print(f"✓ Dedup file exists")
        print(f"  Seen RFPs: {seen_count}")
        print(f"  Last updated: {last_updated}")
    except Exception as e:
        print(f"✗ Error reading dedup file: {e}")
else:
    print(f"✗ Dedup file does not exist at: {dedup_path}")
print()

# Test imports
print("=" * 60)
print("IMPORTS CHECK")
print("=" * 60)

try:
    import requests
    print("✓ requests imported")
except ImportError as e:
    print(f"✗ requests import failed: {e}")

try:
    from bs4 import BeautifulSoup
    print("✓ BeautifulSoup imported")
except ImportError as e:
    print(f"✗ BeautifulSoup import failed: {e}")

try:
    from scraper import send_to_slack, append_to_google_sheets_webhook
    print("✓ scraper functions imported")
except ImportError as e:
    print(f"✗ scraper import failed: {e}")
    sys.exit(1)

print()

# Test empty RFP notifications
print("=" * 60)
print("TESTING EMPTY RFP NOTIFICATIONS")
print("=" * 60)

test_rfps = []

print("\nTesting Slack notification with 0 RFPs...")
try:
    result = send_to_slack(test_rfps)
    print(f"  Result: {'✓ SUCCESS' if result else '✗ FAILED'}")
except Exception as e:
    print(f"  ✗ Exception: {e}")

print("\nTesting Google Sheets webhook with 0 RFPs...")
try:
    result = append_to_google_sheets_webhook(test_rfps)
    print(f"  Result: {'✓ SUCCESS' if result else '✗ FAILED'}")
except Exception as e:
    print(f"  ✗ Exception: {e}")

print()

# Test with sample RFP
print("=" * 60)
print("TESTING WITH SAMPLE RFP")
print("=" * 60)

sample_rfps = [{
    'id': 'test123',
    'title': 'Test RFP - Digital Health Platform',
    'url': 'https://example.com/test',
    'source': 'Debug Test',
    'publish_date': '2025-01-17',
    'deadline': '2025-02-28',
    'snippet': 'This is a test RFP for debugging'
}]

print("\nTesting Slack notification with 1 sample RFP...")
try:
    result = send_to_slack(sample_rfps)
    print(f"  Result: {'✓ SUCCESS' if result else '✗ FAILED'}")
except Exception as e:
    print(f"  ✗ Exception: {e}")

print("\nTesting Google Sheets webhook with 1 sample RFP...")
try:
    result = append_to_google_sheets_webhook(sample_rfps)
    print(f"  Result: {'✓ SUCCESS' if result else '✗ FAILED'}")
except Exception as e:
    print(f"  ✗ Exception: {e}")

print()
print("=" * 60)
print("DEBUG COMPLETE")
print("=" * 60)
print("\nIf both tests show FAILED, check:")
print("1. Environment variables are set correctly")
print("2. Webhook URLs are valid and accessible")
print("3. Slack/Google Sheets webhooks are properly configured")
print("\nFor GitHub Actions, check the workflow logs for similar output")
