# Marshall Daily Price Tracker

This sub-project automates the daily collection and visualization of Marshall product prices across multiple retailers in Vietnam.

## Project Structure

- `scraper.py`: Unified Playwright scraper for FPT, MW, and CellPhoneS Marshall URLs.
- `dashboard_generator.py`: Generates a modern HTML dashboard (`index.html`) using historical data.
- `content/`: Directory containing daily CSV snapshots (`YYYY-MM-DD.csv`).
- `run_workflow.sh`: Main automation script (Scrape -> Generate -> Push).
- `index.html`: The generated dashboard, ready for GitHub Pages.

## Usage

### Prerequisites
- Python 3.x
- Pandas (`pip install pandas`)
- Playwright (`pip install playwright` + `playwright install`)

### Manual Run
```bash
./run_workflow.sh
```

### Automation
Setup a crontab on your Mac to run this script daily:
```bash
0 9 * * * /path/to/projects/marshall_daily/run_workflow.sh
```
