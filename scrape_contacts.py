#!/usr/bin/env python3
"""
Company Contact Scraper
Scrapes email addresses and phone numbers from company websites.
"""

import csv
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraping_errors.log'),
        logging.StreamHandler()
    ]
)

class ContactScraper:
    def __init__(self, input_url, output_file, delay=1.5):
        """
        Initialize the contact scraper.

        Args:
            input_url: URL or path to input CSV
            output_file: Path to output CSV file
            delay: Delay between requests in seconds
        """
        self.input_url = input_url
        self.output_file = output_file
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        # Regex patterns
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        # Singapore phone patterns: +65 xxxx xxxx, 6xxx xxxx, 8xxx xxxx, 9xxx xxxx
        self.phone_pattern = re.compile(r'(?:\+65[\s-]?)?[6|8|9]\d{3}[\s-]?\d{4}')

    def convert_google_sheets_url(self, url):
        """Convert Google Sheets edit URL to CSV export URL."""
        if 'docs.google.com/spreadsheets' in url:
            # Extract spreadsheet ID and gid
            match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
            if match:
                spreadsheet_id = match.group(1)
                gid_match = re.search(r'gid=(\d+)', url)
                gid = gid_match.group(1) if gid_match else '0'
                return f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}'
        return url

    def read_input_csv(self):
        """Read the input CSV file and return list of companies."""
        input_url = self.convert_google_sheets_url(self.input_url)
        logging.info(f"Reading input from: {input_url}")

        try:
            response = self.session.get(input_url, timeout=30)
            response.raise_for_status()

            # Parse CSV from response content
            lines = response.text.splitlines()
            reader = csv.DictReader(lines)
            companies = list(reader)
            logging.info(f"Successfully loaded {len(companies)} companies")
            return companies
        except Exception as e:
            logging.error(f"Failed to read input CSV: {e}")
            raise

    def extract_emails(self, soup, url):
        """Extract email addresses from the page."""
        emails = set()

        # Look for mailto: links
        for link in soup.find_all('a', href=True):
            if link['href'].startswith('mailto:'):
                email = link['href'].replace('mailto:', '').split('?')[0]
                emails.add(email.lower().strip())

        # Search for email patterns in text
        text = soup.get_text()
        found_emails = self.email_pattern.findall(text)
        for email in found_emails:
            email = email.lower().strip()
            # Filter out common false positives
            if not any(ext in email for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg']):
                emails.add(email)

        return list(emails)

    def extract_phones(self, soup):
        """Extract Singapore phone numbers from the page."""
        phones = set()

        # Search in text content
        text = soup.get_text()
        found_phones = self.phone_pattern.findall(text)

        for phone in found_phones:
            # Normalize format
            phone = re.sub(r'[\s-]', '', phone)
            if not phone.startswith('+65'):
                phone = '+65' + phone
            phones.add(phone)

        # Also check href attributes for tel: links
        for link in soup.find_all('a', href=True):
            if link['href'].startswith('tel:'):
                phone = link['href'].replace('tel:', '').strip()
                phone = re.sub(r'[\s-()]', '', phone)
                if re.match(r'^\+?65[689]\d{7}$', phone):
                    if not phone.startswith('+'):
                        phone = '+65' + phone
                    phones.add(phone)

        return list(phones)

    def scrape_website(self, url):
        """
        Scrape a website for contact information.

        Returns:
            tuple: (email, phone) - first valid email and phone found, or None
        """
        try:
            # Ensure URL has scheme
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            logging.debug(f"Scraping: {url}")

            response = self.session.get(url, timeout=15, allow_redirects=True)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract emails and phones
            emails = self.extract_emails(soup, url)
            phones = self.extract_phones(soup)

            # Return first valid email and phone
            email = emails[0] if emails else ''
            phone = phones[0] if phones else ''

            return email, phone

        except requests.exceptions.Timeout:
            logging.warning(f"Timeout scraping {url}")
            return '', ''
        except requests.exceptions.ConnectionError:
            logging.warning(f"Connection error for {url}")
            return '', ''
        except requests.exceptions.HTTPError as e:
            logging.warning(f"HTTP error for {url}: {e}")
            return '', ''
        except Exception as e:
            logging.warning(f"Error scraping {url}: {e}")
            return '', ''

    def scrape_all(self):
        """Main method to scrape all companies and save results."""
        # Read input
        companies = self.read_input_csv()
        total = len(companies)

        # Prepare output
        results = []

        logging.info(f"Starting to scrape {total} companies...")

        for idx, company in enumerate(companies, 1):
            company_name = company.get('company_name', '').strip()
            website = company.get('website', '').strip()

            if not website:
                logging.info(f"Processing {idx}/{total} - {company_name}: No website provided")
                results.append({
                    'business_name': company_name,
                    'email': '',
                    'phone_number': ''
                })
                continue

            logging.info(f"Processing {idx}/{total} - {company_name} ({website})")

            # Scrape the website
            email, phone = self.scrape_website(website)

            results.append({
                'business_name': company_name,
                'email': email,
                'phone_number': phone
            })

            # Progress update
            if idx % 10 == 0:
                found_emails = sum(1 for r in results if r['email'])
                found_phones = sum(1 for r in results if r['phone_number'])
                logging.info(f"Progress: {idx}/{total} | Found {found_emails} emails, {found_phones} phones")

            # Delay between requests
            if idx < total:
                time.sleep(self.delay)

        # Write output
        self.write_output(results)

        # Final summary
        found_emails = sum(1 for r in results if r['email'])
        found_phones = sum(1 for r in results if r['phone_number'])
        logging.info(f"\nCompleted! Processed {total} companies")
        logging.info(f"Found {found_emails} emails ({found_emails/total*100:.1f}%)")
        logging.info(f"Found {found_phones} phone numbers ({found_phones/total*100:.1f}%)")
        logging.info(f"Results saved to: {self.output_file}")

    def write_output(self, results):
        """Write results to output CSV."""
        with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['business_name', 'email', 'phone_number'])
            writer.writeheader()
            writer.writerows(results)
        logging.info(f"Saved results to {self.output_file}")


def main():
    """Main entry point."""
    INPUT_URL = 'https://docs.google.com/spreadsheets/d/1x4wP4iatiDPeRSFjdq8dIby-PMLzfvl7d8QpI59P7fc/edit?gid=1826015035#gid=1826015035'
    OUTPUT_FILE = 'scraped_contacts.csv'
    DELAY = 1.5  # seconds between requests

    scraper = ContactScraper(INPUT_URL, OUTPUT_FILE, delay=DELAY)
    scraper.scrape_all()


if __name__ == '__main__':
    main()
