#!/usr/bin/env python3
"""
Google Places API (New) - Singapore Address Scraper (Grid Search)

This script searches for industrial and commercial facilities across Singapore
using a grid-based approach with the Google Places API (New) Text Search endpoint.

The script divides Singapore into a grid of 0.05 degree cells and searches each
cell for specified facility types using text queries.

Requirements:
- requests library: pip install requests
"""

import csv
import json
import time
import requests
from typing import List, Set, Dict, Any, Tuple

# Configuration
API_KEY = "AIzaSyBxMYYMr9XTw4q78oPwEEynPJqY5yyugkc"
OUTPUT_FILE = "singapore_addresses.csv"
MAX_REQUESTS = 9000

# API endpoint
TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

# Search queries for different facility types
SEARCH_QUERIES = [
    "manufacturing companies",
    "manufacturing facilities",
    "logistics companies",
    "warehousing companies",
    "distribution centers",
    "food processing companies",
    "electronics manufacturing",
    "chemical companies",
    "petrochemical companies"
]

# Singapore geographic bounds
LAT_MIN = 1.15
LAT_MAX = 1.47
LON_MIN = 103.6
LON_MAX = 104.0

# Grid configuration
GRID_SIZE = 0.05  # degrees


class GridSearchScraper:
    """Grid-based scraper for Google Places API (New) using Text Search"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.request_count = 0
        self.addresses: Set[str] = set()
        self.grid_cells = self._generate_grid()

    def _generate_grid(self) -> List[Tuple[float, float, float, float]]:
        """
        Generate grid cell boundaries across Singapore

        Returns:
            List of (lat_min, lat_max, lon_min, lon_max) tuples for grid cells
        """
        cells = []

        # Calculate grid cells
        lat = LAT_MIN
        while lat < LAT_MAX:
            lon = LON_MIN
            while lon < LON_MAX:
                lat_max = min(lat + GRID_SIZE, LAT_MAX)
                lon_max = min(lon + GRID_SIZE, LON_MAX)
                cells.append((lat, lat_max, lon, lon_max))
                lon += GRID_SIZE
            lat += GRID_SIZE

        return cells

    def text_search(self, query: str, lat_min: float, lat_max: float,
                    lon_min: float, lon_max: float) -> Dict[str, Any]:
        """
        Perform a text search using the Places API (New) within a grid cell

        Args:
            query: Search query string
            lat_min: Minimum latitude of search area
            lat_max: Maximum latitude of search area
            lon_min: Minimum longitude of search area
            lon_max: Maximum longitude of search area

        Returns:
            API response as dictionary
        """
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.formattedAddress"
        }

        body = {
            "textQuery": query,
            "locationRestriction": {
                "rectangle": {
                    "low": {
                        "latitude": lat_min,
                        "longitude": lon_min
                    },
                    "high": {
                        "latitude": lat_max,
                        "longitude": lon_max
                    }
                }
            },
            "maxResultCount": 20  # Maximum results per request
        }

        try:
            response = requests.post(TEXT_SEARCH_URL, headers=headers, json=body)
            self.request_count += 1

            if response.status_code == 200:
                return response.json()
            else:
                # Only show non-404/400 errors to reduce noise
                if response.status_code not in [400, 404]:
                    print(f"    ⚠️  HTTP {response.status_code}: {response.text[:100]}")
                return {}

        except Exception as e:
            print(f"    ⚠️  Request failed: {e}")
            return {}

    def scrape_grid(self) -> List[str]:
        """
        Scrape all grid cells and collect unique addresses

        Returns:
            List of unique addresses
        """
        total_cells = len(self.grid_cells)
        total_searches = total_cells * len(SEARCH_QUERIES)

        print(f"Grid Search Configuration:")
        print(f"  Grid size: {GRID_SIZE}° cells")
        print(f"  Total grid cells: {total_cells}")
        print(f"  Search queries per cell: {len(SEARCH_QUERIES)}")
        print(f"  Total searches: {total_searches}")
        print(f"  Maximum requests: {MAX_REQUESTS}")
        print()

        cells_completed = 0

        for i, (lat_min, lat_max, lon_min, lon_max) in enumerate(self.grid_cells, 1):
            if self.request_count >= MAX_REQUESTS:
                print(f"\n⚠️  Reached maximum request limit ({MAX_REQUESTS})")
                break

            # Search this grid cell
            addresses_before = len(self.addresses)
            self._search_cell(lat_min, lat_max, lon_min, lon_max, i, total_cells)
            addresses_found = len(self.addresses) - addresses_before

            cells_completed += 1

            # Progress update every 5 cells
            if i % 5 == 0 or i == total_cells:
                print(f"\n📊 Progress: {cells_completed}/{total_cells} cells completed "
                      f"({cells_completed/total_cells*100:.1f}%)")
                print(f"   Total addresses: {len(self.addresses)} | "
                      f"API requests: {self.request_count}/{MAX_REQUESTS}\n")

            # Small delay to be respectful to the API
            time.sleep(0.3)

        print(f"\n✓ Grid search complete!")
        print(f"  Cells processed: {cells_completed}/{total_cells}")
        print(f"  Total requests: {self.request_count}")
        print(f"  Unique addresses: {len(self.addresses)}")

        return sorted(list(self.addresses))

    def _search_cell(self, lat_min: float, lat_max: float, lon_min: float,
                     lon_max: float, cell_num: int, total_cells: int) -> None:
        """
        Search a single grid cell for all search queries

        Args:
            lat_min: Minimum latitude of cell
            lat_max: Maximum latitude of cell
            lon_min: Minimum longitude of cell
            lon_max: Maximum longitude of cell
            cell_num: Current cell number
            total_cells: Total number of cells
        """
        lat_center = (lat_min + lat_max) / 2
        lon_center = (lon_min + lon_max) / 2

        print(f"Cell {cell_num}/{total_cells}: ({lat_center:.3f}, {lon_center:.3f})")

        cell_addresses = 0
        cell_places = 0

        for query in SEARCH_QUERIES:
            if self.request_count >= MAX_REQUESTS:
                print(f"  ⚠️  Request limit reached")
                break

            # Make the API request for this query in this cell
            result = self.text_search(query, lat_min, lat_max, lon_min, lon_max)

            # Extract addresses from results
            if "places" in result:
                places_found = len(result["places"])
                cell_places += places_found

                for place in result["places"]:
                    if "formattedAddress" in place:
                        address = place["formattedAddress"]
                        if address not in self.addresses:
                            self.addresses.add(address)
                            cell_addresses += 1

            # Small delay between queries
            time.sleep(0.1)

        print(f"  → Found {cell_places} total places, {cell_addresses} new addresses")

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
    print("Google Places API (New) - Grid Search Scraper")
    print("=" * 70)
    print()

    # Initialize scraper
    scraper = GridSearchScraper(API_KEY)

    # Scrape all grid cells
    addresses = scraper.scrape_grid()

    # Save results to CSV
    scraper.save_to_csv(OUTPUT_FILE)

    print("\n" + "=" * 70)
    print("Scraping Summary")
    print("=" * 70)
    print(f"Total API requests: {scraper.request_count}/{MAX_REQUESTS}")
    print(f"Unique addresses collected: {len(addresses)}")
    print(f"Output file: {OUTPUT_FILE}")
    if scraper.request_count > 0:
        print(f"Average addresses per request: {len(addresses)/scraper.request_count:.2f}")
    print("=" * 70)


if __name__ == "__main__":
    main()
