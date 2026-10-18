from __future__ import annotations

from dataclasses import dataclass
from statistics import pstdev, mean
from typing import List

from .config import SystemConfig
from .data import Candle
from .execution import PaperBroker, Side
from .ml import SimpleMLFilter
from .monitor import Monitor
from .risk import RiskManager
from .strategy import Signal, Strategy


@dataclass
class RunResult:
    final_equity: float
    realized_pnl: float
    trade_count: int
    halted: bool
    halt_reason: str | None


@dataclass
class ExecutedTrade:
    timestamp: str
    side: str
    price: float
    quantity: int
    stop_loss: float | None
    take_profit: float | None
    realized_pnl: float | None
    reason: str | None


@dataclass
class RunDetails:
    result: RunResult
    equity_curve: List[tuple[str, float]]
    drawdown_curve: List[tuple[str, float]]
    trades: List[ExecutedTrade]


class TradingSystem:
    def __init__(
        self,
        config: SystemConfig,
        strategy: Strategy,
        broker: PaperBroker,
        risk: RiskManager,
        monitor: Monitor,
        ml_filter: SimpleMLFilter | None = None,
    ):
        self.config = config
        self.strategy = strategy
        self.broker = broker
        self.risk = risk
        self.monitor = monitor
        self.ml_filter = ml_filter
        self.entry_price: float | None = None

    @staticmethod
    def _spread_bps(candle: Candle) -> float:
        if candle.close <= 0:
            return 0.0
        return ((candle.high - candle.low) / candle.close) * 10_000.0

    @staticmethod
    def _volatility_pct(candles: List[Candle], lookback: int = 20) -> float:
        if len(candles) < lookback + 1:
            return 0.0
        closes = [c.close for c in candles[-lookback:]]
        mu = mean(closes)
        if mu == 0:
            return 0.0
        return pstdev(closes) / mu

    def run(self, candles: List[Candle]) -> RunResult:
        return self.run_detailed(candles).result

    def run_detailed(self, candles: List[Candle]) -> RunDetails:
        if self.ml_filter:
            self.ml_filter.train(candles)
        history: List[Candle] = []
        equity_curve: List[tuple[str, float]] = []
        drawdown_curve: List[tuple[str, float]] = []
        trades: List[ExecutedTrade] = []
        peak_equity = self.broker.mark_to_market(candles[0].close) if candles else 0.0

        for candle in candles:
            history.append(candle)
            equity = self.broker.mark_to_market(candle.close)
            self.risk.on_tick(candle.timestamp, equity)
            peak_equity = max(peak_equity, equity)
            drawdown = ((peak_equity - equity) / peak_equity) if peak_equity > 0 else 0.0
            equity_curve.append((candle.timestamp.isoformat(), equity))
            drawdown_curve.append((candle.timestamp.isoformat(), drawdown))

            if self.monitor.killed:
                break

            spread = self._spread_bps(candle)
            slippage = min(spread / 4.0, self.config.execution.max_slippage_bps)

            if self._volatility_pct(history) > self.config.strategy.no_trade_volatility_pct:
                self.monitor.emit("NO_TRADE", "Volatility guard active", {"volatility": self._volatility_pct(history)})
                continue

            raw_signal = self.strategy.signal(history)
            signal = raw_signal
            if self.ml_filter:
                prob = self.ml_filter.score(history)
                signal = self.ml_filter.filter_signal(raw_signal, prob)
                self.monitor.emit("ML", "Signal filtered", {"probability": prob})

            # Stop loss / take profit checks
            if self.broker.position_qty > 0 and self.entry_price:
                ret = (candle.close / self.entry_price) - 1.0
                if ret <= -self.config.strategy.stop_loss_pct or ret >= self.config.strategy.take_profit_pct:
                    pnl = self.broker.close_position(candle, slippage)
                    self.risk.record_trade(pnl)
                    reason = "Stop loss hit" if ret <= -self.config.strategy.stop_loss_pct else "Take profit hit"
                    trades.append(
                        ExecutedTrade(
                            timestamp=candle.timestamp.isoformat(),
                            side=Side.SELL.value,
                            price=candle.close,
                            quantity=abs(self.broker.fills[-1].quantity),
                            stop_loss=self.entry_price * (1.0 - self.config.strategy.stop_loss_pct),
                            take_profit=self.entry_price * (1.0 + self.config.strategy.take_profit_pct),
                            realized_pnl=pnl,
                            reason=reason,
                        )
                    )
                    self.monitor.emit("EXIT", "Risk exit", {"pnl": pnl})
                    self.entry_price = None
                    continue

            allowed, reason = self.risk.can_trade(candle.timestamp, spread, slippage)
            if not allowed:
                if reason in {
                    "Max drawdown exceeded",
                    "Daily loss limit reached",
                    "Consecutive loss breaker",
                }:
                    self.monitor.kill_switch(reason)
                else:
                    self.monitor.emit("BLOCKED", reason or "Blocked")
                continue

            price = candle.close
            if signal == Signal.BUY and self.broker.position_qty <= 0:
                if self.broker.position_qty < 0:
                    pnl = self.broker.close_position(candle, slippage)
                    self.risk.record_trade(pnl)
                qty = self.risk.position_size(
                    equity=self.broker.mark_to_market(price),
                    price=price,
                    stop_loss_pct=self.config.strategy.stop_loss_pct,
                )
                if qty > 0:
                    self.broker.execute_market(Side.BUY, qty, candle, slippage)
                    self.entry_price = price
                    trades.append(
                        ExecutedTrade(
                            timestamp=candle.timestamp.isoformat(),
                            side=Side.BUY.value,
                            price=candle.close,
                            quantity=qty,
                            stop_loss=price * (1.0 - self.config.strategy.stop_loss_pct),
                            take_profit=price * (1.0 + self.config.strategy.take_profit_pct),
                            realized_pnl=None,
                            reason="Strategy entry",
                        )
                    )
                    self.monitor.emit("ENTRY", "Opened long", {"qty": float(qty), "price": price})
            elif signal == Signal.SELL and self.broker.position_qty >= 0:
                if self.broker.position_qty > 0:
                    qty = abs(self.broker.position_qty)
                    pnl = self.broker.close_position(candle, slippage)
                    self.risk.record_trade(pnl)
                    trades.append(
                        ExecutedTrade(
                            timestamp=candle.timestamp.isoformat(),
                            side=Side.SELL.value,
                            price=candle.close,
                            quantity=qty,
                            stop_loss=self.entry_price * (1.0 - self.config.strategy.stop_loss_pct) if self.entry_price else None,
                            take_profit=self.entry_price * (1.0 + self.config.strategy.take_profit_pct) if self.entry_price else None,
                            realized_pnl=pnl,
                            reason="Strategy exit",
                        )
                    )
                    self.monitor.emit("EXIT", "Closed long", {"pnl": pnl})
                    self.entry_price = None

        final_equity = self.broker.mark_to_market(candles[-1].close)
        result = RunResult(
            final_equity=final_equity,
            realized_pnl=self.broker.realized_pnl,
            trade_count=self.risk.state.trade_count,
            halted=self.monitor.killed,
            halt_reason=self.risk.state.halt_reason if self.monitor.killed else None,
        )
        return RunDetails(
            result=result,
            equity_curve=equity_curve,
            drawdown_curve=drawdown_curve,
            trades=trades,
        )
