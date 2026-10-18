# machine-learning

Automatic intraday trading system scaffold (educational/paper-trading first).

## What is implemented

- Scope and constraints configuration (exchange, symbol, timeframe, risk/position limits)
- Data layer for historical and replayed real-time candles from CSV
- Data validation, UTC timestamp normalization, and gap detection
- Strategy framework with trend-following, mean-reversion, and breakout strategies
- Optional ML signal filter using a lightweight logistic model
- Risk management engine with:
  - per-trade risk-based sizing
  - max daily loss breaker
  - max drawdown breaker
  - max trades/day and consecutive loss breaker
  - spread/slippage guards
- Paper execution engine with fees/slippage simulation
- Monitoring events + kill switch
- Walk-forward validation helper
- Tests for key risk/data/strategy behavior

## Quick start

This project is a **paper-trading/backtesting simulation**. It currently reads CSV market data only. No broker API credentials are required.

1. Create and activate a virtual environment:

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
```

2. Install the project from your cloned checkout:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

3. Copy and configure environment defaults (optional overrides):

```bash
# macOS/Linux:
cp .env.example .env
# Windows PowerShell:
# Copy-Item .env.example .env
```

The app reads runtime overrides from OS environment variables (for example `IT_SYMBOL`, `IT_EXCHANGE`, `IT_TIMEFRAME_MINUTES`). `.env` is a safe template for local configuration, and is not committed.

4. Generate sample OHLCV CSV data (relative paths are supported):

```bash
python -m intraday_trading.main --generate-sample data/sample_ohlcv.csv
```

5. Run the trading simulation + walk-forward check:

```bash
python -m intraday_trading.main --csv data/sample_ohlcv.csv
```

6. Run tests:

```bash
python -m unittest discover -s tests
```

## Data format

CSV must contain columns:

- `timestamp` (ISO format)
- `open`
- `high`
- `low`
- `close`
- `volume`

## Important

This is a framework baseline for controlled risk and automated execution flow. It does **not** guarantee profits and should be validated extensively in simulation/paper trading before any live deployment.
