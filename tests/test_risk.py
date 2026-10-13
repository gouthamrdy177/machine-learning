from datetime import datetime, timezone
import unittest

from intraday_trading.config import default_config
from intraday_trading.risk import RiskManager


class RiskManagerTests(unittest.TestCase):
    def test_position_size_respects_max_position(self):
        cfg = default_config()
        rm = RiskManager(cfg)
        qty = rm.position_size(equity=cfg.initial_capital, price=100.0, stop_loss_pct=0.005)
        self.assertLessEqual(qty, cfg.risk.max_position_size)

    def test_daily_loss_breaker(self):
        cfg = default_config()
        rm = RiskManager(cfg)
        now = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
        rm.on_tick(now, cfg.initial_capital)
        rm.record_trade(-(cfg.initial_capital * cfg.risk.max_daily_loss_pct))
        allowed, reason = rm.can_trade(now, spread_bps=1.0, slippage_bps=1.0)
        self.assertFalse(allowed)
        self.assertEqual(reason, "Daily loss limit reached")


if __name__ == "__main__":
    unittest.main()
