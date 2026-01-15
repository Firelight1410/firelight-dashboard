# Google Places API Singapore Scraper

This Python script scrapes addresses of industrial and commercial facilities across Singapore using the Google Places API (New).

## Features

- Uses Google Places API (New) Text Search endpoint
- Searches for 8 different facility types across Singapore
- Collects unique addresses with automatic deduplication
- Respects API rate limits and request quotas
- Exports results to CSV format

## Search Types

The script searches for the following facility types:
- Manufacturing
- Logistics
- Warehousing
- Distribution
- Food processing
- Electronics manufacturing
- Chemical
- Petrochemical

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
1. Search all facility types across Singapore
2. Paginate through results (up to 60 results per search type)
3. Collect unique addresses
4. Save results to `singapore_addresses.csv`

## Output

The script generates a CSV file named `singapore_addresses.csv` with a single column:
- `address`: The formatted address of each facility

## Configuration

You can modify the following parameters in the script:

- `MAX_REQUESTS`: Maximum number of API requests (default: 9,000)
- `SEARCH_TYPES`: List of search keywords
- `SINGAPORE_BOUNDS`: Geographic boundaries for Singapore
- `OUTPUT_FILE`: Output CSV filename

## API Information

- **Endpoint**: Google Places API (New) - Text Search
- **Field**: formattedAddress (Essentials tier)
- **Coverage**: All of Singapore
- **Max results per query**: 60 (3 pages of 20 results each)

## Request Tracking

The script tracks and displays:
- Number of API requests made
- Unique addresses found per search type
- Total unique addresses collected
- Request count vs. maximum allowed

## References

- [Google Places API (New) - Text Search Documentation](https://developers.google.com/maps/documentation/places/web-service/text-search)
- [Place Types Documentation](https://developers.google.com/maps/documentation/places/web-service/place-types)
