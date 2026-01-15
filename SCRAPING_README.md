# Company Contact Scraper

Python script to scrape email addresses and phone numbers from company websites.

## Features

- Reads company names and websites from Google Sheets CSV
- Extracts email addresses (mailto: links and email patterns)
- Extracts Singapore phone numbers (+65, 6xxx, 8xxx, 9xxx formats)
- Handles errors gracefully (timeouts, connection issues)
- Shows progress updates every 10 companies
- Adds 1.5 second delay between requests to avoid being blocked
- Logs errors to `scraping_errors.log`
- Outputs results to CSV file

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the scraper:
```bash
python scrape_contacts.py
```

The script will:
1. Read from the Google Sheets URL (configured in the script)
2. Scrape each company website
3. Save results to `scraped_contacts.csv`
4. Log progress and errors

## Output Format

The output CSV contains three columns:
- `business_name`: Company name from input
- `email`: First email address found (or blank)
- `phone_number`: First Singapore phone number found (or blank)

## Configuration

Edit these variables in `scrape_contacts.py` to customize:
- `INPUT_URL`: Source Google Sheets URL
- `OUTPUT_FILE`: Output CSV filename (default: `scraped_contacts.csv`)
- `DELAY`: Seconds between requests (default: 1.5)

## Error Handling

- Connection timeouts: Logged and skipped, continues to next website
- HTTP errors: Logged and skipped
- Invalid URLs: Handled gracefully
- All errors logged to `scraping_errors.log`

## Performance

- Processing 5900 websites at 1.5s per site ≈ 2.5 hours
- Adjust `DELAY` parameter if needed (lower = faster but higher risk of blocking)
