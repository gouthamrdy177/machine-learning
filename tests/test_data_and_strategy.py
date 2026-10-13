from datetime import datetime, timedelta, timezone
import unittest

from intraday_trading.data import Candle, DataPipeline
from intraday_trading.strategy import Signal, TrendFollowingStrategy


class DataAndStrategyTests(unittest.TestCase):
    def test_gap_detection(self):
        start = datetime(2026, 1, 2, 9, 15, tzinfo=timezone.utc)
        candles = [
            Candle(start, 100, 101, 99, 100.5, 1000),
            Candle(start + timedelta(minutes=5), 100.5, 102, 100, 101.5, 1100),
            Candle(start + timedelta(minutes=20), 101.5, 103, 101, 102, 1050),
        ]
        pipeline = DataPipeline(timeframe_minutes=5)
        gaps = pipeline.detect_gaps(candles)
        self.assertEqual(len(gaps), 1)

    def test_trend_signal_buy(self):
        start = datetime(2026, 1, 2, 9, 15, tzinfo=timezone.utc)
        candles = []
        price = 100.0
        for i in range(30):
            candles.append(Candle(start + timedelta(minutes=i * 5), price, price + 1, price - 1, price, 1000))
            price += 0.5
        signal = TrendFollowingStrategy().signal(candles)
        self.assertEqual(signal, Signal.BUY)


if __name__ == "__main__":
    unittest.main()
