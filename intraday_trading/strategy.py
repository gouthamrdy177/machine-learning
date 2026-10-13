from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from statistics import mean, pstdev
from typing import List

from .data import Candle


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Strategy:
    def signal(self, candles: List[Candle]) -> Signal:
        raise NotImplementedError


@dataclass
class TrendFollowingStrategy(Strategy):
    short_window: int = 8
    long_window: int = 21

    def signal(self, candles: List[Candle]) -> Signal:
        if len(candles) < self.long_window:
            return Signal.HOLD
        closes = [c.close for c in candles]
        short_avg = mean(closes[-self.short_window:])
        long_avg = mean(closes[-self.long_window:])
        if short_avg > long_avg:
            return Signal.BUY
        if short_avg < long_avg:
            return Signal.SELL
        return Signal.HOLD


@dataclass
class MeanReversionStrategy(Strategy):
    lookback: int = 20
    z_threshold: float = 1.2

    def signal(self, candles: List[Candle]) -> Signal:
        if len(candles) < self.lookback:
            return Signal.HOLD
        closes = [c.close for c in candles[-self.lookback:]]
        mu = mean(closes)
        sigma = pstdev(closes)
        if sigma == 0:
            return Signal.HOLD
        z = (closes[-1] - mu) / sigma
        if z <= -self.z_threshold:
            return Signal.BUY
        if z >= self.z_threshold:
            return Signal.SELL
        return Signal.HOLD


@dataclass
class BreakoutStrategy(Strategy):
    lookback: int = 20

    def signal(self, candles: List[Candle]) -> Signal:
        if len(candles) <= self.lookback:
            return Signal.HOLD
        window = candles[-(self.lookback + 1):-1]
        last = candles[-1]
        highest = max(c.high for c in window)
        lowest = min(c.low for c in window)
        if last.close > highest:
            return Signal.BUY
        if last.close < lowest:
            return Signal.SELL
        return Signal.HOLD


@dataclass
class CompositeStrategy(Strategy):
    strategies: List[Strategy]

    def signal(self, candles: List[Candle]) -> Signal:
        votes = [s.signal(candles) for s in self.strategies]
        buys = votes.count(Signal.BUY)
        sells = votes.count(Signal.SELL)
        if buys > sells and buys >= 2:
            return Signal.BUY
        if sells > buys and sells >= 2:
            return Signal.SELL
        return Signal.HOLD
