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

1. Generate sample data:

```bash
python -m intraday_trading.main --generate-sample /home/runner/work/machine-learning/machine-learning/sample_ohlcv.csv
```

2. Run the trading simulation + walk-forward check:

```bash
python -m intraday_trading.main --csv /home/runner/work/machine-learning/machine-learning/sample_ohlcv.csv
```

3. Run tests:

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
