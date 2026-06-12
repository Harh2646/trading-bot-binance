from __future__ import annotations

from decimal import Decimal, InvalidOperation


VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET", "STOP", "TAKE_PROFIT", "TAKE_PROFIT_MARKET"}
VALID_SIDES = {"BUY", "SELL"}
VALID_TIME_IN_FORCE = {"GTC", "IOC", "FOK", "GTX"}


class ValidationError(ValueError):
    """Raised when user-supplied inputs fail validation."""


def validate_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if not s.isalpha() or len(s) < 5:
        raise ValidationError(
            f"'{symbol}' is not a valid symbol. Expected something like BTCUSDT or ETHUSDT."
        )
    return s


def validate_side(side: str) -> str:
    s = side.strip().upper()
    if s not in VALID_SIDES:
        raise ValidationError(
            f"'{side}' is not a valid side. Choose BUY or SELL."
        )
    return s


def validate_order_type(order_type: str) -> str:
    t = order_type.strip().upper()
    if t not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"'{order_type}' is not a supported order type. "
            f"Choose from: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return t


def validate_quantity(quantity: str | float) -> Decimal:
    try:
        q = Decimal(str(quantity))
    except InvalidOperation:
        raise ValidationError(f"'{quantity}' is not a valid quantity.")
    if q <= 0:
        raise ValidationError("Quantity must be greater than zero.")
    return q


def validate_price(price: str | float | None) -> Decimal | None:
    if price is None:
        return None
    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValidationError(f"'{price}' is not a valid price.")
    if p <= 0:
        raise ValidationError("Price must be greater than zero.")
    return p


def validate_stop_price(stop_price: str | float | None) -> Decimal | None:
    if stop_price is None:
        return None
    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValidationError(f"'{stop_price}' is not a valid stop price.")
    if sp <= 0:
        raise ValidationError("Stop price must be greater than zero.")
    return sp


def validate_order_inputs(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: str | float | None = None,
    stop_price: str | float | None = None,
) -> dict:
    validated = {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": validate_order_type(order_type),
        "quantity": validate_quantity(quantity),
        "price": None,
        "stop_price": None,
    }

    ot = validated["order_type"]

    if ot == "LIMIT":
        if price is None:
            raise ValidationError("A price is required for LIMIT orders.")
        validated["price"] = validate_price(price)

    elif ot in {"STOP", "TAKE_PROFIT"}:
        if price is None:
            raise ValidationError(f"A limit price is required for {ot} orders.")
        if stop_price is None:
            raise ValidationError(f"A stop price is required for {ot} orders.")
        validated["price"] = validate_price(price)
        validated["stop_price"] = validate_stop_price(stop_price)

    elif ot in {"STOP_MARKET", "TAKE_PROFIT_MARKET"}:
        if stop_price is None:
            raise ValidationError(f"A stop price is required for {ot} orders.")
        validated["stop_price"] = validate_stop_price(stop_price)

    return validated
