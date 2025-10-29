# Stock Closing Price Fetcher

This script fetches closing prices for a predefined list of ticker symbols on a specified date using the Yahoo Finance API via the `yfinance` library.

## Features

- Fetches closing prices for 100+ predefined tickers
- Configurable target date
- Handles weekends and holidays by finding the nearest trading day
- Exports results to CSV
- Error handling for failed ticker lookups
- Command-line support for date specification

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Method 1: Edit the script

Open `fetch_closing_prices.py` and modify the `TARGET_DATE` variable on line 109:

```python
TARGET_DATE = "2024-12-31"  # Change this to your desired date (YYYY-MM-DD)
```

Then run:

```bash
python fetch_closing_prices.py
```

### Method 2: Command-line argument

Pass the date as a command-line argument:

```bash
python fetch_closing_prices.py 2024-12-31
```

## Output

The script will:

1. Display progress as it fetches each ticker
2. Show a summary of successful and failed lookups
3. Export results to a CSV file named `closing_prices_YYYY-MM-DD.csv`

Example output:

```
============================================================
Stock Closing Price Fetcher
============================================================

Fetching closing prices for 100 tickers on 2024-12-31...
(Searching between 2024-12-26 and 2025-01-02 to account for weekends/holidays)

  ACP: $8.45
  ACV: $12.30
  ARDC: $15.67
  ...

============================================================
Summary:
  Successful: 98/100
  Failed: 2/100

Failed tickers: XYZ, ABC

Results exported to: closing_prices_2024-12-31.csv
============================================================
Done!
```

## Ticker List

The script includes the following tickers:

ACP, ACV, ARDC, AVK, AWF, BANX, BCV, BGH, BGT, BHK, BIT, BLW, BTZ, BWG, CCD, CHI, CHY, CIK, DBL, DFP, DHF, DHY, DLY, DMO, DSL, DSU, EAD, ECC, EDD, EDF, EHI, EIC, EMD, ERC, EVG, EVV, FAX, FCT, FFC, FPF, FRA, FTF, GBAB, GCV, GDO, GHY, GOF, HIO, HIX, HPF, HPI, HPS, HYI, HYT, ISD, JFR, JGH, JHI, JLS, JPC, JQC, KIO, LDP, MCI, MPV, MSD, NBB, NCV, NCZ, NHS, NPCT, OCCI, OPP, OXLC, PCM, PCN, PDI, PDO, PDX, PFD, PFL, PFN, PFO, PHK, PIM, PPT, PSF, PTA, PTY, RA, RCS, TEI, VGI, VLT, VVR, WDI, WEA, WIA, WIW, XFLT

## Modifying the Ticker List

To add or remove tickers, edit the `TICKERS` list in `fetch_closing_prices.py` starting at line 12.

## CSV Output Format

The CSV file contains three columns:

- `Ticker`: The ticker symbol
- `Closing_Price`: The closing price (or None if unavailable)
- `Date`: The target date

## Notes

- The script automatically handles weekends and holidays by searching for the nearest available trading day
- If a ticker is not found or has no data, it will be marked as failed and the price will be None in the CSV
- The yfinance library fetches data from Yahoo Finance, which may have delays or limitations

## Requirements

- Python 3.7+
- yfinance
- pandas

## License

This script is provided as-is for fetching historical stock data.
