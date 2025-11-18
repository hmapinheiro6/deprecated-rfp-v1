# API-Based Scraper Setup Guide

The API-based scraper (`scraper_api.py`) is **much more reliable** than web scraping because:
- ✅ Works with JavaScript-rendered sites
- ✅ Faster response times
- ✅ Official, documented data structures
- ✅ Won't break when websites redesign
- ✅ Better rate limits and performance

## Quick Start

The scraper has been updated to use `scraper_api.py` which uses official APIs instead of web scraping.

### Required: Get SAM.gov API Key (Free!)

SAM.gov is the most important source (US Government contracts). The API key is **free** and takes 2 minutes to set up:

**Step 1: Register for API Key**

1. Go to https://open.gsa.gov/api/opportunities-api/
2. Click **"Request an API Key"** or go to https://sam.gov/data-services/API
3. Sign up with your email (free, no credit card required)
4. Check your email for the API key
5. Copy the API key (format: `DEMO_KEY` or a long string)

**Step 2: Add to GitHub Secrets**

1. Go to your repository **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Name: `SAM_GOV_API_KEY`
4. Value: Paste your API key
5. Click **Add secret**

**Step 3: Done!**

The scraper will now use the SAM.gov API automatically.

---

## API Sources

### 1. SAM.gov (US Government) ✅

**Status:** Fully implemented
**API Docs:** https://open.gsa.gov/api/opportunities-api/
**Requires API Key:** Yes (free)
**Coverage:** All US federal procurement opportunities

**Features:**
- Searches last 30 days of opportunities
- Returns up to 100 results per request
- Includes title, description, deadlines, notice IDs
- Direct links to opportunity pages

**Setup:**
See "Required: Get SAM.gov API Key" above

---

### 2. UNDP (United Nations) ⚠️

**Status:** Implemented (may need adjustment)
**API Endpoint:** `https://procurement-notices.undp.org/api/notices`
**Requires API Key:** No
**Coverage:** UN Development Programme procurement

**Note:** UNDP may not have a public API or the endpoint may have changed. The scraper attempts to use it, but if it fails, this source will be skipped with a warning in logs.

---

### 3. UNGM (UN Global Marketplace) ⚠️

**Status:** Implemented (may need adjustment)
**API Endpoint:** `https://www.ungm.org/Public/Notice/Search`
**Requires API Key:** No
**Coverage:** Multiple UN agencies, WHO, etc.

**Note:** UNGM's API structure may differ from implementation. If it fails, the source will be skipped with a warning.

---

### 4. Sourcewell ❌

**Status:** Not implemented (no public API)
**Alternative:** Would need RSS feed parsing or custom scraper

---

### 5. Gavi ❌

**Status:** Not implemented (no public API)
**Alternative:** Would need RSS feed parsing or custom scraper

---

## Testing the API Scraper

### Test Locally

```bash
# Set environment variables
export SLACK_WEBHOOK_URL="your-slack-webhook"
export GOOGLE_SHEETS_WEBHOOK_URL="your-sheets-webhook"
export SAM_GOV_API_KEY="your-sam-gov-api-key"
export DEDUP_STORAGE_PATH="data/seen_rfps.json"

# Run the API-based scraper
python scraper_api.py
```

### Test on GitHub Actions

1. Make sure `SAM_GOV_API_KEY` is set in GitHub Secrets
2. Go to **Actions** tab → **Daily RFP Scraper** → **Run workflow**
3. Check the logs for:
   ```
   Starting API-based RFP Scraper for Sword Health
   Scraping SAM.gov via API...
   SAM.gov API response status: 200
   SAM.gov API returned X opportunities
   ```

---

## Troubleshooting

### Issue: SAM.gov returns 401 Unauthorized

**Cause:** API key is missing, invalid, or not set correctly

**Solutions:**
1. Verify `SAM_GOV_API_KEY` is set in GitHub Secrets
2. Check the API key is still valid at https://sam.gov/data-services/API
3. Make sure you copied the entire key (no extra spaces)
4. Try generating a new API key if the old one expired

### Issue: UNDP or UNGM return 0 results

**Cause:** These APIs may not exist publicly or structure has changed

**Solutions:**
1. Check the scraper logs for specific error messages
2. These sources are optional - SAM.gov alone provides good coverage
3. If needed, we can implement RSS feed parsing instead

### Issue: No RFPs found at all

**Possible causes:**
1. No opportunities matching keywords in last 30 days
2. API keys not configured
3. Keywords are too restrictive

**Solutions:**
1. Check logs to see which APIs returned data
2. Temporarily broaden keywords in `config.py` for testing
3. Manually visit SAM.gov to verify there are relevant opportunities

---

## Comparing Web Scraper vs API Scraper

| Feature | `scraper.py` (Old) | `scraper_api.py` (New) |
|---------|-------------------|------------------------|
| **Method** | BeautifulSoup web scraping | Official APIs |
| **Reliability** | ❌ Breaks when sites change | ✅ Stable APIs |
| **JavaScript sites** | ❌ Can't handle | ✅ Works perfectly |
| **Speed** | Slower (HTML parsing) | Faster (JSON responses) |
| **Setup** | No API keys needed | SAM.gov key required (free) |
| **Coverage** | 0-5 sources working | 1-3 sources working reliably |
| **Maintenance** | High (sites change often) | Low (APIs stable) |

---

## Adding More API Sources

Want to add more procurement sources? Here's how:

### 1. Find the API

Look for:
- `/api/` endpoints on the website
- `developers.site.com` or `api.site.com` subdomains
- RSS feeds (can be parsed as pseudo-APIs)
- Public data exports

### 2. Test the API

```bash
# Example: Test an API endpoint
curl -X GET "https://api.example.com/rfps?limit=10" \
  -H "Accept: application/json"
```

### 3. Add to scraper_api.py

```python
def scrape_newsource_api() -> List[Dict]:
    """
    Scrape New Source using their API
    """
    source_name = "New Source"
    logger.info(f"Scraping {source_name} via API...")
    rfps = []

    try:
        response = requests.get(
            "https://api.newsource.com/opportunities",
            params={'limit': 100},
            headers={'Accept': 'application/json'},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        for item in data.get('results', []):
            title = item.get('title', '')
            # ... extract fields ...

            if is_relevant(f"{title} {description}"):
                rfp = create_rfp_dict(...)
                rfps.append(rfp)

    except Exception as e:
        logger.error(f"Error scraping {source_name}: {e}")

    return rfps
```

### 4. Register in scrape_all_sources_api()

```python
def scrape_all_sources_api() -> List[Dict]:
    all_rfps = []

    # ... existing sources ...

    # New source
    try:
        rfps = scrape_newsource_api()
        all_rfps.extend(rfps)
    except Exception as e:
        logger.error(f"Critical error in New Source API: {e}")

    return all_rfps
```

---

## API Rate Limits

| Source | Rate Limit | Notes |
|--------|-----------|-------|
| SAM.gov | 1,000 requests/hour (with key) | More than enough for daily runs |
| UNDP | Unknown | Likely no strict limits |
| UNGM | Unknown | Likely no strict limits |

The scraper runs once daily, so rate limits are not a concern.

---

## Rollback to Web Scraper

If you need to rollback to the web scraper temporarily:

1. Edit `.github/workflows/scrape.yml`
2. Change `python scraper_api.py` to `python scraper.py`
3. Commit and push

**Note:** The web scraper likely won't find any RFPs due to JavaScript rendering issues.

---

## Next Steps

1. ✅ Get your SAM.gov API key (2 minutes)
2. ✅ Add it to GitHub Secrets
3. ✅ Run the workflow manually to test
4. ✅ Check the logs for successful API calls
5. 📧 You should now receive notifications with real RFP data!

---

## Support

If you run into issues:
1. Check the **TROUBLESHOOTING.md** file
2. Run `python debug_scraper.py` for diagnostics
3. Check GitHub Actions logs for error messages
4. Verify all GitHub Secrets are set correctly
