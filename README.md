# machine-learning

Automatic intraday trading system scaffold focused on **local paper-trading/backtesting**.

## Important safety and scope warnings

- This repository is for **education and simulation only**.
- It is **not financial advice** and does **not** guarantee recommendations or returns.
- It does **not** connect to a broker and does **not** place live orders.
- Suggested buy/sell timing is generated from supplied historical/replay CSV data and can be wrong.

## What is implemented

- Environment-variable based configuration (`IT_*`)
- CSV OHLCV ingestion, normalization, validation, and data-gap detection
- Composite strategy framework (trend, mean-reversion, breakout) + optional ML signal filter
- Paper execution engine with fees/slippage simulation
- Risk controls (position sizing, max daily loss, max drawdown, trade limits, breakers)
- Walk-forward validation helper
- Local Streamlit dashboard for visualizing results and transparent non-live signals

## Setup

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

### Windows PowerShell

```powershell
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Optional config template:

```bash
# macOS/Linux
cp .env.example .env
```

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

## CLI usage (existing behavior preserved)

Generate sample data:

```bash
python -m intraday_trading.main --generate-sample data/sample_ohlcv.csv
```

Run simulation + walk-forward output:

```bash
python -m intraday_trading.main --csv data/sample_ohlcv.csv
```

Run tests:

```bash
python -m unittest discover -s tests
```

## Dashboard usage

Launch locally:

```bash
streamlit run intraday_trading/dashboard.py
```

In the dashboard you can:

- Upload an OHLCV CSV or use generated sample data
- Configure symbol, timeframe, initial capital, per-trade risk, max daily loss, max drawdown, stop loss, take profit, and max position size
- Run backtest simulation + walk-forward validation
- View:
  - Candlestick chart and BUY/SELL markers
  - Equity curve and drawdown
  - PnL, trade count, win rate (when exits exist), data-gap count
  - Trade table (`timestamp`, `side`, `price`, `quantity`, `stop_loss`, `take_profit`, `realized_pnl`, `reason`)
- See latest transparent BUY/SELL/HOLD/NO_TRADE recommendation with estimated risk, stop-loss/take-profit, quantity, and explanation
- Rank user-provided symbol lists **only when matching symbol CSVs are uploaded**; missing files are marked as insufficient data

## Expected CSV schema

Required columns:

- `timestamp` (ISO-8601, for example `2026-01-02T09:15:00+00:00`)
- `open`
- `high`
- `low`
- `close`
- `volume`

Example:

```csv
timestamp,open,high,low,close,volume
2026-01-02T09:15:00+00:00,2500,2501.2,2498.7,2500.4,8200
2026-01-02T09:20:00+00:00,2500.4,2502.1,2499.9,2501.7,7900
```

If CSV data is missing/invalid (missing columns, parse errors, invalid OHLC constraints, empty history), the CLI/helpers/dashboard fail gracefully with actionable error messages.
