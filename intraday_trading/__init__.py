"""Intraday trading system package."""

from .config import SystemConfig, default_config
from .data import Candle, CSVDataProvider, DataPipeline
from .strategy import CompositeStrategy, TrendFollowingStrategy, MeanReversionStrategy, BreakoutStrategy, Signal
from .ml import SimpleMLFilter
from .risk import RiskManager
from .execution import PaperBroker
from .system import TradingSystem

__all__ = [
    "SystemConfig",
    "default_config",
    "Candle",
    "CSVDataProvider",
    "DataPipeline",
    "CompositeStrategy",
    "TrendFollowingStrategy",
    "MeanReversionStrategy",
    "BreakoutStrategy",
    "Signal",
    "SimpleMLFilter",
    "RiskManager",
    "PaperBroker",
    "TradingSystem",
]
