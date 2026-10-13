from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import mean, pstdev
from typing import List

from .data import Candle
from .strategy import Signal


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


@dataclass
class SimpleLogisticModel:
    learning_rate: float = 0.05
    epochs: int = 80
    weights: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    bias: float = 0.0

    def fit(self, X: List[List[float]], y: List[int]) -> None:
        if not X:
            return
        dim = len(X[0])
        if len(self.weights) != dim:
            self.weights = [0.0] * dim
        for _ in range(self.epochs):
            grad_w = [0.0] * dim
            grad_b = 0.0
            for xi, yi in zip(X, y):
                pred = self.predict_proba_features(xi)
                diff = pred - yi
                for j in range(dim):
                    grad_w[j] += diff * xi[j]
                grad_b += diff
            n = float(len(X))
            for j in range(dim):
                self.weights[j] -= self.learning_rate * (grad_w[j] / n)
            self.bias -= self.learning_rate * (grad_b / n)

    def predict_proba_features(self, features: List[float]) -> float:
        z = self.bias + sum(w * x for w, x in zip(self.weights, features))
        return _sigmoid(z)


@dataclass
class SimpleMLFilter:
    lookback: int = 30
    long_threshold: float = 0.55
    short_threshold: float = 0.45
    model: SimpleLogisticModel = field(default_factory=SimpleLogisticModel)

    def _features(self, candles: List[Candle]) -> List[float]:
        closes = [c.close for c in candles]
        vols = [c.volume for c in candles]
        r1 = (closes[-1] / closes[-2]) - 1.0
        r5 = (closes[-1] / closes[-6]) - 1.0 if len(closes) >= 6 else r1
        local = closes[-self.lookback:]
        volat = pstdev(local) / mean(local) if mean(local) != 0 else 0.0
        avg_v = mean(vols[-self.lookback:]) if vols else 1.0
        vz = (vols[-1] / avg_v) - 1.0 if avg_v else 0.0
        return [r1, r5, volat, vz]

    def train(self, candles: List[Candle], horizon: int = 3) -> None:
        if len(candles) < max(self.lookback + 2, horizon + 5):
            return
        X: List[List[float]] = []
        y: List[int] = []
        for i in range(self.lookback, len(candles) - horizon):
            window = candles[: i + 1]
            f = self._features(window)
            future_ret = (candles[i + horizon].close / candles[i].close) - 1.0
            X.append(f)
            y.append(1 if future_ret > 0 else 0)
        self.model.fit(X, y)

    def score(self, candles: List[Candle]) -> float:
        if len(candles) < max(self.lookback, 6):
            return 0.5
        return self.model.predict_proba_features(self._features(candles))

    def filter_signal(self, raw_signal: Signal, probability: float) -> Signal:
        if raw_signal == Signal.BUY and probability >= self.long_threshold:
            return Signal.BUY
        if raw_signal == Signal.SELL and probability <= self.short_threshold:
            return Signal.SELL
        return Signal.HOLD
