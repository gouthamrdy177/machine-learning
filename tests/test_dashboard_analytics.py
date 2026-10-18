from datetime import datetime, timedelta, timezone
import unittest

from intraday_trading.analytics import parse_symbol_list, recommend_latest_signal, run_dashboard_metrics
from intraday_trading.config import default_config
from intraday_trading.data import Candle
from intraday_trading.strategy import Signal, Strategy


class FixedStrategy(Strategy):
    def __init__(self, signal: Signal):
        self._signal = signal

    def signal(self, candles):  # noqa: D401
        return self._signal


def _candles(count: int = 50, start_price: float = 100.0, hour: int = 10):
    start = datetime(2026, 1, 2, hour, 0, tzinfo=timezone.utc)
    items = []
    price = start_price
    for i in range(count):
        close = price
        items.append(Candle(start + timedelta(minutes=i * 5), close, close + 0.02, close - 0.02, close, 1000))
        price += 0.3
    return items


class DashboardAnalyticsTests(unittest.TestCase):
    def test_recommendation_calculates_risk_and_quantity_for_buy(self):
        cfg = default_config()
        candles = _candles()
        rec = recommend_latest_signal(candles, config=cfg, strategy=FixedStrategy(Signal.BUY))
        self.assertEqual(rec.decision, "BUY")
        self.assertGreater(rec.suggested_quantity, 0)
        self.assertGreater(rec.estimated_risk_pct, 0.0)
        self.assertIsNotNone(rec.stop_loss_price)
        self.assertIsNotNone(rec.take_profit_price)

    def test_recommendation_returns_hold(self):
        cfg = default_config()
        rec = recommend_latest_signal(_candles(), config=cfg, strategy=FixedStrategy(Signal.HOLD))
        self.assertEqual(rec.decision, "HOLD")
        self.assertEqual(rec.suggested_quantity, 0)

    def test_recommendation_blocks_trade_outside_hours(self):
        cfg = default_config()
        candles = _candles(hour=5, count=40)
        rec = recommend_latest_signal(candles, config=cfg, strategy=FixedStrategy(Signal.BUY))
        self.assertEqual(rec.decision, "NO_TRADE")
        self.assertIn("risk checks blocked", rec.explanation)

    def test_dashboard_metrics_returns_validation_error_for_short_history(self):
        cfg = default_config()
        metrics = run_dashboard_metrics(_candles(count=40), cfg)
        self.assertIsNone(metrics.validation.result)
        self.assertIsNotNone(metrics.validation.error)

    def test_parse_symbol_list(self):
        self.assertEqual(parse_symbol_list(" RELIANCE, tcs , ,INFY "), ["RELIANCE", "TCS", "INFY"])


if __name__ == "__main__":
    unittest.main()
