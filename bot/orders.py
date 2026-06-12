from __future__ import annotations

from decimal import Decimal
from typing import Any

from .client import BinanceClient, BinanceAPIError, BinanceNetworkError
from .logging_config import setup_logger
from .validators import validate_order_inputs, ValidationError

logger = setup_logger("trading_bot.orders")


def _fmt(value: Any, decimals: int = 8) -> str:
    """Return a clean string for a numeric value, stripping trailing zeros."""
    try:
        return f"{Decimal(str(value)):.{decimals}f}".rstrip("0").rstrip(".")
    except Exception:
        return str(value)


def _build_order_params(validated: dict) -> dict:
    """Convert validated inputs into the parameter dict expected by the API."""
    params: dict[str, Any] = {
        "symbol": validated["symbol"],
        "side": validated["side"],
        "type": validated["order_type"],
        "quantity": str(validated["quantity"]),
    }

    ot = validated["order_type"]

    if ot == "LIMIT":
        params["price"] = str(validated["price"])
        params["timeInForce"] = "GTC"

    elif ot in {"STOP", "TAKE_PROFIT"}:
        params["price"] = str(validated["price"])
        params["stopPrice"] = str(validated["stop_price"])
        params["timeInForce"] = "GTC"

    elif ot in {"STOP_MARKET", "TAKE_PROFIT_MARKET"}:
        params["stopPrice"] = str(validated["stop_price"])

    return params


def print_order_summary(validated: dict) -> None:
    ot = validated["order_type"]
    lines = [
        "",
        "  ┌─ Order Request ──────────────────────────────",
        f"  │  Symbol     : {validated['symbol']}",
        f"  │  Side       : {validated['side']}",
        f"  │  Type       : {ot}",
        f"  │  Quantity   : {_fmt(validated['quantity'])}",
    ]
    if validated.get("price"):
        lines.append(f"  │  Price      : {_fmt(validated['price'])}")
    if validated.get("stop_price"):
        lines.append(f"  │  Stop Price : {_fmt(validated['stop_price'])}")
    lines.append("  └──────────────────────────────────────────────")
    print("\n".join(lines))


def print_order_response(response: dict) -> None:
    order_id   = response.get("orderId", "N/A")
    status     = response.get("status", "N/A")
    exec_qty   = response.get("executedQty", "0")
    avg_price  = response.get("avgPrice", response.get("price", "N/A"))
    client_id  = response.get("clientOrderId", "N/A")
    symbol     = response.get("symbol", "N/A")
    side       = response.get("side", "N/A")
    otype      = response.get("type", "N/A")

    lines = [
        "",
        "  ┌─ Order Response ─────────────────────────────",
        f"  │  Order ID    : {order_id}",
        f"  │  Client ID   : {client_id}",
        f"  │  Symbol      : {symbol}",
        f"  │  Side        : {side}",
        f"  │  Type        : {otype}",
        f"  │  Status      : {status}",
        f"  │  Executed    : {_fmt(exec_qty)}",
        f"  │  Avg Price   : {_fmt(avg_price)}",
        "  └──────────────────────────────────────────────",
        "",
    ]
    print("\n".join(lines))


def place_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: str | float | None = None,
    stop_price: str | float | None = None,
) -> dict:
    """
    Validate inputs, log the request, call the API, log and return the response.

    Raises ValidationError, BinanceAPIError, or BinanceNetworkError on failure.
    """
    try:
        validated = validate_order_inputs(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
        )
    except ValidationError as exc:
        logger.warning("Validation failed: %s", exc)
        raise

    logger.info(
        "Placing %s %s order on %s  qty=%s  price=%s  stop_price=%s",
        validated["side"],
        validated["order_type"],
        validated["symbol"],
        validated["quantity"],
        validated.get("price"),
        validated.get("stop_price"),
    )

    print_order_summary(validated)

    params = _build_order_params(validated)

    try:
        response = client.new_order(**params)
    except BinanceAPIError as exc:
        logger.error("API rejected the order: %s", exc)
        raise
    except BinanceNetworkError as exc:
        logger.error("Network error while placing order: %s", exc)
        raise

    logger.info(
        "Order accepted – id=%s  status=%s  executedQty=%s  avgPrice=%s",
        response.get("orderId"),
        response.get("status"),
        response.get("executedQty"),
        response.get("avgPrice", response.get("price")),
    )

    print_order_response(response)
    return response
