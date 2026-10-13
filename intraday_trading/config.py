from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True)
class MarketScope:
    exchange: str
    symbol: str
    instrument_type: str
    timeframe_minutes: int


@dataclass(frozen=True)
class RiskConstraints:
    max_daily_loss_pct: float
    max_drawdown_pct: float
    per_trade_risk_pct: float
    max_position_size: int
    max_leverage: float
    max_trades_per_day: int
    max_consecutive_losses: int


@dataclass(frozen=True)
class TradingHours:
    start: time
    end: time


@dataclass(frozen=True)
class ExecutionConstraints:
    max_slippage_bps: float
    max_spread_bps: float
    fee_bps: float


@dataclass(frozen=True)
class StrategyConstraints:
    stop_loss_pct: float
    take_profit_pct: float
    no_trade_volatility_pct: float


@dataclass(frozen=True)
class SystemConfig:
    market: MarketScope
    risk: RiskConstraints
    hours: TradingHours
    execution: ExecutionConstraints
    strategy: StrategyConstraints
    initial_capital: float


def default_config() -> SystemConfig:
    return SystemConfig(
        market=MarketScope(
            exchange="NSE",
            symbol="RELIANCE",
            instrument_type="EQUITY",
            timeframe_minutes=5,
        ),
        risk=RiskConstraints(
            max_daily_loss_pct=0.02,
            max_drawdown_pct=0.1,
            per_trade_risk_pct=0.005,
            max_position_size=200,
            max_leverage=1.0,
            max_trades_per_day=30,
            max_consecutive_losses=4,
        ),
        hours=TradingHours(start=time(9, 15), end=time(15, 30)),
        execution=ExecutionConstraints(
            max_slippage_bps=10.0,
            max_spread_bps=15.0,
            fee_bps=2.0,
        ),
        strategy=StrategyConstraints(
            stop_loss_pct=0.006,
            take_profit_pct=0.012,
            no_trade_volatility_pct=0.025,
        ),
        initial_capital=1_000_000.0,
    )
