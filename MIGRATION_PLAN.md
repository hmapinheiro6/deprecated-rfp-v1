# Migration Plan: Modular Architecture Refactor

## 📊 Current State Analysis

### Existing Files
```
rfp/
├── .github/workflows/scrape.yml     ✅ Working - GitHub Actions
├── scraper.py                       ⚠️  Old web scraper (not working - JS issue)
├── scraper_api.py                   ✅ Working - API-based scraper
├── config.py                        ✅ Working - Keywords & sources config
├── utils.py                         ✅ Working - Helper functions
├── google-apps-script-webhook.js    ✅ Working - Sheets integration
├── debug_scraper.py                 ✅ Working - Debugging tool
├── test_api_scraper.py             ✅ Working - API testing tool
├── test_sources.py                 ⚠️  Web scraping test (not needed for APIs)
├── requirements.txt                ✅ Working - Dependencies
├── data/seen_rfps.json             ✅ Working - Deduplication database
├── README.md                       ✅ Working - Main documentation
├── API_SETUP.md                    ✅ Working - API setup guide
└── TROUBLESHOOTING.md              ✅ Working - Troubleshooting guide
```

### What's Currently Working ✅
1. **SAM.gov API scraping** - Fully functional via `scraper_api.py`
2. **Slack webhooks** - Both Workflow and traditional formats
3. **Google Sheets webhooks** - Activity Log + RFPs tracking
4. **Deduplication system** - JSON-based seen RFPs tracking
5. **GitHub Actions** - Daily automated runs
6. **Notification systems** - Always-on notifications (even with 0 RFPs)

### What's Not Working ❌
1. **Web-based scrapers** - BeautifulSoup can't handle JavaScript sites
2. **UNDP/UNGM APIs** - Experimental, may not have public APIs
3. **Sourcewell** - Not implemented
4. **Gavi** - Not implemented

### Current Architecture Issues
- **Monolithic files**: All scrapers in one file (`scraper_api.py`)
- **No modularity**: Can't easily enable/disable individual scrapers
- **Mixed concerns**: Orchestration + scraping + notifications in same file
- **Hard to test**: Can't test individual scrapers independently
- **Hard to extend**: Adding new sources requires editing main file

---

## 🎯 Target Architecture

### New File Structure
```
rfp/
├── .github/
│   └── workflows/
│       └── scrape.yml               # UPDATE - Add Selenium setup
├── scrapers/
│   ├── __init__.py                  # NEW - Package initialization
│   ├── base.py                      # NEW - Base scraper class
│   ├── sam_gov.py                   # NEW - Extract from scraper_api.py
│   ├── undp.py                      # NEW - Extract from scraper_api.py
│   ├── ungm.py                      # NEW - Extract from scraper_api.py
│   ├── sourcewell.py                # NEW - Implement Selenium scraper
│   └── gavi.py                      # NEW - Implement Selenium scraper
├── main.py                          # NEW - Orchestrator
├── config.py                        # UPDATE - Add scraper enable/disable
├── utils.py                         # KEEP - Already good
├── notifications/
│   ├── __init__.py                  # NEW
│   ├── slack.py                     # NEW - Extract from scraper_api.py
│   └── google_sheets.py             # NEW - Extract from scraper_api.py
├── requirements.txt                 # UPDATE - Add Selenium
├── .env.example                     # NEW - Environment template
├── google-apps-script-webhook.js    # KEEP - Already working
├── debug_scraper.py                 # KEEP - Useful for debugging
├── test_api_scraper.py             # UPDATE - Work with new structure
├── data/
│   └── seen_rfps.json              # KEEP - Deduplication database
├── README.md                        # UPDATE - New setup instructions
├── API_SETUP.md                     # UPDATE - Reference new structure
└── TROUBLESHOOTING.md               # UPDATE - New architecture tips
```

### Key Benefits
✅ **Modular**: Each scraper is independent
✅ **Testable**: Can test scrapers individually
✅ **Configurable**: Easy enable/disable per source
✅ **Extensible**: Add new scrapers without touching existing code
✅ **Maintainable**: Clear separation of concerns
✅ **Type-safe**: Type hints throughout

---

## 📋 Migration Steps

### Phase 1: Create New Structure (No Breaking Changes)
**Goal**: Add new modular files alongside existing code

1. ✅ Create `scrapers/` directory structure
2. ✅ Create `notifications/` directory structure
3. ✅ Extract SAM.gov scraper to `scrapers/sam_gov.py`
4. ✅ Extract UNDP scraper to `scrapers/undp.py`
5. ✅ Extract UNGM scraper to `scrapers/ungm.py`
6. ✅ Create base scraper class in `scrapers/base.py`
7. ✅ Extract notification functions to `notifications/`
8. ✅ Create new `main.py` orchestrator
9. ✅ Update `config.py` with enable/disable flags

**Status**: OLD code still works, NEW code ready to test

### Phase 2: Implement Missing Scrapers
**Goal**: Add Sourcewell and Gavi with Selenium

1. ✅ Add Selenium dependencies to `requirements.txt`
2. ✅ Create `scrapers/sourcewell.py` with Selenium
3. ✅ Create `scrapers/gavi.py` with Selenium
4. ✅ Update GitHub Actions to install Chrome
5. ✅ Test locally with `python main.py --test`

**Status**: NEW scrapers added, OLD code still works

### Phase 3: Switch Over
**Goal**: Update GitHub Actions to use new architecture

1. ✅ Update `.github/workflows/scrape.yml` to call `main.py`
2. ✅ Test manual workflow run
3. ✅ Verify notifications work
4. ✅ Verify deduplication works

**Status**: NEW code in production, OLD code deprecated

### Phase 4: Cleanup (Optional)
**Goal**: Remove deprecated files

1. ✅ Move `scraper.py` to `deprecated/scraper_old.py`
2. ✅ Move `scraper_api.py` to `deprecated/scraper_api_old.py`
3. ✅ Update documentation to remove old references
4. ✅ Add deprecation notices to old files

**Status**: Clean, modular codebase

---

## 🔄 Code Preservation Strategy

### Files to KEEP Unchanged ✅
- `utils.py` - Helper functions are already well-designed
- `google-apps-script-webhook.js` - Sheets webhook works perfectly
- `data/seen_rfps.json` - Deduplication database
- `debug_scraper.py` - Still useful for debugging
- Core documentation files (README, etc.) - Will be updated, not replaced

### Files to EXTRACT (not replace)
- `scraper_api.py` → Split into `scrapers/*.py` + `main.py` + `notifications/*.py`
- Keep original file until migration is complete

### Files to UPDATE
- `config.py` - Add scraper enable/disable config
- `requirements.txt` - Add Selenium dependencies
- `.github/workflows/scrape.yml` - Update to call `main.py`
- `README.md` - Update setup instructions

### Files to CREATE (New)
- `scrapers/` directory - All new scraper modules
- `notifications/` directory - Extracted notification logic
- `main.py` - New orchestrator
- `.env.example` - Environment variable template

---

## 🧪 Testing Strategy

### Phase 1 Testing: Verify New Structure Works
```bash
# Test individual scrapers
python -c "from scrapers.sam_gov import SamGovScraper; print(SamGovScraper().scrape())"

# Test with orchestrator (skip notifications)
python main.py --test

# Test with notifications (use test webhooks)
export SLACK_WEBHOOK_URL="test-webhook"
python main.py
```

### Phase 2 Testing: Compare Old vs New
```bash
# Run old scraper
python scraper_api.py > old_results.txt

# Run new scraper
python main.py > new_results.txt

# Compare results
diff old_results.txt new_results.txt
```

### Phase 3 Testing: Production Validation
```bash
# Manual GitHub Actions trigger
# Check logs for errors
# Verify Slack notification received
# Verify Google Sheets updated
# Verify deduplication working
```

---

## ⚠️ Risk Assessment

### Low Risk ✅
- Creating new files alongside old ones
- Adding new dependencies
- Extracting working code to modules

### Medium Risk ⚠️
- Adding Selenium (needs Chrome in GitHub Actions)
- Changing workflow to call `main.py` instead of `scraper_api.py`
- New scrapers (Sourcewell, Gavi) might not work perfectly at first

### Mitigation Strategies
1. **Keep old code working** until new code is proven
2. **Test locally** before deploying to GitHub Actions
3. **Use `--test` flag** to test without sending notifications
4. **Manual trigger** workflows before relying on cron schedule
5. **Monitor Activity Log** in Google Sheets to track runs

---

## 📦 New Dependencies

### Current (requirements.txt)
```
requests==2.31.0
beautifulsoup4==4.12.3
lxml==5.1.0
google-api-python-client==2.116.0
google-auth==2.27.0
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
```

### To Add
```
selenium==4.16.0
webdriver-manager==4.0.1
python-dotenv==1.0.0
```

### Why?
- **selenium**: For Sourcewell and Gavi (JavaScript-heavy sites)
- **webdriver-manager**: Auto-install ChromeDriver
- **python-dotenv**: Load `.env` file for local testing

---

## 🎯 Success Criteria

### Must Have ✅
- [ ] All existing functionality preserved
- [ ] SAM.gov API scraper works identically
- [ ] Slack notifications work identically
- [ ] Google Sheets updates work identically
- [ ] Deduplication works identically
- [ ] GitHub Actions runs successfully
- [ ] Can enable/disable scrapers via config
- [ ] Can test individual scrapers
- [ ] Can run locally with `python main.py`

### Nice to Have 🎁
- [ ] Sourcewell scraper working
- [ ] Gavi scraper working
- [ ] Better error messages
- [ ] Individual scraper retry logic
- [ ] Scraper-specific configurations
- [ ] Performance metrics per scraper

---

## 🚀 Timeline Estimate

- **Phase 1**: Create new structure - 2 hours
- **Phase 2**: Implement Selenium scrapers - 3 hours
- **Phase 3**: Switch over & test - 1 hour
- **Phase 4**: Cleanup (optional) - 30 minutes

**Total**: ~6-7 hours of development time

---

## 📝 Migration Checklist

### Pre-Migration
- [ ] Create backup branch: `git checkout -b backup-before-refactor`
- [ ] Document current state (this file)
- [ ] Test current setup works

### Phase 1: New Structure
- [ ] Create `scrapers/` directory
- [ ] Create `scrapers/__init__.py`
- [ ] Create `scrapers/base.py`
- [ ] Extract SAM.gov to `scrapers/sam_gov.py`
- [ ] Extract UNDP to `scrapers/undp.py`
- [ ] Extract UNGM to `scrapers/ungm.py`
- [ ] Create `notifications/` directory
- [ ] Extract Slack to `notifications/slack.py`
- [ ] Extract Sheets to `notifications/google_sheets.py`
- [ ] Create `main.py` orchestrator
- [ ] Update `config.py`
- [ ] Create `.env.example`
- [ ] Test with `python main.py --test`

### Phase 2: New Scrapers
- [ ] Update `requirements.txt`
- [ ] Create `scrapers/sourcewell.py`
- [ ] Create `scrapers/gavi.py`
- [ ] Test Selenium locally
- [ ] Update GitHub Actions workflow
- [ ] Test manual workflow trigger

### Phase 3: Production
- [ ] Verify manual run works
- [ ] Wait for scheduled run
- [ ] Check notifications sent
- [ ] Check Activity Log updated
- [ ] Monitor for 3 days

### Phase 4: Cleanup
- [ ] Move old files to `deprecated/`
- [ ] Update all documentation
- [ ] Remove old references
- [ ] Delete backup branch if successful

---

## 🆘 Rollback Plan

If something breaks:

### Immediate Rollback (< 5 minutes)
```bash
# In .github/workflows/scrape.yml, change:
python main.py
# Back to:
python scraper_api.py

# Commit and push
git add .github/workflows/scrape.yml
git commit -m "Rollback to old scraper"
git push
```

### Full Rollback (< 15 minutes)
```bash
# Restore backup branch
git checkout backup-before-refactor
git checkout -b main-restored
git push -f origin main-restored:main
```

---

## 📞 Support & Questions

Before starting migration:
1. ✅ Review this plan
2. ✅ Ask questions about any unclear steps
3. ✅ Confirm Phase 1 approach looks good
4. ✅ Decide if you want Phase 4 (cleanup)

During migration:
- Test each phase before moving to next
- Keep old code until Phase 3 is proven
- Document any issues encountered

---

**Ready to proceed?** Let me know and I'll start with Phase 1!
