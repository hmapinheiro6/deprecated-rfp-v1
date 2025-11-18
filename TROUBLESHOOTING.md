# Troubleshooting Guide for RFP Scraper

## Quick Diagnostics

### 1. Run the Debug Script Locally

```bash
# Set your environment variables
export SLACK_WEBHOOK_URL="your-webhook-url"
export GOOGLE_SHEETS_WEBHOOK_URL="your-sheets-webhook-url"

# Run the debug script
python debug_scraper.py
```

This will show you:
- Whether environment variables are set
- Whether the dedup file exists and is valid
- Whether imports work
- Whether webhooks are accessible

### 2. Check GitHub Actions Logs

1. Go to your repository on GitHub
2. Click the **Actions** tab
3. Click on the most recent workflow run
4. Click on the "scrape" job
5. Expand the "Run scraper" step
6. Look for the **SCRAPER RUN SUMMARY** section at the end

The summary will show:
```
============================================================
SCRAPER RUN SUMMARY
============================================================
Total RFPs scraped: X
New RFPs found: Y
Slack notification: ✓ SENT / ✗ FAILED
Google Sheets update: ✓ SENT / ✗ FAILED
============================================================
```

## Common Issues and Solutions

### Issue 1: Environment Variables Not Set

**Symptoms:**
- Logs show: "SLACK_WEBHOOK_URL not set, skipping Slack notification"
- Logs show: "GOOGLE_SHEETS_WEBHOOK_URL not set, skipping Sheets update"

**Solution:**
1. Go to GitHub repository **Settings → Secrets and variables → Actions**
2. Verify these secrets exist:
   - `SLACK_WEBHOOK_URL`
   - `GOOGLE_SHEETS_WEBHOOK_URL` (optional)
3. Make sure secret names are EXACT (case-sensitive)
4. Re-run the workflow after adding secrets

### Issue 2: All RFPs Already Seen (0 New RFPs)

**Symptoms:**
- Logs show: "Found 0 new RFPs"
- But you expected to see some

**Explanation:**
The scraper maintains a dedup file (`data/seen_rfps.json`) that tracks all RFPs it has ever seen. On subsequent runs, only truly NEW RFPs are reported.

**Solution:**
To reset and see all RFPs again:

```bash
# Delete the dedup file
rm data/seen_rfps.json
git add data/seen_rfps.json
git commit -m "Reset dedup database"
git push
```

Or via GitHub:
1. Navigate to `data/seen_rfps.json` in your repository
2. Click the trash icon to delete it
3. Commit the deletion
4. Next run will treat all RFPs as "new"

### Issue 3: Slack Webhook Returns Error

**Symptoms:**
- Logs show: "✗ HTTP error sending to Slack"
- Response status: 404, 401, or 403

**Solutions:**

**For Slack Workflows:**
1. Check that workflow is **Published** (not draft)
2. Verify webhook URL ends with `/exec` (not `/dev`)
3. Make sure variables in workflow match: `count`, `message`, `rfps`
4. Test manually:
   ```bash
   curl -X POST -H 'Content-type: application/json' \
     -d '{"count": 0, "message": "Test", "rfps": []}' \
     YOUR_WORKFLOW_URL
   ```

**For Traditional Webhooks:**
1. Verify the webhook hasn't been revoked
2. Check app permissions in Slack
3. Test manually:
   ```bash
   curl -X POST -H 'Content-type: application/json' \
     -d '{"text": "Test message"}' \
     YOUR_WEBHOOK_URL
   ```

### Issue 4: Google Sheets Webhook Returns Error

**Symptoms:**
- Logs show: "✗ HTTP error sending to Google Sheets"
- Response status: 302, 403, or 500

**Solutions:**

1. **Check deployment settings:**
   - Open Apps Script editor
   - Go to **Deploy → Manage deployments**
   - Verify "Who has access" is set to **Anyone**
   - If it says "Anyone with Google account", change to **Anyone**

2. **Verify the webhook URL:**
   - Should end with `/exec` (NOT `/dev`)
   - Should start with `https://script.google.com/macros/s/`

3. **Test the webhook manually:**
   ```bash
   curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"rfps": []}' \
     YOUR_APPS_SCRIPT_URL
   ```

4. **Check Apps Script execution logs:**
   - Open your sheet → **Extensions → Apps Script**
   - Click **Executions** (clock icon on left)
   - Look for recent executions and any errors

### Issue 5: No RFPs Being Scraped (Total = 0)

**Symptoms:**
- Logs show: "Total RFPs scraped: 0"
- All sources returning 0 RFPs

**Possible Causes:**
1. **Network issues:** GitHub Actions can't reach external sites
2. **Source websites changed:** HTML structure changed
3. **Keywords too restrictive:** No RFPs match your keywords

**Solutions:**

1. **Test locally first:**
   ```bash
   python scraper.py
   ```

2. **Check if sources are accessible:**
   ```bash
   curl -I https://sam.gov
   curl -I https://procurement-notices.undp.org
   ```

3. **Try broadening keywords temporarily:**
   Edit `config.py` and add more general terms, then test again

4. **Check source-specific logs:**
   Look for lines like "Scraping SAM.gov..." and see if they report errors

### Issue 6: Workflow Not Running on Schedule

**Symptoms:**
- Workflow should run daily at 06:00 UTC but doesn't

**Solutions:**

1. **Check if Actions are enabled:**
   - Go to **Actions** tab
   - Look for any message saying Actions are disabled
   - Enable if needed

2. **GitHub Actions schedule limitations:**
   - Scheduled workflows can be delayed during high load
   - Can be delayed up to 15+ minutes
   - May be disabled if repo is inactive for 60 days

3. **Trigger manually to test:**
   - Go to **Actions** tab
   - Select "Daily RFP Scraper"
   - Click **Run workflow**

## Reading the Logs

### Good Run Example:
```
============================================================
Starting RFP Scraper for Sword Health
Timestamp: 2025-01-17T06:00:00
============================================================
Loaded 142 previously seen RFP IDs
Scraping SAM.gov...
Found 5 relevant RFPs from SAM.gov
Scraping UNDP Procurement...
Found 2 relevant RFPs from UNDP Procurement
...
Total RFPs found across all sources: 7
Filtered 7 RFPs down to 2 new ones
============================================================
Processing 2 new RFPs (Total scraped: 7)
============================================================
Found 2 new RFPs - sending to Slack
Attempting to send Slack notification (RFP count: 2)
Detected Slack Workflow webhook
Slack API response status: 200
✓ Successfully sent notification with 2 RFPs to Slack

Attempting to update Google Sheets (RFP count: 2)
Google Sheets API response status: 200
✓ Successfully appended 2 RFPs to Google Sheets via webhook

============================================================
SCRAPER RUN SUMMARY
============================================================
Total RFPs scraped: 7
New RFPs found: 2
Slack notification: ✓ SENT
Google Sheets update: ✓ SENT
============================================================
```

### Failed Run Example (Missing Secrets):
```
============================================================
Starting RFP Scraper for Sword Health
============================================================
...
Processing 0 new RFPs (Total scraped: 0)
============================================================
No new RFPs found - sending empty notification to Slack
SLACK_WEBHOOK_URL not set, skipping Slack notification
Set SLACK_WEBHOOK_URL environment variable to enable Slack notifications

GOOGLE_SHEETS_WEBHOOK_URL not set, skipping Sheets update
Set GOOGLE_SHEETS_WEBHOOK_URL environment variable to enable Google Sheets tracking

============================================================
SCRAPER RUN SUMMARY
============================================================
Total RFPs scraped: 0
New RFPs found: 0
Slack notification: ✗ FAILED (check logs above)
Google Sheets update: ✗ FAILED (check logs above)
============================================================
```

## Still Having Issues?

1. **Run the debug script** (see above) to get detailed diagnostics
2. **Check the full workflow logs** for specific error messages
3. **Test webhooks manually** using curl commands
4. **Verify all secrets are set** in GitHub repository settings
5. **Open a GitHub issue** with:
   - Full error logs from Actions
   - Output from `debug_scraper.py`
   - Steps you've already tried
