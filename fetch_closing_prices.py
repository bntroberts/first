#!/usr/bin/env python3
"""
Fetch closing prices for a list of ticker symbols on a specified date.

This script retrieves historical closing prices for multiple tickers
using the yfinance library.
"""

import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import sys

# List of tickers to fetch
TICKERS = [
    "ACP", "ACV", "ARDC", "AVK", "AWF", "BANX", "BCV", "BGH", "BGT", "BHK",
    "BIT", "BLW", "BTZ", "BWG", "CCD", "CHI", "CHY", "CIK", "DBL", "DFP",
    "DHF", "DHY", "DLY", "DMO", "DSL", "DSU", "EAD", "ECC", "EDD", "EDF",
    "EHI", "EIC", "EMD", "ERC", "EVG", "EVV", "FAX", "FCT", "FFC", "FPF",
    "FRA", "FTF", "GBAB", "GCV", "GDO", "GHY", "GOF", "HIO", "HIX", "HPF",
    "HPI", "HPS", "HYI", "HYT", "ISD", "JFR", "JGH", "JHI", "JLS", "JPC",
    "JQC", "KIO", "LDP", "MCI", "MPV", "MSD", "NBB", "NCV", "NCZ", "NHS",
    "NPCT", "OCCI", "OPP", "OXLC", "PCM", "PCN", "PDI", "PDO", "PDX", "PFD",
    "PFL", "PFN", "PFO", "PHK", "PIM", "PPT", "PSF", "PTA", "PTY", "RA",
    "RCS", "TEI", "VGI", "VLT", "VVR", "WDI", "WEA", "WIA", "WIW", "XFLT"
]


def fetch_closing_prices(tickers, target_date):
    "2025-10-28"
    Fetch closing prices for a list of tickers on a specified date.

    Args:
        tickers (list): List of ticker symbols
        target_date (str): Date in YYYY-MM-DD format

    Returns:
        dict: Dictionary mapping ticker symbols to their closing prices
    """
    # Parse the target date
    try:
        date_obj = datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        print(f"Error: Invalid date format. Please use YYYY-MM-DD format.")
        sys.exit(1)

    # Calculate date range (get a few days around the target to handle weekends/holidays)
    start_date = (date_obj - timedelta(days=5)).strftime("%Y-%m-%d")
    end_date = (date_obj + timedelta(days=2)).strftime("%Y-%m-%d")

    print(f"Fetching closing prices for {len(tickers)} tickers on {target_date}...")
    print(f"(Searching between {start_date} and {end_date} to account for weekends/holidays)\n")

    results = {}
    failed_tickers = []

    for ticker in tickers:
        try:
            # Fetch historical data
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)

            if hist.empty:
                print(f"  {ticker}: No data available")
                failed_tickers.append(ticker)
                results[ticker] = None
                continue

            # Try to get the exact date, or the closest available date
            if target_date in hist.index.strftime("%Y-%m-%d").tolist():
                close_price = hist.loc[hist.index.strftime("%Y-%m-%d") == target_date, 'Close'].iloc[0]
                print(f"  {ticker}: ${close_price:.2f}")
            else:
                # Get the closest date
                closest_date = hist.index[-1]
                close_price = hist['Close'].iloc[-1]
                print(f"  {ticker}: ${close_price:.2f} (from {closest_date.strftime('%Y-%m-%d')})")

            results[ticker] = close_price

        except Exception as e:
            print(f"  {ticker}: Error - {str(e)}")
            failed_tickers.append(ticker)
            results[ticker] = None

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Successful: {len([v for v in results.values() if v is not None])}/{len(tickers)}")
    print(f"  Failed: {len(failed_tickers)}/{len(tickers)}")

    if failed_tickers:
        print(f"\nFailed tickers: {', '.join(failed_tickers)}")

    return results


def export_to_csv(results, target_date, filename=None):
    """
    Export results to a CSV file.

    Args:
        results (dict): Dictionary of ticker -> price mappings
        target_date (str): The target date
        filename (str): Output filename (optional)
    """
    if filename is None:
        filename = f"closing_prices_{target_date}.csv"

    df = pd.DataFrame([
        {"Ticker": ticker, "Closing_Price": price, "Date": target_date}
        for ticker, price in results.items()
    ])

    df.to_csv(filename, index=False)
    print(f"\nResults exported to: {filename}")


if __name__ == "__main__":
    # CONFIGURE YOUR TARGET DATE HERE
    # Format: YYYY-MM-DD
    TARGET_DATE = "2024-12-31"  # Example: December 31, 2024

    # You can also pass the date as a command-line argument
    if len(sys.argv) > 1:
        TARGET_DATE = sys.argv[1]

    print(f"{'='*60}")
    print(f"Stock Closing Price Fetcher")
    print(f"{'='*60}\n")

    # Fetch the closing prices
    results = fetch_closing_prices(TICKERS, TARGET_DATE)

    # Export to CSV
    export_to_csv(results, TARGET_DATE)

    print(f"\n{'='*60}")
    print("Done!")
