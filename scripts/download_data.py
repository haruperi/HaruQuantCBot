#!/usr/bin/env python3
"""
Data download CLI utility for HQT Trading System.

Downloads market data from configured provider (MT5/Dukascopy), validates,
and stores in Parquet format with catalog registration.

Usage:
    python scripts/download_data.py EURUSD --timeframe H1 --start 2024-01-01 --end 2024-12-31
    python scripts/download_data.py GBPUSD --timeframe M15 --days 30
    python scripts/download_data.py XAUUSD --ticks --start "2024-01-01 09:00" --end "2024-01-01 17:00"

[REQ: DAT-FR-001 through DAT-FR-029]
[SDD: §5] Data Layer
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from hqt.data.models.bar import Timeframe
from hqt.data.providers.dukascopy_provider import DukascopyProvider
from hqt.data.providers.mt5_provider import MT5DataProvider
from hqt.data.storage.catalog import DataCatalog
from hqt.data.storage.manager import StorageManager
from hqt.data.storage.parquet_store import ParquetStore


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Download market data and store in HQT data infrastructure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download 1 year of hourly EUR/USD data
  %(prog)s EURUSD --timeframe H1 --start 2024-01-01 --end 2024-12-31

  # Download last 30 days of 15-minute GBP/USD data
  %(prog)s GBPUSD --timeframe M15 --days 30

  # Download tick data for a specific day
  %(prog)s XAUUSD --ticks --start "2024-01-15 09:00" --end "2024-01-15 17:00"

  # Download with custom provider
  %(prog)s EURUSD --timeframe H1 --days 7 --provider dukascopy
        """,
    )

    parser.add_argument(
        "symbol", type=str, help="Trading symbol (e.g., EURUSD, GBPUSD, XAUUSD)"
    )

    # Timeframe options (mutually exclusive)
    time_group = parser.add_mutually_exclusive_group(required=True)
    time_group.add_argument(
        "--timeframe",
        "-t",
        type=str,
        choices=[
            "M1",
            "M2",
            "M3",
            "M4",
            "M5",
            "M6",
            "M10",
            "M12",
            "M15",
            "M20",
            "M30",
            "H1",
            "H2",
            "H3",
            "H4",
            "H6",
            "H8",
            "H12",
            "D1",
            "W1",
            "MN1",
        ],
        help="Bar timeframe",
    )
    time_group.add_argument(
        "--ticks", action="store_true", help="Download tick data instead of bars"
    )

    # Date range options
    date_group = parser.add_argument_group("date range (choose one)")
    range_group = date_group.add_mutually_exclusive_group(required=True)
    range_group.add_argument(
        "--start",
        type=str,
        metavar="DATETIME",
        help='Start date/time (format: "YYYY-MM-DD" or "YYYY-MM-DD HH:MM")',
    )
    range_group.add_argument(
        "--days", type=int, metavar="N", help="Download last N days (from now)"
    )

    parser.add_argument(
        "--end",
        type=str,
        metavar="DATETIME",
        help='End date/time (format: "YYYY-MM-DD" or "YYYY-MM-DD HH:MM"). Default: now',
    )

    # Provider options
    parser.add_argument(
        "--provider",
        "-p",
        type=str,
        default="mt5",
        choices=["mt5", "dukascopy"],
        help="Data provider (default: mt5)",
    )

    # Storage options
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/parquet",
        help="Data storage directory (default: data/parquet)",
    )
    parser.add_argument(
        "--catalog-db",
        type=str,
        default="data/catalog.db",
        help="Catalog database path (default: data/catalog.db)",
    )

    # Validation options
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip data validation (not recommended)",
    )
    parser.add_argument(
        "--validation-level",
        type=str,
        default="normal",
        choices=["strict", "normal", "permissive"],
        help="Validation strictness (default: normal)",
    )

    # Output options
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Minimal output (errors only)"
    )

    return parser.parse_args()


def parse_datetime(date_str: str) -> datetime:
    """Parse datetime string in flexible format."""
    # Try different formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    raise ValueError(
        f"Invalid datetime format: {date_str}. Use YYYY-MM-DD or YYYY-MM-DD HH:MM"
    )


def print_info(msg: str, verbose: bool = True, quiet: bool = False):
    """Print info message."""
    if not quiet and verbose:
        print(f"[INFO] {msg}")


def print_error(msg: str):
    """Print error message."""
    print(f"[ERROR] {msg}", file=sys.stderr)


def print_success(msg: str, quiet: bool = False):
    """Print success message."""
    if not quiet:
        print(f"[SUCCESS] {msg}")


def main():
    """Main entry point."""
    args = parse_args()

    try:
        # Parse dates
        if args.days:
            end = datetime.now()
            start = end - timedelta(days=args.days)
        else:
            start = parse_datetime(args.start)
            end = parse_datetime(args.end) if args.end else datetime.now()

        # Validate date range
        if start >= end:
            print_error("Start date must be before end date")
            return 1

        # Parse timeframe
        timeframe = Timeframe(args.timeframe) if args.timeframe else None

        # Print configuration
        print_info("=== HQT Data Download ===", args.verbose, args.quiet)
        print_info(f"Symbol: {args.symbol}", args.verbose, args.quiet)
        print_info(
            f"Type: {'Ticks' if args.ticks else f'Bars ({args.timeframe})'}",
            args.verbose,
            args.quiet,
        )
        print_info(f"Start: {start.strftime('%Y-%m-%d %H:%M:%S')}", args.verbose, args.quiet)
        print_info(f"End: {end.strftime('%Y-%m-%d %H:%M:%S')}", args.verbose, args.quiet)
        print_info(f"Provider: {args.provider}", args.verbose, args.quiet)
        print_info("", args.verbose, args.quiet)

        # Initialize components
        print_info("Initializing data provider...", args.verbose, args.quiet)
        if args.provider == "mt5":
            provider = MT5DataProvider()
        elif args.provider == "dukascopy":
            provider = DukascopyProvider()
        else:
            print_error(f"Unknown provider: {args.provider}")
            return 1

        print_info("Initializing storage...", args.verbose, args.quiet)
        store = ParquetStore(args.data_dir)
        catalog = DataCatalog(args.catalog_db)
        manager = StorageManager(store=store, catalog=catalog)

        try:
            # Download and store
            print_info(
                f"Downloading {args.symbol} data from {args.provider}...",
                args.verbose,
                args.quiet,
            )


            result = manager.download_and_store(
                provider=provider,
                symbol=args.symbol,
                timeframe=timeframe,
                start=start,
                end=end,
                validate=not args.no_validate,
                validate_critical_only=(args.validation_level != "permissive"),
            )

            # Print results
            if result["total_rows"] > 0:
                print_success(
                    f"Downloaded and stored {result['total_rows']} rows", args.quiet
                )
             
                print_info(f"Partitions: {', '.join(result['partitions'])}", args.verbose, args.quiet)

                if result.get("validation_report"):
                    report = result["validation_report"]
                    print_info(
                        f"Validation: {report.total_issues} issues found",
                        args.verbose,
                        args.quiet,
                    )
                    if args.verbose and report.total_issues > 0:
                        print_info(f"  Critical: {report.critical_count}", args.verbose, args.quiet)
                        print_info(f"  Errors: {report.error_count}", args.verbose, args.quiet)
                        print_info(f"  Warnings: {report.warning_count}", args.verbose, args.quiet)

                return 0
            else:
                print_error("No data downloaded")
                return 1

        finally:
            catalog.close()

    except KeyboardInterrupt:
        print_error("Interrupted by user")
        return 130
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
