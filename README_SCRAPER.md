# Google Places API Singapore Scraper (Grid Search)

This Python script scrapes addresses of industrial and commercial facilities across Singapore using the Google Places API (New) with a grid-based search approach.

## Features

- Uses Google Places API (New) Text Search endpoint
- Grid-based search: Divides Singapore into 0.05° grid cells
- Searches each cell with multiple text queries for different facility types
- 9 different search queries per grid cell
- Collects unique addresses with automatic deduplication
- Respects API rate limits and request quotas (max 9,000 requests)
- Real-time progress logging showing grid cells completed and addresses collected
- Exports results to CSV format

## Search Approach

The script divides Singapore into a grid and searches each cell systematically:

- **Grid size**: 0.05 degree cells
- **Geographic bounds**:
  - Latitude: 1.15°N to 1.47°N
  - Longitude: 103.6°E to 104.0°E
- **Total grid cells**: 56 cells (7 × 8 grid)
- **Queries per grid cell**: 9 text queries
- **Total API requests**: 56 cells × 9 queries = 504 requests

## Search Queries

The script uses the following text queries per grid cell:
1. "manufacturing companies"
2. "manufacturing facilities"
3. "logistics companies"
4. "warehousing companies"
5. "distribution centers"
6. "food processing companies"
7. "electronics manufacturing"
8. "chemical companies"
9. "petrochemical companies"

These text queries are more effective than place types, as they search for actual business names and descriptions rather than relying on Google's limited place type taxonomy.

## Requirements

- Python 3.6+
- `requests` library

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python scrape_singapore_places.py
```

The script will:
1. Generate a 7×8 grid covering all of Singapore
2. For each grid cell, run 9 different text search queries
3. Use locationRestriction to limit results to each grid cell
4. Collect unique addresses from all searches
5. Display progress every 5 cells
6. Save results to `singapore_addresses.csv`

## Output

The script generates a CSV file named `singapore_addresses.csv` with a single column:
- `address`: The formatted address of each facility

## Configuration

You can modify the following parameters in the script:

- `MAX_REQUESTS`: Maximum number of API requests (default: 9,000)
- `SEARCH_QUERIES`: List of text queries to search for
- `LAT_MIN`, `LAT_MAX`, `LON_MIN`, `LON_MAX`: Geographic boundaries for Singapore
- `GRID_SIZE`: Grid cell size in degrees (default: 0.05°)
- `OUTPUT_FILE`: Output CSV filename

## API Information

- **Endpoint**: Google Places API (New) - Text Search
- **Field**: formattedAddress (Essentials tier)
- **Coverage**: All of Singapore via grid search
- **Grid cells**: 56 total (7 latitude × 8 longitude)
- **Queries per cell**: 9 text queries
- **Total requests**: 504 (56 cells × 9 queries)
- **Max results per request**: 20

## Progress Logging

The script provides real-time feedback:
- Per-cell results: Shows coordinates and total results from all queries in that cell
- Displays total places found and new unique addresses per cell
- Progress updates every 5 cells with percentage completion
- Running totals of unique addresses and API requests
- Final summary with total cells processed and addresses collected

## Sample Output

During execution, you'll see output like this:

```
Grid Search Configuration:
  Grid size: 0.05° cells
  Total grid cells: 56
  Search queries per cell: 9
  Total searches: 504
  Maximum requests: 9000

Cell 1/56: (1.175, 103.625)
  → Found 42 total places, 38 new addresses
Cell 2/56: (1.175, 103.675)
  → Found 25 total places, 18 new addresses
...
Cell 5/56: (1.225, 103.675)
  → Found 15 total places, 8 new addresses

📊 Progress: 5/56 cells completed (8.9%)
   Total addresses: 145 | API requests: 45/9000
```

## References

- [Google Places API (New) - Text Search Documentation](https://developers.google.com/maps/documentation/places/web-service/text-search)
- [Place Data Fields Documentation](https://developers.google.com/maps/documentation/places/web-service/data-fields)
- [Google Places API Overview](https://developers.google.com/maps/documentation/places/web-service/overview)
