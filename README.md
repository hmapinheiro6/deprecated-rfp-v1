# RFP Scraper for Sword Health

A production-ready, automated RFP (Request for Proposal) scraper that monitors multiple procurement sources daily and delivers relevant opportunities directly to your team via Slack.

## Features

- **Automated Daily Scraping**: Runs automatically every day at 06:00 UTC via GitHub Actions
- **Multiple Sources**: Scrapes 5+ major procurement platforms
- **Smart Filtering**: Filters RFPs using health-tech specific keywords
- **Duplicate Detection**: Tracks seen RFPs to avoid duplicate notifications
- **Slack Integration**: Sends beautifully formatted daily digests to Slack
- **Google Sheets Support**: Optionally appends results to Google Sheets for tracking
- **Zero Cost**: Runs entirely on GitHub Actions free tier
- **Modular Design**: Easy to add or remove scraping sources

## Project Structure

```
rfp-scraper/
├── scraper.py              # Main scraper with source-specific functions
├── config.py               # Keywords and source URLs configuration
├── utils.py                # Helper functions (dedup, parsing, logging)
├── requirements.txt        # Python dependencies
├── data/
│   ├── .gitkeep
│   └── seen_rfps.json     # Auto-generated dedup storage
└── .github/
    └── workflows/
        └── scrape.yml      # GitHub Actions workflow
```

## Scraping Sources

The scraper currently monitors:

1. **SAM.gov** - US Government procurement opportunities
2. **UNDP** - United Nations Development Programme procurement
3. **UNGM** - UN Global Marketplace / WHO procurement
4. **Sourcewell** - Cooperative purchasing solicitations
5. **Gavi** - Global vaccine alliance tenders

## Filtering Keywords

RFPs are filtered using these health-tech relevant keywords:

- digital health
- telehealth
- virtual physical therapy
- musculoskeletal
- msk
- physical therapy
- employee wellness
- digital therapeutics
- chronic pain

Modify the `KEYWORDS` list in `config.py` to adjust filtering.

## Setup Instructions

### 1. Fork/Clone Repository

```bash
git clone https://github.com/yourusername/rfp-scraper.git
cd rfp-scraper
```

### 2. Set Up Slack Webhook

1. Go to your Slack workspace
2. Create a new app at https://api.slack.com/apps
3. Enable "Incoming Webhooks"
4. Create a webhook URL for your desired channel
5. Copy the webhook URL (format: `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX`)

### 3. (Optional) Set Up Google Sheets

If you want to append results to Google Sheets:

1. Create a new Google Cloud Project
2. Enable the Google Sheets API
3. Create a Service Account
4. Download the service account JSON key
5. Create a Google Sheet and share it with the service account email
6. Copy the Sheet ID from the URL (the long string in the middle of the sheet URL)

### 4. Configure GitHub Secrets

In your GitHub repository, go to **Settings → Secrets and variables → Actions** and add:

**Required:**
- `SLACK_WEBHOOK_URL`: Your Slack webhook URL

**Optional (for Google Sheets):**
- `GOOGLE_SERVICE_ACCOUNT_JSON`: Entire contents of your service account JSON file
- `GOOGLE_SHEET_ID`: Your Google Sheet ID

To add the service account JSON:
```bash
# Copy the entire contents of your downloaded JSON file and paste as secret
cat path/to/service-account-key.json
```

### 5. Enable GitHub Actions

1. Go to **Actions** tab in your repository
2. Enable workflows if prompted
3. The scraper will now run automatically every day at 06:00 UTC

## Manual Execution

### Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SLACK_WEBHOOK_URL="your-webhook-url"
export GOOGLE_SERVICE_ACCOUNT_JSON='{"type": "service_account", ...}'
export GOOGLE_SHEET_ID="your-sheet-id"
export DEDUP_STORAGE_PATH="data/seen_rfps.json"

# Run scraper
python scraper.py
```

### Trigger Manual Run on GitHub

1. Go to **Actions** tab
2. Select "Daily RFP Scraper" workflow
3. Click "Run workflow"
4. Click "Run workflow" button

## How Deduplication Works

The scraper uses a JSON file (`data/seen_rfps.json`) to track RFPs that have already been processed:

1. **First Run**: All relevant RFPs are considered "new" and sent to Slack
2. **Subsequent Runs**: Each RFP is assigned a unique ID (MD5 hash of URL + title)
3. **Filtering**: RFPs with IDs that exist in `seen_rfps.json` are filtered out
4. **Updating**: After each run, the file is updated with new RFP IDs
5. **Persistence**: GitHub Actions automatically commits the updated file back to the repository

### Dedup File Format

```json
{
  "seen_ids": [
    "a1b2c3d4e5f6...",
    "f6e5d4c3b2a1..."
  ],
  "last_updated": "2025-01-15T06:00:00",
  "total_count": 142
}
```

### Resetting the Dedup Database

To reset and see all RFPs again (useful for testing):

```bash
# Delete the dedup file
rm data/seen_rfps.json

# Or clear it via GitHub
# Go to repository → data/seen_rfps.json → Delete file
```

## Customization

### Adding a New Scraping Source

1. Add source configuration to `config.py`:

```python
SOURCES = {
    # ... existing sources ...
    "new_source": {
        "name": "New Source Name",
        "url": "https://example.com/rfps",
        "enabled": True
    }
}
```

2. Create scraper function in `scraper.py`:

```python
def scrape_new_source() -> List[Dict]:
    """
    Scrape New Source RFPs

    Returns:
        List of RFP dictionaries
    """
    source_name = "New Source Name"
    logger.info(f"Scraping {source_name}...")
    rfps = []

    soup = fetch_url(SOURCES['new_source']['url'])
    if not soup:
        return rfps

    # Your scraping logic here
    # ...

    return rfps
```

3. Register scraper in `scrape_all_sources()`:

```python
scrapers = {
    # ... existing scrapers ...
    'new_source': scrape_new_source
}
```

### Modifying Keywords

Edit `KEYWORDS` list in `config.py`:

```python
KEYWORDS = [
    "your",
    "custom",
    "keywords"
]
```

### Changing Schedule

Edit the cron expression in `.github/workflows/scrape.yml`:

```yaml
schedule:
  - cron: "0 6 * * *"  # Daily at 06:00 UTC
  # - cron: "0 */6 * * *"  # Every 6 hours
  # - cron: "0 9 * * 1"  # Every Monday at 09:00 UTC
```

## Slack Output Format

The scraper sends formatted messages to Slack with:

- **Header**: "Daily RFP Digest – Sword Health"
- **For each RFP**:
  - Clickable title (linked to source)
  - Source name
  - Publication date
  - Deadline
- **Empty state**: "No new relevant RFPs found today"

## Troubleshooting

### GitHub Actions Fails

1. Check the Actions tab for error logs
2. Verify all secrets are set correctly
3. Ensure the repository has write permissions for workflows

### No RFPs Found

1. Check if sources have changed their HTML structure
2. Verify keywords are appropriate
3. Run locally with debug logging to inspect responses

### Slack Messages Not Sending

1. Verify webhook URL is correct and active
2. Check webhook permissions in Slack app settings
3. Test webhook manually:

```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test message"}' \
  YOUR_WEBHOOK_URL
```

### Google Sheets Not Updating

1. Verify service account has edit access to the sheet
2. Check that sheet ID is correct
3. Ensure Google Sheets API is enabled in GCP project

## Architecture Decisions

### Why BeautifulSoup instead of Selenium?

- **Speed**: BeautifulSoup is much faster
- **Resources**: Works within GitHub Actions free tier limits
- **Simplicity**: No browser dependencies or ChromeDriver management
- **Reliability**: More stable for simple HTML parsing

### Why GitHub Actions?

- **Free**: 2,000 minutes/month on free tier (plenty for daily scraping)
- **No Server**: No need to maintain infrastructure
- **Integrated**: Works seamlessly with Git for dedup storage
- **Reliable**: High uptime and automatic retries

### Why JSON for Dedup Storage?

- **Git-Friendly**: Easy to track changes and merge
- **Human-Readable**: Can manually inspect and edit
- **No Database**: No external dependencies
- **Atomic Updates**: GitHub Actions commits ensure consistency

## Monitoring and Maintenance

### Check Last Run

View workflow runs in the **Actions** tab to see:
- Execution time
- Number of RFPs found
- Any errors or warnings

### Update Dependencies

Regularly update Python packages:

```bash
pip install --upgrade -r requirements.txt
pip freeze > requirements.txt
```

### Review Dedup File Size

The `seen_rfps.json` file will grow over time. Consider periodic cleanup:

```python
# Keep only last 1000 IDs
python -c "
import json
with open('data/seen_rfps.json', 'r') as f:
    data = json.load(f)
data['seen_ids'] = data['seen_ids'][-1000:]
with open('data/seen_rfps.json', 'w') as f:
    json.dump(data, f, indent=2)
"
```

## Contributing

To add new features or sources:

1. Create a feature branch
2. Add your changes
3. Test locally
4. Submit a pull request

## License

MIT License - feel free to use and modify for your organization.

## Support

For issues or questions:
- Open a GitHub issue
- Check workflow logs in Actions tab
- Review error messages in Slack notifications

---

**Built for Sword Health** - Automating the discovery of relevant RFP opportunities in digital health and musculoskeletal care.
