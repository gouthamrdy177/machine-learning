from __future__ import annotations

import tempfile
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .analytics import parse_symbol_list, rank_symbol_candidates, recommend_latest_signal, run_dashboard_metrics
from .config import (
    MarketScope,
    RiskConstraints,
    StrategyConstraints,
    SystemConfig,
    default_config,
)
from .data import CSVDataProvider
from .main import generate_sample_data


def _load_candles_from_upload(upload) -> List:
    with tempfile.NamedTemporaryFile("wb", suffix=".csv", delete=False) as handle:
        handle.write(upload.getvalue())
        tmp_path = Path(handle.name)
    try:
        return CSVDataProvider(str(tmp_path)).historical()
    finally:
        tmp_path.unlink(missing_ok=True)


def _load_sample_candles() -> List:
    sample_path = Path(tempfile.gettempdir()) / "intraday_sample_ohlcv.csv"
    if not sample_path.exists():
        generate_sample_data(sample_path, rows=300)
    return CSVDataProvider(str(sample_path)).historical()


def _config_from_inputs(base: SystemConfig) -> SystemConfig:
    symbol = st.sidebar.text_input("Symbol", value=base.market.symbol).strip() or base.market.symbol
    timeframe = st.sidebar.number_input("Timeframe (minutes)", min_value=1, max_value=240, value=base.market.timeframe_minutes)
    initial_capital = st.sidebar.number_input("Initial capital", min_value=1000.0, value=float(base.initial_capital), step=1000.0)
    per_trade_risk = st.sidebar.number_input("Per-trade risk %", min_value=0.01, max_value=25.0, value=base.risk.per_trade_risk_pct * 100.0)
    max_daily_loss = st.sidebar.number_input("Max daily loss %", min_value=0.1, max_value=50.0, value=base.risk.max_daily_loss_pct * 100.0)
    max_drawdown = st.sidebar.number_input("Max drawdown %", min_value=0.1, max_value=80.0, value=base.risk.max_drawdown_pct * 100.0)
    stop_loss = st.sidebar.number_input("Stop loss %", min_value=0.01, max_value=20.0, value=base.strategy.stop_loss_pct * 100.0)
    take_profit = st.sidebar.number_input("Take profit %", min_value=0.01, max_value=50.0, value=base.strategy.take_profit_pct * 100.0)
    max_position_size = st.sidebar.number_input(
        "Max position size", min_value=1, max_value=1_000_000, value=base.risk.max_position_size, step=1
    )

    return replace(
        base,
        market=MarketScope(
            exchange=base.market.exchange,
            symbol=symbol.upper(),
            instrument_type=base.market.instrument_type,
            timeframe_minutes=int(timeframe),
        ),
        initial_capital=float(initial_capital),
        risk=RiskConstraints(
            max_daily_loss_pct=max_daily_loss / 100.0,
            max_drawdown_pct=max_drawdown / 100.0,
            per_trade_risk_pct=per_trade_risk / 100.0,
            max_position_size=int(max_position_size),
            max_leverage=base.risk.max_leverage,
            max_trades_per_day=base.risk.max_trades_per_day,
            max_consecutive_losses=base.risk.max_consecutive_losses,
        ),
        strategy=StrategyConstraints(
            stop_loss_pct=stop_loss / 100.0,
            take_profit_pct=take_profit / 100.0,
            no_trade_volatility_pct=base.strategy.no_trade_volatility_pct,
        ),
    )


def _price_chart(candles, trades):
    frame = pd.DataFrame(
        [{"timestamp": c.timestamp, "open": c.open, "high": c.high, "low": c.low, "close": c.close} for c in candles]
    )
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=frame["timestamp"],
                open=frame["open"],
                high=frame["high"],
                low=frame["low"],
                close=frame["close"],
                name="Price",
            )
        ]
    )
    buys = [t for t in trades if t.side == "BUY"]
    sells = [t for t in trades if t.side == "SELL"]
    if buys:
        fig.add_trace(
            go.Scatter(
                x=[datetime.fromisoformat(t.timestamp) for t in buys],
                y=[t.price for t in buys],
                mode="markers",
                marker=dict(color="green", size=8),
                name="BUY",
            )
        )
    if sells:
        fig.add_trace(
            go.Scatter(
                x=[datetime.fromisoformat(t.timestamp) for t in sells],
                y=[t.price for t in sells],
                mode="markers",
                marker=dict(color="red", size=8),
                name="SELL",
            )
        )
    return fig


def main() -> None:
    st.set_page_config(page_title="Paper Trading Dashboard", layout="wide")
    st.title("Paper-Trading Backtest Dashboard")
    st.warning(
        "Educational simulation only. Not financial advice. No guaranteed returns. "
        "This dashboard does not connect to any broker and does not place live orders."
    )

    base_config = default_config()
    cfg = _config_from_inputs(base_config)

    source = st.radio("Data source", options=["Upload CSV", "Use generated sample data"], horizontal=True)
    upload = st.file_uploader("Upload OHLCV CSV", type=["csv"]) if source == "Upload CSV" else None

    if source == "Use generated sample data":
        candles = _load_sample_candles()
    elif upload:
        try:
            candles = _load_candles_from_upload(upload)
        except (ValueError, FileNotFoundError) as exc:
            st.error(f"Unable to parse CSV: {exc}")
            return
    else:
        st.info("Upload a CSV with columns: timestamp, open, high, low, close, volume.")
        return

    try:
        metrics = run_dashboard_metrics(candles, cfg)
    except ValueError as exc:
        st.error(f"Unable to run analysis: {exc}")
        return

    rec = recommend_latest_signal(candles, config=cfg)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Final Equity", f"{metrics.run.result.final_equity:,.2f}")
    col2.metric("Realized PnL", f"{metrics.run.result.realized_pnl:,.2f}")
    col3.metric("Trades", str(metrics.run.result.trade_count))
    win_text = f"{metrics.win_rate * 100:.1f}%" if metrics.win_rate is not None else "N/A"
    col4.metric("Win Rate", win_text)

    st.subheader("Latest Transparent Signal (historical/replay data only)")
    st.write(
        {
            "Decision": rec.decision,
            "Estimated risk %": round(rec.estimated_risk_pct, 4),
            "Suggested quantity": rec.suggested_quantity,
            "Stop loss": rec.stop_loss_price,
            "Take profit": rec.take_profit_price,
            "Explanation": rec.explanation,
        }
    )

    left, right = st.columns(2)
    left.plotly_chart(_price_chart(candles, metrics.run.trades), use_container_width=True)

    equity_df = pd.DataFrame(metrics.run.equity_curve, columns=["timestamp", "equity"])
    drawdown_df = pd.DataFrame(metrics.run.drawdown_curve, columns=["timestamp", "drawdown"])
    right.line_chart(equity_df.set_index("timestamp"))
    right.line_chart(drawdown_df.set_index("timestamp"))

    st.subheader("Trade Table")
    trades_df = pd.DataFrame(
        [
            {
                "timestamp": t.timestamp,
                "side": t.side,
                "price": t.price,
                "quantity": t.quantity,
                "stop_loss": t.stop_loss,
                "take_profit": t.take_profit,
                "realized_pnl": t.realized_pnl,
                "reason": t.reason,
            }
            for t in metrics.run.trades
        ]
    )
    if trades_df.empty:
        st.info("No trades executed for this run.")
    else:
        st.dataframe(trades_df, use_container_width=True)

    st.subheader("Validation & Data Quality")
    st.write({"detected_data_gaps": len(metrics.gaps), "gaps": metrics.gaps[:10]})
    if metrics.validation.result:
        st.write(
            {
                "walk_forward_folds": metrics.validation.result.folds,
                "avg_final_equity": metrics.validation.result.avg_final_equity,
                "avg_realized_pnl": metrics.validation.result.avg_realized_pnl,
            }
        )
    else:
        st.info(f"Walk-forward validation unavailable: {metrics.validation.error}")

    st.subheader("Which stock should I buy? (from your uploaded historical CSV data only)")
    symbols_raw = st.text_input("Symbols (comma separated)", value=cfg.market.symbol)
    candidate_uploads = st.file_uploader("Upload candidate symbol CSVs", type=["csv"], accept_multiple_files=True)
    symbols = parse_symbol_list(symbols_raw)
    if st.button("Rank candidates"):
        mapping: Dict[str, List] = {}
        files_by_name = {Path(item.name).stem.upper(): item for item in candidate_uploads}
        for symbol in symbols:
            file_obj = files_by_name.get(symbol)
            if not file_obj:
                mapping[symbol] = []
                continue
            try:
                mapping[symbol] = _load_candles_from_upload(file_obj)
            except (ValueError, FileNotFoundError):
                mapping[symbol] = []
        ranked = rank_symbol_candidates(mapping, cfg)
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "symbol": item.symbol,
                        "status": item.status,
                        "score": item.score,
                        "decision": item.decision,
                        "realized_pnl": item.pnl,
                        "max_drawdown_pct": item.max_drawdown_pct,
                        "explanation": item.explanation,
                    }
                    for item in ranked
                ]
            ),
            use_container_width=True,
        )
        st.caption(
            "Timing suggestions are generated from supplied historical/replay candles only and can be wrong. "
            "Insufficient or missing CSV data is explicitly labeled."
        )


if __name__ == "__main__":
    main()
