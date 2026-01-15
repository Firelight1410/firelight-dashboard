#!/usr/bin/env python3
"""
Google Places API (New) - Singapore Address Scraper

This script searches for industrial and commercial facilities across Singapore
using the Google Places API (New) Text Search endpoint.

Requirements:
- requests library: pip install requests
"""

import csv
import json
import time
import requests
from typing import List, Set, Dict, Any

# Configuration
API_KEY = "AIzaSyBxMYYMr9XTw4q78oPwEEynPJqY5yyugkc"
OUTPUT_FILE = "singapore_addresses.csv"
MAX_REQUESTS = 9000

# API endpoint
SEARCH_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"

# Search keywords for different facility types
SEARCH_TYPES = [
    "manufacturing",
    "logistics",
    "warehousing",
    "distribution",
    "food processing",
    "electronics manufacturing",
    "chemical",
    "petrochemical"
]

# Singapore bounding box (approximate)
# Southwest corner: 1.15°N, 103.6°E
# Northeast corner: 1.47°N, 104.05°E
SINGAPORE_BOUNDS = {
    "rectangle": {
        "low": {
            "latitude": 1.15,
            "longitude": 103.6
        },
        "high": {
            "latitude": 1.47,
            "longitude": 104.05
        }
    }
}


class PlacesScraper:
    """Scraper for Google Places API (New)"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.request_count = 0
        self.addresses: Set[str] = set()

    def search_text(self, query: str, page_token: str = None) -> Dict[str, Any]:
        """
        Perform a text search using the Places API (New)

        Args:
            query: Search query string
            page_token: Token for pagination (optional)

        Returns:
            API response as dictionary
        """
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.formattedAddress,nextPageToken"
        }

        body = {
            "textQuery": f"{query} in Singapore",
            "locationRestriction": SINGAPORE_BOUNDS,
            "pageSize": 20  # Maximum results per page
        }

        # Add page token if this is a pagination request
        if page_token:
            body["pageToken"] = page_token

        try:
            response = requests.post(SEARCH_TEXT_URL, headers=headers, json=body)
            self.request_count += 1

            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return {}

        except Exception as e:
            print(f"Request failed: {e}")
            return {}

    def scrape_all_types(self) -> List[str]:
        """
        Scrape all search types and collect unique addresses

        Returns:
            List of unique addresses
        """
        print(f"Starting scrape of {len(SEARCH_TYPES)} search types...")
        print(f"Maximum requests allowed: {MAX_REQUESTS}\n")

        for search_type in SEARCH_TYPES:
            if self.request_count >= MAX_REQUESTS:
                print(f"\n⚠️  Reached maximum request limit ({MAX_REQUESTS})")
                break

            print(f"Searching for: {search_type}")
            self._scrape_type(search_type)

            # Add a small delay between different search types to be respectful
            time.sleep(0.5)

        print(f"\n✓ Scraping complete!")
        print(f"Total requests made: {self.request_count}")
        print(f"Unique addresses found: {len(self.addresses)}")

        return sorted(list(self.addresses))

    def _scrape_type(self, search_type: str) -> None:
        """
        Scrape all pages for a specific search type

        Args:
            search_type: The type/keyword to search for
        """
        page_num = 1
        next_page_token = None
        addresses_found = 0

        while True:
            if self.request_count >= MAX_REQUESTS:
                print(f"  ⚠️  Request limit reached")
                break

            # Make the API request
            result = self.search_text(search_type, next_page_token)

            # Extract addresses from results
            if "places" in result:
                for place in result["places"]:
                    if "formattedAddress" in place:
                        address = place["formattedAddress"]
                        if address not in self.addresses:
                            self.addresses.add(address)
                            addresses_found += 1

            print(f"  Page {page_num}: Found {len(result.get('places', []))} results "
                  f"({addresses_found} new addresses)")

            # Check if there are more pages
            next_page_token = result.get("nextPageToken")
            if not next_page_token:
                break

            page_num += 1
            time.sleep(0.3)  # Small delay between pagination requests

        print(f"  Total new addresses from '{search_type}': {addresses_found}\n")

    def save_to_csv(self, filename: str) -> None:
        """
        Save collected addresses to CSV file

        Args:
            filename: Output CSV filename
        """
        addresses_list = sorted(list(self.addresses))

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['address'])  # Header

            for address in addresses_list:
                writer.writerow([address])

        print(f"\n✓ Saved {len(addresses_list)} addresses to {filename}")


def main():
    """Main execution function"""
    print("=" * 70)
    print("Google Places API (New) - Singapore Address Scraper")
    print("=" * 70)
    print()

    # Initialize scraper
    scraper = PlacesScraper(API_KEY)

    # Scrape all search types
    addresses = scraper.scrape_all_types()

    # Save results to CSV
    scraper.save_to_csv(OUTPUT_FILE)

    print("\n" + "=" * 70)
    print("Scraping Summary")
    print("=" * 70)
    print(f"Total API requests: {scraper.request_count}/{MAX_REQUESTS}")
    print(f"Unique addresses collected: {len(addresses)}")
    print(f"Output file: {OUTPUT_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    main()
