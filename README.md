# Blocket.se Job Scraper

This project is a web scraper built using the **Scrapy** framework to collect job listings from the Swedish job portal [Blocket.se](https://www.blocket.se). 

The scraper saves collected data into an **SQLite** database and generates two Excel files:
1. **`job_data.xlsx`**: Stores the results of the current scrape.
2. **`job_data_from_db.xlsx`**: Exports all data from the database after the scraper finishes.

## Features

- **SQLite database support**: Saves scraped data in a structured database for persistent storage.
- **Incremental scraping**: Supports bypassing duplicate filtering for pages based on configurable rules (e.g., refresh interval).
- **Customizable settings**: Flexible settings for concurrency, duplicate filtering, and export behavior.
- **Excel exports**:
  - Incremental results during scraping.
  - Final dataset export after scraping.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/pitergon/blocket-scraper.git
   cd blocket-scraper
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Configure settings:
   - Default Scrapy settings can be modified in `settings.py`.
   - Custom scraper-specific settings are located in `custom_settings.py`.

   Example (`custom_settings.py`):
   ```python
   SQLITE_FILE = "blocket.db"
   JOBDIR = "spider_data"
   EXCEL_FILE_INCREMENTAL = "job_data.xlsx"
   EXCEL_FILE_FROM_DB = "job_data_from_db.xlsx"
   SAVE_JOB_DESCRIPTION = True
   REFRESH_MODE = True
   REFRESH_DAYS = 14
   MAX_CATEGORY_PAGE_NUMBER = 1
   ```

2. Run the scraper:
   ```bash
   scrapy crawl blocket
   ```

3. After completion:
   - View the current results in `job_data.xlsx`.
   - Access the full dataset from the SQLite database in `job_data_from_db.xlsx`.

## Settings Overview

### `custom_settings.py`
- **`SQLITE_FILE`**: Name of the SQLite database file.
- **`EXCEL_FILE_INCREMENTAL`**: Path to the Excel file storing incremental results.
- **`EXCEL_FILE_FROM_DB`**: Path to the Excel file exporting the final database.
- **`REFRESH_MODE`**: Allows bypassing duplicate filtering for specific pages.
- **`REFRESH_DAYS`**: Maximum age (in days) for job postings to bypass duplicate filtering.
- **`MAX_CATEGORY_PAGE_NUMBER`**: Limits the number of pages scraped per category.
- **`SAVE_JOB_DESCRIPTION`**: Toggles saving detailed job descriptions.

### Scrapy Extensions and Pipelines
- **LoggingExtension**: Enhanced logging for debugging and tracking scraper performance.
- **DbExtension**: Ensures proper handling of the SQLite database.
- **JobPipeline**: Processes and cleans scraped data.
- **DatabasePipeline**: Stores items in the SQLite database.
- **ExcelSavePipeline**: Saves incremental results to an Excel file.
- **ExcelFinalExportPipeline**: Exports the full database to an Excel file at the end.

### Performance Settings
- **`CONCURRENT_REQUESTS`**: Number of concurrent requests (default: 16).
- **`DOWNLOAD_DELAY`**: Delay between requests to avoid being blocked (default: 0.2 seconds).
- **`AUTOTHROTTLE_ENABLED`**: Enables adaptive request throttling.

## Requirements

- Python 3.10+
- Scrapy
- SQLite
- `openpyxl` (for Excel export)

Install dependencies via:
```bash
pip install scrapy openpyxl
```

### Author
Created by [Petro Honcharov](https://github.com/pitergon).
