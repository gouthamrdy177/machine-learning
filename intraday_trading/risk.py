from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
import math

from .config import SystemConfig


@dataclass
class RiskState:
    day: datetime.date | None = None
    day_start_equity: float = 0.0
    daily_pnl: float = 0.0
    trade_count: int = 0
    consecutive_losses: int = 0
    peak_equity: float = 0.0
    halt_reason: str | None = None


class RiskManager:
    def __init__(self, config: SystemConfig):
        self.config = config
        self.state = RiskState(
            day_start_equity=config.initial_capital,
            peak_equity=config.initial_capital,
        )

    def on_tick(self, now: datetime, equity: float) -> None:
        if self.state.day != now.date():
            self.state.day = now.date()
            self.state.day_start_equity = equity
            self.state.daily_pnl = 0.0
            self.state.trade_count = 0
            self.state.consecutive_losses = 0
            self.state.halt_reason = None
        self.state.peak_equity = max(self.state.peak_equity, equity)
        self._check_drawdown(equity)

    def _check_drawdown(self, equity: float) -> None:
        if self.state.peak_equity <= 0:
            return
        dd = (self.state.peak_equity - equity) / self.state.peak_equity
        if dd >= self.config.risk.max_drawdown_pct:
            self.state.halt_reason = "Max drawdown exceeded"

    def trading_open(self, t: time) -> bool:
        return self.config.hours.start <= t <= self.config.hours.end

    def position_size(self, equity: float, price: float, stop_loss_pct: float) -> int:
        risk_cash = equity * self.config.risk.per_trade_risk_pct
        risk_per_unit = max(price * stop_loss_pct, 1e-8)
        by_risk = int(math.floor(risk_cash / risk_per_unit))
        by_notional = int(math.floor((equity * self.config.risk.max_leverage) / max(price, 1e-8)))
        qty = max(0, min(by_risk, by_notional, self.config.risk.max_position_size))
        return qty

    def can_trade(self, now: datetime, spread_bps: float, slippage_bps: float) -> tuple[bool, str | None]:
        if self.state.halt_reason:
            return False, self.state.halt_reason
        if not self.trading_open(now.time()):
            return False, "Outside trading hours"
        if self.state.trade_count >= self.config.risk.max_trades_per_day:
            return False, "Max trades per day reached"
        if spread_bps > self.config.execution.max_spread_bps:
            return False, "Spread too wide"
        if slippage_bps > self.config.execution.max_slippage_bps:
            return False, "Slippage too high"
        if self.state.consecutive_losses >= self.config.risk.max_consecutive_losses:
            return False, "Consecutive loss breaker"
        if self.state.day_start_equity > 0:
            loss = -self.state.daily_pnl / self.state.day_start_equity
            if loss >= self.config.risk.max_daily_loss_pct:
                return False, "Daily loss limit reached"
        return True, None

    def record_trade(self, pnl: float) -> None:
        self.state.trade_count += 1
        self.state.daily_pnl += pnl
        if pnl < 0:
            self.state.consecutive_losses += 1
        else:
            self.state.consecutive_losses = 0
