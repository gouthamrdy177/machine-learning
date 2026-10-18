from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Dict, List

from .backtest import WalkForwardResult, walk_forward_validate
from .config import SystemConfig, default_config
from .data import Candle, DataPipeline
from .execution import PaperBroker
from .ml import SimpleMLFilter
from .monitor import Monitor
from .risk import RiskManager
from .strategy import BreakoutStrategy, CompositeStrategy, MeanReversionStrategy, Signal, Strategy, TrendFollowingStrategy
from .system import ExecutedTrade, RunDetails, TradingSystem


@dataclass
class ValidationSummary:
    result: WalkForwardResult | None
    error: str | None = None


@dataclass
class DashboardMetrics:
    run: RunDetails
    gaps: List[tuple[str, str]]
    win_rate: float | None
    validation: ValidationSummary


@dataclass
class SignalRecommendation:
    decision: str
    estimated_risk_pct: float
    stop_loss_price: float | None
    take_profit_price: float | None
    suggested_quantity: int
    explanation: str


@dataclass
class CandidateScore:
    symbol: str
    score: float | None
    status: str
    explanation: str
    decision: str
    pnl: float | None
    max_drawdown_pct: float | None


def default_strategy() -> Strategy:
    return CompositeStrategy(
        strategies=[
            TrendFollowingStrategy(),
            MeanReversionStrategy(),
            BreakoutStrategy(),
        ]
    )


def build_system(config: SystemConfig) -> TradingSystem:
    return TradingSystem(
        config=config,
        strategy=default_strategy(),
        broker=PaperBroker(config.initial_capital, fee_bps=config.execution.fee_bps),
        risk=RiskManager(config),
        monitor=Monitor(),
        ml_filter=SimpleMLFilter(),
    )


def run_dashboard_metrics(candles: List[Candle], config: SystemConfig, folds: int = 3) -> DashboardMetrics:
    pipeline = DataPipeline(config.market.timeframe_minutes)
    prepared = pipeline.run(candles)
    gaps = [(a.isoformat(), b.isoformat()) for a, b in pipeline.detect_gaps(prepared)]
    run = build_system(config).run_detailed(prepared)
    exits = [t.realized_pnl for t in run.trades if t.realized_pnl is not None]
    wins = [p for p in exits if p > 0]
    win_rate = (len(wins) / len(exits)) if exits else None
    try:
        wf = walk_forward_validate(lambda: build_system(config), prepared, folds=folds)
        validation = ValidationSummary(result=wf)
    except ValueError as exc:
        validation = ValidationSummary(result=None, error=str(exc))
    return DashboardMetrics(run=run, gaps=gaps, win_rate=win_rate, validation=validation)


def _spread_bps(candle: Candle) -> float:
    if candle.close <= 0:
        return 0.0
    return ((candle.high - candle.low) / candle.close) * 10_000.0


def recommend_latest_signal(
    candles: List[Candle],
    config: SystemConfig | None = None,
    strategy: Strategy | None = None,
) -> SignalRecommendation:
    if not candles:
        return SignalRecommendation(
            decision="NO_TRADE",
            estimated_risk_pct=0.0,
            stop_loss_price=None,
            take_profit_price=None,
            suggested_quantity=0,
            explanation="No candles provided. Upload a CSV with OHLCV history.",
        )

    cfg = config or default_config()
    strat = strategy or default_strategy()
    signal = strat.signal(candles)
    latest = candles[-1]

    equity = cfg.initial_capital
    risk = RiskManager(cfg)
    risk.on_tick(latest.timestamp, equity)
    spread = _spread_bps(latest)
    slippage = min(spread / 4.0, cfg.execution.max_slippage_bps)
    can_trade, reason = risk.can_trade(latest.timestamp, spread, slippage)

    qty = risk.position_size(equity=equity, price=latest.close, stop_loss_pct=cfg.strategy.stop_loss_pct)
    estimated_risk_pct = 0.0
    if equity > 0 and qty > 0:
        estimated_risk_pct = ((latest.close * qty * cfg.strategy.stop_loss_pct) / equity) * 100.0

    if signal == Signal.HOLD:
        return SignalRecommendation(
            decision="HOLD",
            estimated_risk_pct=estimated_risk_pct,
            stop_loss_price=None,
            take_profit_price=None,
            suggested_quantity=0,
            explanation="Strategy signal is HOLD, so no entry is suggested on the latest candle.",
        )

    if not can_trade:
        return SignalRecommendation(
            decision="NO_TRADE",
            estimated_risk_pct=estimated_risk_pct,
            stop_loss_price=None,
            take_profit_price=None,
            suggested_quantity=0,
            explanation=f"Signal was {signal.value}, but risk checks blocked trading: {reason}.",
        )

    if qty <= 0:
        return SignalRecommendation(
            decision="NO_TRADE",
            estimated_risk_pct=0.0,
            stop_loss_price=None,
            take_profit_price=None,
            suggested_quantity=0,
            explanation="Risk and position limits produced zero quantity. Increase capital or limits to simulate entries.",
        )

    if signal == Signal.BUY:
        stop_loss = latest.close * (1.0 - cfg.strategy.stop_loss_pct)
        take_profit = latest.close * (1.0 + cfg.strategy.take_profit_pct)
    else:
        stop_loss = latest.close * (1.0 + cfg.strategy.stop_loss_pct)
        take_profit = latest.close * (1.0 - cfg.strategy.take_profit_pct)

    return SignalRecommendation(
        decision=signal.value,
        estimated_risk_pct=estimated_risk_pct,
        stop_loss_price=stop_loss,
        take_profit_price=take_profit,
        suggested_quantity=qty,
        explanation=(
            f"Signal={signal.value}; risk checks passed (spread={spread:.2f}bps, slippage={slippage:.2f}bps). "
            f"Position size capped by per-trade risk and limits."
        ),
    )


def rank_symbol_candidates(symbol_candles: Dict[str, List[Candle]], config: SystemConfig) -> List[CandidateScore]:
    ranked: List[CandidateScore] = []
    for symbol, candles in symbol_candles.items():
        if not candles:
            ranked.append(
                CandidateScore(
                    symbol=symbol,
                    score=None,
                    status="insufficient_data",
                    explanation="No CSV data provided for this symbol.",
                    decision="NO_TRADE",
                    pnl=None,
                    max_drawdown_pct=None,
                )
            )
            continue
        try:
            metrics = run_dashboard_metrics(candles, config)
        except ValueError as exc:
            ranked.append(
                CandidateScore(
                    symbol=symbol,
                    score=None,
                    status="insufficient_data",
                    explanation=str(exc),
                    decision="NO_TRADE",
                    pnl=None,
                    max_drawdown_pct=None,
                )
            )
            continue
        recommendation = recommend_latest_signal(candles, config=config)
        max_drawdown = max((dd for _, dd in metrics.run.drawdown_curve), default=0.0)
        signal_bonus = {"BUY": 2.0, "HOLD": 0.5, "SELL": -1.0, "NO_TRADE": -1.5}.get(recommendation.decision, 0.0)
        pnl_pct = (metrics.run.result.realized_pnl / config.initial_capital) * 100.0 if config.initial_capital else 0.0
        score = signal_bonus + pnl_pct - (max_drawdown * 10.0)
        ranked.append(
            CandidateScore(
                symbol=symbol,
                score=score,
                status="ok",
                explanation=(
                    "Transparent score = signal bonus + backtest PnL% - drawdown penalty. "
                    "Uses only uploaded historical/replay CSV data."
                ),
                decision=recommendation.decision,
                pnl=metrics.run.result.realized_pnl,
                max_drawdown_pct=max_drawdown * 100.0,
            )
        )
    ranked.sort(key=lambda item: (item.score is None, -(item.score or -10_000.0), item.symbol))
    return ranked


def parse_symbol_list(raw_value: str) -> List[str]:
    values = [part.strip().upper() for part in raw_value.split(",")]
    return [v for v in values if v]


def average_equity(equity_curve: List[tuple[str, float]]) -> float | None:
    if not equity_curve:
        return None
    return mean(value for _, value in equity_curve)

