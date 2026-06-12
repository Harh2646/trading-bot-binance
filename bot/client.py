from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any
from urllib.parse import urlencode

import requests

from .logging_config import setup_logger

logger = setup_logger("trading_bot.client")

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_TIMEOUT = 10


class BinanceAPIError(Exception):
    """Wraps an error response returned by the Binance API."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


class BinanceNetworkError(ConnectionError):
    """Raised when a network-level failure occurs."""


class BinanceClient:
    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        base_url: str = TESTNET_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.api_key = api_key or os.environ.get("BINANCE_API_KEY", "")
        self.api_secret = api_secret or os.environ.get("BINANCE_API_SECRET", "")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        if not self.api_key or not self.api_secret:
            raise ValueError(
                "API key and secret are required. "
                "Set BINANCE_API_KEY and BINANCE_API_SECRET environment variables "
                "or pass them explicitly."
            )

        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self.api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.debug("BinanceClient initialised – base_url=%s", self.base_url)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sign(self, params: dict) -> dict:
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        signed: bool = False,
    ) -> Any:
        url = f"{self.base_url}{endpoint}"
        params = params or {}

        if signed:
            params = self._sign(params)

        logger.debug(
            "→ %s %s  params=%s",
            method.upper(),
            endpoint,
            {k: v for k, v in params.items() if k != "signature"},
        )

        try:
            response = self._session.request(
                method,
                url,
                params=params if method.upper() == "GET" else None,
                data=params if method.upper() != "GET" else None,
                timeout=self.timeout,
            )
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network failure reaching %s: %s", url, exc)
            raise BinanceNetworkError(f"Cannot reach Binance API: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            logger.error("Request to %s timed out after %ss", url, self.timeout)
            raise BinanceNetworkError(f"Request timed out after {self.timeout}s") from exc

        logger.debug("← HTTP %s  body=%s", response.status_code, response.text[:500])

        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
            return {}

        if isinstance(data, dict) and "code" in data and int(data["code"]) < 0:
            raise BinanceAPIError(data["code"], data.get("msg", "unknown error"))

        if not response.ok:
            response.raise_for_status()

        return data

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        self._request("GET", "/fapi/v1/ping")
        logger.info("Ping successful")
        return True

    def get_server_time(self) -> int:
        data = self._request("GET", "/fapi/v1/time")
        return data["serverTime"]

    def get_exchange_info(self, symbol: str | None = None) -> dict:
        params = {"symbol": symbol} if symbol else {}
        return self._request("GET", "/fapi/v1/exchangeInfo", params=params)

    def get_account(self) -> dict:
        return self._request("GET", "/fapi/v2/account", signed=True)

    def new_order(self, **params) -> dict:
        return self._request("POST", "/fapi/v1/order", params=params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> dict:
        return self._request(
            "GET",
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        return self._request(
            "DELETE",
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )
