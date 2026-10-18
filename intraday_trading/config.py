import os
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


def _env_str(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def default_config() -> SystemConfig:
    return SystemConfig(
        market=MarketScope(
            exchange=_env_str("IT_EXCHANGE", "NSE"),
            symbol=_env_str("IT_SYMBOL", "RELIANCE"),
            instrument_type=_env_str("IT_INSTRUMENT_TYPE", "EQUITY"),
            timeframe_minutes=_env_int("IT_TIMEFRAME_MINUTES", 5),
        ),
        risk=RiskConstraints(
            max_daily_loss_pct=_env_float("IT_MAX_DAILY_LOSS_PCT", 0.02),
            max_drawdown_pct=_env_float("IT_MAX_DRAWDOWN_PCT", 0.1),
            per_trade_risk_pct=_env_float("IT_PER_TRADE_RISK_PCT", 0.005),
            max_position_size=_env_int("IT_MAX_POSITION_SIZE", 200),
            max_leverage=_env_float("IT_MAX_LEVERAGE", 1.0),
            max_trades_per_day=_env_int("IT_MAX_TRADES_PER_DAY", 30),
            max_consecutive_losses=_env_int("IT_MAX_CONSECUTIVE_LOSSES", 4),
        ),
        hours=TradingHours(start=time(9, 15), end=time(15, 30)),
        execution=ExecutionConstraints(
            max_slippage_bps=10.0,
            max_spread_bps=15.0,
            fee_bps=2.0,
        ),
        strategy=StrategyConstraints(
            stop_loss_pct=_env_float("IT_STOP_LOSS_PCT", 0.006),
            take_profit_pct=_env_float("IT_TAKE_PROFIT_PCT", 0.012),
            no_trade_volatility_pct=_env_float("IT_NO_TRADE_VOLATILITY_PCT", 0.025),
        ),
        initial_capital=_env_float("IT_INITIAL_CAPITAL", 1_000_000.0),
    )
