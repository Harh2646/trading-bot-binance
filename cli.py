#!/usr/bin/env python3
"""
cli.py – Command-line entry point for the Binance Futures Testnet trading bot.

Usage examples
--------------
# Market buy
python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Limit sell
python cli.py order --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 70000

# Stop-Limit buy (bonus order type)
python cli.py order --symbol ETHUSDT --side BUY --type STOP --quantity 0.01 \\
    --price 3500 --stop-price 3480

# Check connectivity / account balance
python cli.py ping
python cli.py account
"""
from __future__ import annotations

import sys
import argparse
import os

# Make sure the package is importable when running as a script from the project root
sys.path.insert(0, os.path.dirname(__file__))

from bot.client import BinanceClient, BinanceAPIError, BinanceNetworkError
from bot.logging_config import setup_logger
from bot.orders import place_order
from bot.validators import ValidationError

logger = setup_logger("trading_bot.cli")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client() -> BinanceClient:
    try:
        return BinanceClient()
    except ValueError as exc:
        print(f"\n  ✗  Configuration error: {exc}\n")
        logger.critical("Client init failed: %s", exc)
        sys.exit(1)


def _print_success(msg: str) -> None:
    print(f"\n  ✓  {msg}\n")


def _print_error(msg: str) -> None:
    print(f"\n  ✗  {msg}\n")


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------

def cmd_ping(args: argparse.Namespace) -> None:
    client = _make_client()
    try:
        client.ping()
        server_time = client.get_server_time()
        _print_success(f"Connected to Binance Futures Testnet  (server time: {server_time})")
    except BinanceNetworkError as exc:
        _print_error(str(exc))
        sys.exit(1)


def cmd_account(args: argparse.Namespace) -> None:
    client = _make_client()
    try:
        data = client.get_account()
        balances = [
            b for b in data.get("assets", [])
            if float(b.get("walletBalance", 0)) > 0
        ]
        print("\n  ── Account Balances ──────────────────────────")
        if balances:
            for b in balances:
                asset  = b.get("asset", "?")
                wallet = b.get("walletBalance", "0")
                avail  = b.get("availableBalance", "0")
                print(f"  {asset:10s}  wallet={wallet:>18}  available={avail:>18}")
        else:
            print("  No non-zero balances found.")
        print("  ──────────────────────────────────────────────\n")
    except (BinanceAPIError, BinanceNetworkError) as exc:
        _print_error(str(exc))
        logger.error("account command failed: %s", exc)
        sys.exit(1)


def cmd_order(args: argparse.Namespace) -> None:
    client = _make_client()
    try:
        place_order(
            client=client,
            symbol=args.symbol,
            side=args.side,
            order_type=args.type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
        _print_success("Order placed successfully.")
    except ValidationError as exc:
        _print_error(f"Invalid input – {exc}")
        logger.warning("Order rejected at validation: %s", exc)
        sys.exit(2)
    except BinanceAPIError as exc:
        _print_error(f"Exchange rejected the order – {exc}")
        sys.exit(1)
    except BinanceNetworkError as exc:
        _print_error(f"Network error – {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n  Aborted by user.\n")
        sys.exit(0)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet – CLI trading bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # -- ping ----------------------------------------------------------------
    sub.add_parser("ping", help="Check connectivity to the testnet")

    # -- account -------------------------------------------------------------
    sub.add_parser("account", help="Show non-zero account balances")

    # -- order ---------------------------------------------------------------
    order_p = sub.add_parser("order", help="Place a new order")
    order_p.add_argument(
        "--symbol", "-s",
        required=True,
        metavar="SYMBOL",
        help="Trading pair, e.g. BTCUSDT",
    )
    order_p.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL"],
        type=str.upper,
        help="BUY or SELL",
    )
    order_p.add_argument(
        "--type", "-t",
        required=True,
        dest="type",
        metavar="ORDER_TYPE",
        type=str.upper,
        help="MARKET | LIMIT | STOP | STOP_MARKET | TAKE_PROFIT | TAKE_PROFIT_MARKET",
    )
    order_p.add_argument(
        "--quantity", "-q",
        required=True,
        metavar="QTY",
        help="Order quantity (base asset)",
    )
    order_p.add_argument(
        "--price", "-p",
        default=None,
        metavar="PRICE",
        help="Limit price (required for LIMIT / STOP / TAKE_PROFIT orders)",
    )
    order_p.add_argument(
        "--stop-price",
        default=None,
        metavar="STOP_PRICE",
        help="Stop trigger price (required for STOP / STOP_MARKET / TAKE_PROFIT / TAKE_PROFIT_MARKET)",
    )

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

COMMAND_MAP = {
    "ping":    cmd_ping,
    "account": cmd_account,
    "order":   cmd_order,
}


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    handler = COMMAND_MAP.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)
    handler(args)


if __name__ == "__main__":
    main()
