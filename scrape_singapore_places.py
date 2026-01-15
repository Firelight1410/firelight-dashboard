#!/usr/bin/env python3
"""
Google Places API (New) - Singapore Address Scraper (Grid Search)

This script searches for industrial and commercial facilities across Singapore
using a grid-based approach with the Google Places API (New) Nearby Search endpoint.

The script divides Singapore into a grid of 0.05 degree cells and searches each
cell for specified facility types.

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
NEARBY_SEARCH_URL = "https://places.googleapis.com/v1/places:searchNearby"

# Place types to search for
# Note: These types may not all be valid in Google's Place Types taxonomy.
# The API will ignore invalid types and search for valid ones.
PLACE_TYPES = [
    "manufacturing",
    "logistics",
    "warehousing",
    "distribution",
    "food_processing",
    "electronics_manufacturing",
    "chemical",
    "petrochemical"
]

# Singapore geographic bounds
LAT_MIN = 1.15
LAT_MAX = 1.47
LON_MIN = 103.6
LON_MAX = 104.0

# Grid configuration
GRID_SIZE = 0.05  # degrees
SEARCH_RADIUS = 2000.0  # meters


class GridSearchScraper:
    """Grid-based scraper for Google Places API (New)"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.request_count = 0
        self.addresses: Set[str] = set()
        self.grid_cells = self._generate_grid()

    def _generate_grid(self) -> List[Tuple[float, float]]:
        """
        Generate grid cell center points across Singapore

        Returns:
            List of (latitude, longitude) tuples for grid cell centers
        """
        cells = []

        # Calculate grid points
        lat = LAT_MIN
        while lat <= LAT_MAX:
            lon = LON_MIN
            while lon <= LON_MAX:
                cells.append((lat, lon))
                lon += GRID_SIZE
            lat += GRID_SIZE

        return cells

    def nearby_search(self, lat: float, lon: float, included_types: List[str]) -> Dict[str, Any]:
        """
        Perform a nearby search using the Places API (New)

        Args:
            lat: Latitude of search center
            lon: Longitude of search center
            included_types: List of place types to search for

        Returns:
            API response as dictionary
        """
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.formattedAddress"
        }

        body = {
            "includedTypes": included_types,
            "maxResultCount": 20,  # Maximum results per request
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": lat,
                        "longitude": lon
                    },
                    "radius": SEARCH_RADIUS
                }
            }
        }

        try:
            response = requests.post(NEARBY_SEARCH_URL, headers=headers, json=body)
            self.request_count += 1

            if response.status_code == 200:
                return response.json()
            else:
                # Don't print errors for every failed request to reduce noise
                if response.status_code != 400:  # 400 often means no results
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

        print(f"Grid Search Configuration:")
        print(f"  Grid size: {GRID_SIZE}° cells")
        print(f"  Search radius: {SEARCH_RADIUS}m per cell")
        print(f"  Total grid cells: {total_cells}")
        print(f"  Place types: {len(PLACE_TYPES)}")
        print(f"  Maximum requests: {MAX_REQUESTS}")
        print()

        cells_completed = 0

        for i, (lat, lon) in enumerate(self.grid_cells, 1):
            if self.request_count >= MAX_REQUESTS:
                print(f"\n⚠️  Reached maximum request limit ({MAX_REQUESTS})")
                break

            # Search this grid cell
            addresses_before = len(self.addresses)
            self._search_cell(lat, lon, i, total_cells)
            addresses_found = len(self.addresses) - addresses_before

            cells_completed += 1

            # Progress update every 10 cells
            if i % 10 == 0 or i == total_cells:
                print(f"\n📊 Progress: {cells_completed}/{total_cells} cells completed "
                      f"({cells_completed/total_cells*100:.1f}%)")
                print(f"   Total addresses: {len(self.addresses)} | "
                      f"API requests: {self.request_count}/{MAX_REQUESTS}\n")

            # Small delay to be respectful to the API
            time.sleep(0.2)

        print(f"\n✓ Grid search complete!")
        print(f"  Cells processed: {cells_completed}/{total_cells}")
        print(f"  Total requests: {self.request_count}")
        print(f"  Unique addresses: {len(self.addresses)}")

        return sorted(list(self.addresses))

    def _search_cell(self, lat: float, lon: float, cell_num: int, total_cells: int) -> None:
        """
        Search a single grid cell for all place types

        Args:
            lat: Cell center latitude
            lon: Cell center longitude
            cell_num: Current cell number
            total_cells: Total number of cells
        """
        print(f"Cell {cell_num}/{total_cells}: ({lat:.3f}, {lon:.3f})", end=" ")

        if self.request_count >= MAX_REQUESTS:
            print("⚠️  Request limit reached")
            return

        # Make the API request for this cell with all place types
        result = self.nearby_search(lat, lon, PLACE_TYPES)

        # Extract addresses from results
        new_addresses = 0
        if "places" in result:
            for place in result["places"]:
                if "formattedAddress" in place:
                    address = place["formattedAddress"]
                    if address not in self.addresses:
                        self.addresses.add(address)
                        new_addresses += 1

        places_count = len(result.get("places", []))
        if places_count > 0:
            print(f"→ Found {places_count} places ({new_addresses} new addresses)")
        else:
            print(f"→ No results")

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
    print(f"Average addresses per request: {len(addresses)/scraper.request_count:.2f}")
    print("=" * 70)


if __name__ == "__main__":
    main()
