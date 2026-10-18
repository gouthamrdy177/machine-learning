import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from intraday_trading.config import default_config
from intraday_trading.main import generate_sample_data


class ConfigAndMainTests(unittest.TestCase):
    def test_default_config_uses_existing_defaults_without_env(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = default_config()
        self.assertEqual(cfg.market.exchange, "NSE")
        self.assertEqual(cfg.market.symbol, "RELIANCE")
        self.assertEqual(cfg.market.timeframe_minutes, 5)
        self.assertEqual(cfg.initial_capital, 1_000_000.0)
        self.assertEqual(cfg.risk.max_daily_loss_pct, 0.02)

    def test_default_config_applies_environment_overrides(self):
        with patch.dict(
            os.environ,
            {
                "IT_EXCHANGE": "NASDAQ",
                "IT_SYMBOL": "AAPL",
                "IT_TIMEFRAME_MINUTES": "15",
                "IT_INITIAL_CAPITAL": "250000",
                "IT_MAX_DAILY_LOSS_PCT": "0.03",
                "IT_MAX_DRAWDOWN_PCT": "0.2",
            },
            clear=True,
        ):
            cfg = default_config()
        self.assertEqual(cfg.market.exchange, "NASDAQ")
        self.assertEqual(cfg.market.symbol, "AAPL")
        self.assertEqual(cfg.market.timeframe_minutes, 15)
        self.assertEqual(cfg.initial_capital, 250000.0)
        self.assertEqual(cfg.risk.max_daily_loss_pct, 0.03)
        self.assertEqual(cfg.risk.max_drawdown_pct, 0.2)

    def test_default_config_falls_back_when_env_invalid(self):
        with patch.dict(
            os.environ,
            {
                "IT_TIMEFRAME_MINUTES": "invalid",
                "IT_INITIAL_CAPITAL": "not-a-number",
                "IT_MAX_DAILY_LOSS_PCT": "oops",
            },
            clear=True,
        ):
            cfg = default_config()
        self.assertEqual(cfg.market.timeframe_minutes, 5)
        self.assertEqual(cfg.initial_capital, 1_000_000.0)
        self.assertEqual(cfg.risk.max_daily_loss_pct, 0.02)

    def test_generate_sample_data_creates_parent_directories(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "nested" / "sample_ohlcv.csv"
            generate_sample_data(output, rows=5)
            self.assertTrue(output.exists())
            with output.open("r", encoding="utf-8") as handle:
                lines = handle.readlines()
            self.assertEqual(len(lines), 6)


if __name__ == "__main__":
    unittest.main()
