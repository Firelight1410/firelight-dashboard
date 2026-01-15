# Google Places API Singapore Scraper (Grid Search)

This Python script scrapes addresses of industrial and commercial facilities across Singapore using the Google Places API (New) with a grid-based search approach.

## Features

- Uses Google Places API (New) Nearby Search endpoint
- Grid-based search: Divides Singapore into 0.05° grid cells
- Searches each cell with 2000m radius
- Searches for 8 different facility types
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
- **Search radius**: 2000 meters per cell center
- **One API request per grid cell**

## Place Types Searched

The script searches for the following facility types:
- manufacturing
- logistics
- warehousing
- distribution
- food_processing
- electronics_manufacturing
- chemical
- petrochemical

**Note**: Not all of these types may be valid in Google's official Place Types taxonomy. The API will process valid types and ignore invalid ones.

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
2. Search each grid cell with a 2000m radius
3. Collect unique addresses from all grid cells
4. Display progress every 10 cells
5. Save results to `singapore_addresses.csv`

## Output

The script generates a CSV file named `singapore_addresses.csv` with a single column:
- `address`: The formatted address of each facility

## Configuration

You can modify the following parameters in the script:

- `MAX_REQUESTS`: Maximum number of API requests (default: 9,000)
- `PLACE_TYPES`: List of place types to search for
- `LAT_MIN`, `LAT_MAX`, `LON_MIN`, `LON_MAX`: Geographic boundaries for Singapore
- `GRID_SIZE`: Grid cell size in degrees (default: 0.05°)
- `SEARCH_RADIUS`: Search radius per grid cell in meters (default: 2000m)
- `OUTPUT_FILE`: Output CSV filename

## API Information

- **Endpoint**: Google Places API (New) - Nearby Search
- **Field**: formattedAddress (Essentials tier)
- **Coverage**: All of Singapore via grid search
- **Grid cells**: 56 total (7 latitude × 8 longitude)
- **Max results per request**: 20

## Progress Logging

The script provides real-time feedback:
- Per-cell results: Shows coordinates, places found, and new addresses
- Progress updates every 10 cells with percentage completion
- Running totals of unique addresses and API requests
- Final summary with total cells processed and addresses collected

## Sample Output

During execution, you'll see output like this:

```
Grid Search Configuration:
  Grid size: 0.05° cells
  Search radius: 2000.0m per cell
  Total grid cells: 56
  Place types: 8
  Maximum requests: 9000

Cell 1/56: (1.150, 103.600) → Found 5 places (5 new addresses)
Cell 2/56: (1.150, 103.650) → Found 3 places (2 new addresses)
...
Cell 10/56: (1.200, 103.750) → No results

📊 Progress: 10/56 cells completed (17.9%)
   Total addresses: 45 | API requests: 10/9000
```

## References

- [Google Places API (New) - Nearby Search Documentation](https://developers.google.com/maps/documentation/places/web-service/nearby-search)
- [Place Types Documentation](https://developers.google.com/maps/documentation/places/web-service/place-types)
- [Place Data Fields Documentation](https://developers.google.com/maps/documentation/places/web-service/data-fields)
