from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .backtest import walk_forward_validate
from .config import default_config
from .data import Candle, CSVDataProvider, DataPipeline
from .execution import PaperBroker
from .ml import SimpleMLFilter
from .monitor import Monitor
from .risk import RiskManager
from .strategy import BreakoutStrategy, CompositeStrategy, MeanReversionStrategy, TrendFollowingStrategy
from .system import TradingSystem


def generate_sample_data(path: Path, rows: int = 300) -> None:
    random.seed(7)
    ts = datetime(2026, 1, 2, 9, 15, tzinfo=timezone.utc)
    price = 2500.0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        for _ in range(rows):
            drift = random.uniform(-2.0, 2.5)
            o = price
            c = max(1.0, price + drift)
            h = max(o, c) + random.uniform(0, 1.5)
            l = min(o, c) - random.uniform(0, 1.5)
            v = random.randint(1000, 10000)
            writer.writerow(
                {
                    "timestamp": ts.isoformat(),
                    "open": f"{o:.2f}",
                    "high": f"{h:.2f}",
                    "low": f"{l:.2f}",
                    "close": f"{c:.2f}",
                    "volume": str(v),
                }
            )
            ts += timedelta(minutes=5)
            price = c


def build_system() -> TradingSystem:
    config = default_config()
    strategy = CompositeStrategy(
        strategies=[
            TrendFollowingStrategy(),
            MeanReversionStrategy(),
            BreakoutStrategy(),
        ]
    )
    broker = PaperBroker(config.initial_capital, fee_bps=config.execution.fee_bps)
    risk = RiskManager(config)
    monitor = Monitor()
    ml_filter = SimpleMLFilter()
    return TradingSystem(config, strategy, broker, risk, monitor, ml_filter)


def main() -> None:
    parser = argparse.ArgumentParser(description="Automatic intraday trading system demo")
    parser.add_argument("--csv", type=str, default="", help="Path to OHLCV CSV file")
    parser.add_argument("--generate-sample", type=str, default="", help="Generate sample data to path")
    args = parser.parse_args()

    if args.generate_sample:
        target = Path(args.generate_sample)
        generate_sample_data(target)
        print(f"Sample dataset written to: {target}")
        return

    if not args.csv:
        raise SystemExit("Provide --csv <path> or --generate-sample <path>")

    provider = CSVDataProvider(args.csv)
    config = default_config()
    pipeline = DataPipeline(config.market.timeframe_minutes)
    candles = pipeline.run(provider.historical())
    gaps = pipeline.detect_gaps(candles)

    system = build_system()
    result = system.run(candles)

    wf = walk_forward_validate(build_system, candles, folds=3)

    print("=== Trading Run Summary ===")
    print(f"Final equity: {result.final_equity:.2f}")
    print(f"Realized PnL: {result.realized_pnl:.2f}")
    print(f"Trade count: {result.trade_count}")
    print(f"Halted: {result.halted}")
    if result.halt_reason:
        print(f"Halt reason: {result.halt_reason}")
    print(f"Detected gaps: {len(gaps)}")
    print("=== Walk-forward Validation ===")
    print(f"Folds: {wf.folds}")
    print(f"Average final equity: {wf.avg_final_equity:.2f}")
    print(f"Average realized PnL: {wf.avg_realized_pnl:.2f}")


if __name__ == "__main__":
    main()
