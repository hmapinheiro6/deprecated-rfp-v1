"""
Test script to diagnose which sources are working
This will test each scraping source individually
"""

import requests
from bs4 import BeautifulSoup
from config import SOURCES, HEADERS

def test_source(name, url):
    """Test if a source is accessible and returns content"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"{'='*60}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        print(f"✓ Status Code: {response.status_code}")
        print(f"✓ Content Length: {len(response.content)} bytes")

        soup = BeautifulSoup(response.content, 'html.parser')

        # Check for common elements
        title = soup.find('title')
        print(f"✓ Page Title: {title.get_text(strip=True) if title else 'No title found'}")

        # Check for divs
        divs = soup.find_all('div')
        print(f"✓ Total <div> elements: {len(divs)}")

        # Check for links
        links = soup.find_all('a')
        print(f"✓ Total <a> elements: {len(links)}")

        # Check for common patterns
        patterns = ['result', 'opportunity', 'notice', 'listing', 'tender', 'procurement']
        for pattern in patterns:
            count = sum(1 for elem in soup.find_all() if elem.get('class') and any(pattern in str(c).lower() for c in elem.get('class')))
            if count > 0:
                print(f"  - Found {count} elements with class containing '{pattern}'")

        # Sample some content
        text_content = soup.get_text()
        if 'digital' in text_content.lower() or 'health' in text_content.lower():
            print(f"✓ Contains health-related keywords")
        else:
            print(f"⚠ No obvious health keywords found in content")

        # Check if it's a JavaScript-heavy page
        scripts = soup.find_all('script')
        print(f"✓ Total <script> tags: {len(scripts)}")
        if len(scripts) > 10 and len(divs) < 50:
            print(f"⚠ WARNING: Likely JavaScript-rendered content (BeautifulSoup won't see it)")

        # Show first 500 chars of body
        body = soup.find('body')
        if body:
            body_text = body.get_text(strip=True)[:500]
            print(f"\nFirst 500 chars of body:")
            print(f"{body_text}...")

        return True

    except requests.exceptions.Timeout:
        print(f"✗ TIMEOUT: Request took longer than 30 seconds")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"✗ CONNECTION ERROR: {e}")
        return False
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False

def main():
    print("="*60)
    print("RFP SCRAPER SOURCE DIAGNOSTICS")
    print("="*60)

    results = {}

    for key, config in SOURCES.items():
        if config.get('enabled', True):
            success = test_source(config['name'], config['url'])
            results[config['name']] = success

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for name, success in results.items():
        status = "✓ ACCESSIBLE" if success else "✗ FAILED"
        print(f"{name}: {status}")

    print(f"\n{'='*60}")
    print("RECOMMENDATIONS")
    print(f"{'='*60}")
    print("If sources show 'JavaScript-rendered content':")
    print("  - These sources need Selenium or API access")
    print("  - BeautifulSoup cannot scrape JavaScript-rendered pages")
    print("\nIf sources are accessible but scraper finds 0 RFPs:")
    print("  - HTML structure doesn't match the generic patterns")
    print("  - Need to inspect each site and write custom parsing logic")
    print("\nNext steps:")
    print("  1. Run this script: python test_sources.py")
    print("  2. Check which sources are accessible")
    print("  3. Manually inspect HTML structure of working sources")
    print("  4. Update scraper functions with correct selectors")

if __name__ == "__main__":
    main()
