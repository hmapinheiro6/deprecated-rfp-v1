"""
Test script for API-based scraper
Tests each API individually without saving or sending notifications
"""

import os
import sys

# Set environment to avoid notification attempts
os.environ['SLACK_WEBHOOK_URL'] = ''
os.environ['GOOGLE_SHEETS_WEBHOOK_URL'] = ''

from scraper_api import scrape_sam_gov_api, scrape_undp_api, scrape_ungm_api

print("=" * 60)
print("API SCRAPER TEST")
print("=" * 60)
print()

# Check for SAM.gov API key
sam_api_key = os.environ.get('SAM_GOV_API_KEY', '')
if sam_api_key:
    print(f"✓ SAM_GOV_API_KEY is set: {sam_api_key[:10]}...")
else:
    print("⚠ SAM_GOV_API_KEY is NOT set")
    print("  Get a free key at: https://open.gsa.gov/api/opportunities-api/")
    print("  The scraper will still work but may be rate-limited")

print()
print("=" * 60)
print("TESTING SAM.GOV API")
print("=" * 60)

try:
    rfps = scrape_sam_gov_api()
    print(f"\n✓ SAM.gov API test completed")
    print(f"  Found {len(rfps)} relevant RFPs")

    if len(rfps) > 0:
        print(f"\n  Sample RFP:")
        sample = rfps[0]
        print(f"    Title: {sample['title'][:60]}...")
        print(f"    URL: {sample['url']}")
        print(f"    Source: {sample['source']}")
        print(f"    Deadline: {sample['deadline']}")
except Exception as e:
    print(f"\n✗ SAM.gov API test FAILED: {e}")

print()
print("=" * 60)
print("TESTING UNDP API")
print("=" * 60)

try:
    rfps = scrape_undp_api()
    print(f"\n✓ UNDP API test completed")
    print(f"  Found {len(rfps)} relevant RFPs")

    if len(rfps) > 0:
        print(f"\n  Sample RFP:")
        sample = rfps[0]
        print(f"    Title: {sample['title'][:60]}...")
        print(f"    URL: {sample['url']}")
        print(f"    Source: {sample['source']}")
        print(f"    Deadline: {sample['deadline']}")
    else:
        print(f"  (UNDP API may not have public endpoint or no matching RFPs)")
except Exception as e:
    print(f"\n✗ UNDP API test FAILED: {e}")
    print(f"  (This is OK - UNDP may not have a public API)")

print()
print("=" * 60)
print("TESTING UNGM API")
print("=" * 60)

try:
    rfps = scrape_ungm_api()
    print(f"\n✓ UNGM API test completed")
    print(f"  Found {len(rfps)} relevant RFPs")

    if len(rfps) > 0:
        print(f"\n  Sample RFP:")
        sample = rfps[0]
        print(f"    Title: {sample['title'][:60]}...")
        print(f"    URL: {sample['url']}")
        print(f"    Source: {sample['source']}")
        print(f"    Deadline: {sample['deadline']}")
    else:
        print(f"  (UNGM API may not have public endpoint or no matching RFPs)")
except Exception as e:
    print(f"\n✗ UNGM API test FAILED: {e}")
    print(f"  (This is OK - UNGM may not have a public API)")

print()
print("=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print()
print("Next steps:")
print("1. If SAM.gov worked: Great! That's the most important source.")
print("2. If UNDP/UNGM failed: That's expected - they may not have public APIs")
print("3. If ALL failed: Check your internet connection and API key")
print()
print("To run the full scraper with notifications:")
print("  export SLACK_WEBHOOK_URL='your-webhook'")
print("  export GOOGLE_SHEETS_WEBHOOK_URL='your-sheets-webhook'")
print("  export SAM_GOV_API_KEY='your-api-key'")
print("  python scraper_api.py")
print()
