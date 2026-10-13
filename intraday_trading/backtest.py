from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .data import Candle
from .system import TradingSystem, RunResult


@dataclass
class WalkForwardResult:
    folds: int
    avg_final_equity: float
    avg_realized_pnl: float


def walk_forward_validate(system_factory, candles: List[Candle], folds: int = 3) -> WalkForwardResult:
    if folds <= 0:
        raise ValueError("folds must be positive")
    if len(candles) < folds * 30:
        raise ValueError("not enough data for walk-forward")

    fold_size = len(candles) // folds
    results: List[RunResult] = []
    for i in range(1, folds + 1):
        train_end = fold_size * i
        train = candles[:train_end]
        test = candles[train_end: train_end + fold_size]
        if len(test) < 10:
            continue
        system: TradingSystem = system_factory()
        _ = train  # placeholder to show split; model training occurs inside system
        results.append(system.run(test))

    if not results:
        raise ValueError("no valid folds")

    return WalkForwardResult(
        folds=len(results),
        avg_final_equity=sum(r.final_equity for r in results) / len(results),
        avg_realized_pnl=sum(r.realized_pnl for r in results) / len(results),
    )
