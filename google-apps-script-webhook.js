/**
 * Google Apps Script Webhook for RFP Scraper
 *
 * SETUP INSTRUCTIONS:
 * 1. Open your Google Sheet
 * 2. Go to Extensions → Apps Script
 * 3. Copy this entire file into the editor
 * 4. Save the project
 * 5. Click Deploy → New deployment
 * 6. Select type: Web app
 * 7. Execute as: Me
 * 8. Who has access: Anyone
 * 9. Click Deploy
 * 10. Copy the Web app URL and add it to GitHub Secrets as GOOGLE_SHEETS_WEBHOOK_URL
 *
 * SHEET FORMAT:
 * "RFPs" sheet:
 *   Column A: Timestamp (when added to sheet)
 *   Column B: Title
 *   Column C: URL
 *   Column D: Source
 *   Column E: Publish Date
 *   Column F: Deadline
 *   Column G: Snippet/Description
 *
 * "Activity Log" sheet:
 *   Column A: Run Timestamp
 *   Column B: New RFPs Found
 *   Column C: Status
 *   Column D: Notes
 */

function doPost(e) {
  try {
    // Parse incoming JSON payload
    const data = JSON.parse(e.postData.contents);
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();

    // Get or create RFPs sheet
    let rfpSheet = spreadsheet.getSheetByName('RFPs');
    if (!rfpSheet) {
      rfpSheet = spreadsheet.insertSheet('RFPs');
      // Add headers
      rfpSheet.appendRow([
        'Timestamp',
        'Title',
        'URL',
        'Source',
        'Published',
        'Deadline',
        'Description'
      ]);
      // Format header
      const headerRange = rfpSheet.getRange(1, 1, 1, 7);
      headerRange.setFontWeight('bold');
      headerRange.setBackground('#4285f4');
      headerRange.setFontColor('#ffffff');
      rfpSheet.setFrozenRows(1);
    }

    // Get or create Activity Log sheet
    let activitySheet = spreadsheet.getSheetByName('Activity Log');
    if (!activitySheet) {
      activitySheet = spreadsheet.insertSheet('Activity Log');
      // Add headers
      activitySheet.appendRow([
        'Run Timestamp',
        'New RFPs Found',
        'Status',
        'Notes'
      ]);
      // Format header
      const headerRange = activitySheet.getRange(1, 1, 1, 4);
      headerRange.setFontWeight('bold');
      headerRange.setBackground('#34a853');
      headerRange.setFontColor('#ffffff');
      activitySheet.setFrozenRows(1);
    }

    const runTimestamp = new Date();
    const rfpCount = data.rfps ? data.rfps.length : 0;
    let rowsAdded = 0;

    // Append each RFP to RFPs sheet
    if (data.rfps && data.rfps.length > 0) {
      data.rfps.forEach(rfp => {
        rfpSheet.appendRow([
          runTimestamp,                  // Timestamp
          rfp.title || '',               // Title
          rfp.url || '',                 // URL
          rfp.source || '',              // Source
          rfp.publish_date || 'N/A',     // Published date
          rfp.deadline || 'N/A',         // Deadline
          rfp.snippet || ''              // Description/snippet
        ]);
        rowsAdded++;
      });

      // Auto-resize columns for better readability
      rfpSheet.autoResizeColumns(1, 7);
    }

    // Log this run to Activity Log sheet
    const status = rfpCount > 0 ? 'Success' : 'No new RFPs';
    const notes = rfpCount > 0
      ? `Added ${rfpCount} new RFP(s)`
      : 'Scraper ran successfully but found no new relevant RFPs';

    activitySheet.appendRow([
      runTimestamp,
      rfpCount,
      status,
      notes
    ]);

    // Auto-resize Activity Log columns
    activitySheet.autoResizeColumns(1, 4);

    // Return success response
    return ContentService.createTextOutput(JSON.stringify({
      'status': 'success',
      'rows_added': rowsAdded,
      'rfps_processed': rfpCount,
      'timestamp': runTimestamp.toISOString()
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    // Log error to Activity Log if possible
    try {
      const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
      let activitySheet = spreadsheet.getSheetByName('Activity Log');
      if (activitySheet) {
        activitySheet.appendRow([
          new Date(),
          0,
          'Error',
          error.toString()
        ]);
      }
    } catch (logError) {
      // Ignore logging errors
    }

    // Return error response
    return ContentService.createTextOutput(JSON.stringify({
      'status': 'error',
      'message': error.toString(),
      'timestamp': new Date().toISOString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Optional: doGet function for testing the endpoint
 * Visit your web app URL in a browser to test
 */
function doGet(e) {
  return ContentService.createTextOutput(
    'RFP Scraper Google Sheets Webhook is active! Use POST requests to add data.'
  );
}

/**
 * Optional: Function to manually test the webhook with RFPs
 * Run this from the Apps Script editor to test appending data
 */
function testWebhookWithRFPs() {
  const testData = {
    postData: {
      contents: JSON.stringify({
        rfps: [
          {
            title: 'Test RFP - Digital Health Platform',
            url: 'https://example.com/rfp/123',
            source: 'Test Source',
            publish_date: '2025-01-15',
            deadline: '2025-02-28',
            snippet: 'This is a test RFP for digital health services'
          },
          {
            title: 'Test RFP - Telehealth Services',
            url: 'https://example.com/rfp/456',
            source: 'Another Test Source',
            publish_date: '2025-01-16',
            deadline: '2025-03-01',
            snippet: 'This is another test RFP for telehealth'
          }
        ]
      })
    }
  };

  const result = doPost(testData);
  Logger.log(result.getContent());
}

/**
 * Optional: Function to test webhook with NO RFPs (Activity Log only)
 * Run this to test the Activity Log when scraper finds nothing
 */
function testWebhookNoRFPs() {
  const testData = {
    postData: {
      contents: JSON.stringify({
        rfps: []  // Empty array - no RFPs found
      })
    }
  };

  const result = doPost(testData);
  Logger.log(result.getContent());
}
