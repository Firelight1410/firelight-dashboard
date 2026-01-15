#!/usr/bin/env python3
"""
CSV Company Data Email Scraper
Reads company data from Google Sheets CSV and scrapes emails from websites
"""

import csv
import re
import time
import sys
from typing import Optional, List
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Configuration
INPUT_CSV_URL = "https://docs.google.com/spreadsheets/d/1x4wP4iatiDPeRSFjdq8dIby-PMLzfvl7d8QpI59P7fc/export?format=csv&gid=1826015035"
OUTPUT_CSV_FILE = "contacts_with_emails.csv"
REQUEST_DELAY = 1.5  # seconds between requests
REQUEST_TIMEOUT = 10  # seconds

# Email prioritization
PRIORITY_1_PREFIXES = ['sales@', 'business@', 'enquiry@', 'inquiry@', 'contact@']
EXCLUDE_PREFIXES = ['info@', 'admin@', 'noreply@', 'no-reply@', 'support@', 'help@']

# Headers to mimic a real browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}


def extract_domain(url: str) -> Optional[str]:
    """Extract domain from URL"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return None


def is_valid_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def should_exclude_email(email: str) -> bool:
    """Check if email should be excluded based on prefixes"""
    email_lower = email.lower()
    for prefix in EXCLUDE_PREFIXES:
        if email_lower.startswith(prefix):
            return True
    return False


def prioritize_emails(emails: List[str], domain: str) -> Optional[str]:
    """
    Prioritize emails based on criteria:
    1. First priority: sales@, business@, enquiry@, inquiry@, contact@
    2. Second priority: Any other company domain emails
    3. Exclude: info@, admin@, noreply@, support@, help@, no-reply@
    """
    if not emails:
        return None

    # Filter out excluded emails and validate
    valid_emails = []
    for email in emails:
        email = email.lower().strip()
        if is_valid_email(email) and not should_exclude_email(email):
            # Only include emails from the same domain
            email_domain = email.split('@')[1] if '@' in email else ''
            if domain and email_domain in domain:
                valid_emails.append(email)

    if not valid_emails:
        return None

    # Priority 1: sales@, business@, etc.
    for email in valid_emails:
        for prefix in PRIORITY_1_PREFIXES:
            if email.startswith(prefix):
                return email

    # Priority 2: Return first company domain email
    return valid_emails[0]


def scrape_emails_from_website(url: str) -> Optional[str]:
    """
    Scrape emails from a website with smart prioritization
    Returns: Best email found or None
    """
    if not url or url == "(empty)" or not url.startswith('http'):
        return None

    try:
        # Make request
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract domain for filtering
        domain = extract_domain(url)

        # Find all emails using regex
        email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'

        # Search in text content
        text_content = soup.get_text()
        emails_in_text = re.findall(email_pattern, text_content)

        # Search in mailto links
        mailto_links = soup.find_all('a', href=re.compile(r'^mailto:', re.I))
        emails_in_mailto = [link['href'].replace('mailto:', '').split('?')[0] for link in mailto_links]

        # Combine all found emails
        all_emails = list(set(emails_in_text + emails_in_mailto))

        # Prioritize and return best email
        return prioritize_emails(all_emails, domain)

    except requests.exceptions.Timeout:
        print(f"  ⏱️  Timeout: {url}", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Error: {url} - {str(e)[:50]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  ⚠️  Parse error: {url} - {str(e)[:50]}", file=sys.stderr)
        return None


def download_csv(url: str) -> List[dict]:
    """Download CSV from Google Sheets"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Parse CSV
        content = response.content.decode('utf-8')
        csv_reader = csv.DictReader(content.splitlines())
        return list(csv_reader)
    except Exception as e:
        print(f"❌ Error downloading CSV: {e}")
        sys.exit(1)


def main():
    """Main execution function"""
    print("=" * 60)
    print("CSV Company Data Email Scraper")
    print("=" * 60)
    print()

    # Download input CSV
    print("📥 Downloading CSV from Google Sheets...")
    rows = download_csv(INPUT_CSV_URL)
    total_rows = len(rows)
    print(f"✅ Loaded {total_rows} companies")
    print()

    # Process each row
    output_rows = []
    emails_found = 0

    print("🔍 Starting email scraping...")
    print("-" * 60)

    for idx, row in enumerate(rows, 1):
        # Extract data
        name = row.get('Name', '').strip()
        address = row.get('Address', '').strip()
        phone = row.get('Phone', '').strip()
        website = row.get('Website', '').strip()
        service_category = row.get('Service Category', '').strip()
        remarks = row.get('Remarks', '').strip()

        # Progress indicator
        print(f"Processing {idx}/{total_rows}: {name[:40]}...", end=' ')
        sys.stdout.flush()

        # Scrape email
        email = scrape_emails_from_website(website)

        if email:
            print(f"✅ Found: {email}")
            emails_found += 1
        else:
            print("⚫ No email")
            email = ""

        # Build output row
        output_rows.append({
            'Name': name,
            'Address': address,
            'Phone': phone,
            'Email': email,
            'Website': website,
            'Service Category': service_category,
            'Remarks': remarks
        })

        # Rate limiting delay (except for last item)
        if idx < total_rows:
            time.sleep(REQUEST_DELAY)

    print("-" * 60)
    print()

    # Write output CSV
    print(f"💾 Writing results to {OUTPUT_CSV_FILE}...")
    try:
        with open(OUTPUT_CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['Name', 'Address', 'Phone', 'Email', 'Website', 'Service Category', 'Remarks']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_rows)
        print(f"✅ Success! Output saved to: {OUTPUT_CSV_FILE}")
    except Exception as e:
        print(f"❌ Error writing output file: {e}")
        sys.exit(1)

    # Summary
    print()
    print("=" * 60)
    print("📊 Summary")
    print("=" * 60)
    print(f"Total companies processed: {total_rows}")
    print(f"Emails found: {emails_found}")
    print(f"Success rate: {(emails_found/total_rows*100):.1f}%")
    print(f"Output file: {OUTPUT_CSV_FILE}")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Script interrupted by user")
        sys.exit(0)
