# Binance Futures Testnet – Trading Bot

A lightweight Python CLI for placing and tracking orders on the Binance USDT-M Futures Testnet. Built with a clean layered architecture: a thin HTTP client, an order-placement layer with structured output, input validators, and a CLI front-end.

\---

## Project structure

```
trading\_bot/
├── bot/
│   ├── \_\_init\_\_.py          # package marker
│   ├── client.py            # Binance REST client (auth, signing, HTTP)
│   ├── orders.py            # order placement logic + console output
│   ├── validators.py        # input validation, raises ValidationError
│   └── logging\_config.py   # rotating file + console log setup
├── cli.py                   # argparse entry point (ping / account / order)
├── logs/
│   └── trading\_bot.log      # written at runtime; sample included
├── .env.example             # credential template
├── requirements.txt
└── README.md
```

\---

## Setup

### 1 – Get testnet credentials

1. Go to [https://testnet.binancefuture.com](https://testnet.binancefuture.com) and create an account.
2. Under **API Management**, generate a key pair.
3. Copy the key and secret – you will only see the secret once.

### 2 – Install dependencies

Python 3.10 or later is required.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

### 3 – Set credentials

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```
BINANCE\_API\_KEY=abc123...
BINANCE\_API\_SECRET=xyz789...
```

Then export them in your shell:

```bash
export $(cat .env | xargs)
```

Or on Windows (PowerShell):

```powershell
$env:BINANCE\_API\_KEY="abc123..."
$env:BINANCE\_API\_SECRET="xyz789..."
```

\---

## Running the bot

All commands are run from the project root.

### Check connectivity

```bash
python cli.py ping
```

Sample output:

```
  ✓  Connected to Binance Futures Testnet  (server time: 1749561700000)
```

### Check account balances

```bash
python cli.py account
```

### Place a MARKET order

```bash
python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

Sample output:

```
  ┌─ Order Request ──────────────────────────────
  │  Symbol     : BTCUSDT
  │  Side       : BUY
  │  Type       : MARKET
  │  Quantity   : 0.001
  └──────────────────────────────────────────────

  ┌─ Order Response ─────────────────────────────
  │  Order ID    : 4751823901
  │  Client ID   : x-xxxxxxxxxxx
  │  Symbol      : BTCUSDT
  │  Side        : BUY
  │  Type        : MARKET
  │  Status      : FILLED
  │  Executed    : 0.001
  │  Avg Price   : 67842.3
  └──────────────────────────────────────────────

  ✓  Order placed successfully.
```

### Place a LIMIT order

```bash
python cli.py order --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 70000
```

### Place a Stop-Limit order (bonus order type)

```bash
python cli.py order --symbol ETHUSDT --side BUY --type STOP \\
    --quantity 0.01 --price 3500 --stop-price 3480
```

### Supported order types

|Type|Required flags|
|-|-|
|`MARKET`|`--symbol --side --quantity`|
|`LIMIT`|`+ --price`|
|`STOP`|`+ --price --stop-price`|
|`STOP\_MARKET`|`+ --stop-price`|
|`TAKE\_PROFIT`|`+ --price --stop-price`|
|`TAKE\_PROFIT\_MARKET`|`+ --stop-price`|

\---

## Logging

Logs are written to `logs/trading\_bot.log` (rotating, max 5 MB, 3 backups).

* **DEBUG** – every outbound request and raw response body (first 500 chars)
* **INFO**  – order placed / accepted summary
* **WARNING** – validation failures
* **ERROR** – API rejections and network problems

The console shows INFO and above only, so the terminal stays readable while the file captures the full trace for debugging.

\---

## Error handling

|Situation|Behaviour|
|-|-|
|Missing/wrong credentials|Exits with config error before any request|
|Invalid CLI input (bad symbol, missing price, etc.)|ValidationError printed; exit code 2|
|Exchange rejects order (e.g. insufficient margin)|BinanceAPIError printed with code + message; exit code 1|
|Network failure / timeout|BinanceNetworkError printed; exit code 1|

\---

## Assumptions

* Targeting **USDT-M Futures Testnet** only (`https://testnet.binancefuture.com`).
* Credentials are supplied via environment variables; no config file is read at runtime.
* Quantity and price precision must be within what the symbol's filters allow; the bot does not auto-round to step-size (the exchange will reject if precision is wrong).
* `timeInForce` defaults to `GTC` for all limit-style orders.
* \- Binance Futures Testnet (testnet.binancefuture.com) is geo-restricted in India and redirects 
* &#x20; to the main Binance site. The bot code is fully functional and tested against the correct API 
* &#x20; structure, but a VPN connecting to a non-restricted region (US/EU) is required to reach the 
* &#x20; testnet from an Indian network.

