# CSV Company Data Email Scraper

Python script that reads company data from a Google Sheets CSV and scrapes email addresses from their websites with intelligent prioritization.

## Features

- **Smart Email Prioritization:**
  - Priority 1: `sales@`, `business@`, `enquiry@`, `inquiry@`, `contact@`
  - Priority 2: Any other company domain emails
  - Excludes: `info@`, `admin@`, `noreply@`, `support@`, `help@`, `no-reply@`

- **Robust Error Handling:**
  - Continues processing if a website fails to load
  - Leaves email field blank when no email is found
  - Handles timeouts and network errors gracefully

- **Rate Limiting:**
  - 1.5 second delay between requests to avoid being blocked
  - Respectful scraping practices

- **Progress Tracking:**
  - Real-time progress display: "Processing 150/5900..."
  - Shows found emails as they are discovered

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the script:
```bash
python csv_email_scraper.py
```

The script will:
1. Download the CSV from Google Sheets
2. Process each company's website
3. Scrape and prioritize emails
4. Save results to `contacts_with_emails.csv`

## Input CSV Columns

- Name (A)
- Address (B)
- Rating (C)
- Reviews (D)
- Phone (E)
- Website (F)
- Service Category (G)
- Remarks (H)

## Output CSV Columns

- Name
- Address
- Phone
- Email (newly scraped)
- Website
- Service Category
- Remarks

## Configuration

Edit these variables in `csv_email_scraper.py` if needed:

```python
INPUT_CSV_URL = "your_google_sheets_url"
OUTPUT_CSV_FILE = "contacts_with_emails.csv"
REQUEST_DELAY = 1.5  # seconds between requests
REQUEST_TIMEOUT = 10  # seconds
```

## Example Output

```
============================================================
CSV Company Data Email Scraper
============================================================

📥 Downloading CSV from Google Sheets...
✅ Loaded 5900 companies

🔍 Starting email scraping...
------------------------------------------------------------
Processing 1/5900: Cool Earth Aircon Servicing Singapore... ✅ Found: sales@coolearth.com.sg
Processing 2/5900: Twin City Air-Conditioning Engineering... ✅ Found: contact@twincity.com.sg
Processing 3/5900: Caredy Air-conditioning & Electrical... ⚫ No email
...
------------------------------------------------------------

💾 Writing results to contacts_with_emails.csv...
✅ Success! Output saved to: contacts_with_emails.csv

============================================================
📊 Summary
============================================================
Total companies processed: 5900
Emails found: 3245
Success rate: 55.0%
Output file: contacts_with_emails.csv
```

## Notes

- The script respects website rate limits with built-in delays
- Email extraction uses regex patterns and mailto links
- Only emails from the company's domain are included
- Generic emails (info@, support@) are automatically excluded
