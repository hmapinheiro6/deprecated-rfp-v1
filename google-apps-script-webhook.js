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
 * Column A: Timestamp (when added to sheet)
 * Column B: Title
 * Column C: URL
 * Column D: Source
 * Column E: Publish Date
 * Column F: Deadline
 * Column G: Snippet/Description
 */

function doPost(e) {
  try {
    // Parse incoming JSON payload
    const data = JSON.parse(e.postData.contents);

    // Get the active sheet (or specify sheet name)
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    // To use a specific sheet, uncomment and modify:
    // const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('RFPs');

    // Optional: Add headers if this is the first row
    if (sheet.getLastRow() === 0) {
      sheet.appendRow([
        'Timestamp',
        'Title',
        'URL',
        'Source',
        'Published',
        'Deadline',
        'Description'
      ]);

      // Make header bold
      const headerRange = sheet.getRange(1, 1, 1, 7);
      headerRange.setFontWeight('bold');
      headerRange.setBackground('#f3f3f3');
    }

    // Counter for rows added
    let rowsAdded = 0;

    // Append each RFP as a new row
    data.rfps.forEach(rfp => {
      sheet.appendRow([
        new Date(),                    // Timestamp
        rfp.title || '',               // Title
        rfp.url || '',                 // URL
        rfp.source || '',              // Source
        rfp.publish_date || 'N/A',     // Published date
        rfp.deadline || 'N/A',         // Deadline
        rfp.snippet || ''              // Description/snippet
      ]);
      rowsAdded++;
    });

    // Auto-resize columns for better readability (optional)
    sheet.autoResizeColumns(1, 7);

    // Return success response
    return ContentService.createTextOutput(JSON.stringify({
      'status': 'success',
      'rows_added': rowsAdded,
      'timestamp': new Date().toISOString()
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
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
 * Optional: Function to manually test the webhook
 * Run this from the Apps Script editor to test appending data
 */
function testWebhook() {
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
