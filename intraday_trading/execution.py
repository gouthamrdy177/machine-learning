from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

from .data import Candle


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Fill:
    timestamp: str
    side: Side
    quantity: int
    price: float
    fee: float
    slippage_bps: float


class PaperBroker:
    def __init__(self, initial_capital: float, fee_bps: float = 0.0):
        self.cash = initial_capital
        self.fee_bps = fee_bps
        self.position_qty = 0
        self.avg_entry = 0.0
        self.realized_pnl = 0.0
        self.fills: List[Fill] = []

    def _fee(self, notional: float) -> float:
        return notional * (self.fee_bps / 10_000.0)

    def mark_to_market(self, price: float) -> float:
        return self.cash + (self.position_qty * price)

    def execute_market(self, side: Side, quantity: int, candle: Candle, slippage_bps: float) -> Fill:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        sign = 1 if side == Side.BUY else -1
        fill_price = candle.close * (1 + (slippage_bps / 10_000.0) * sign)
        notional = fill_price * quantity
        fee = self._fee(notional)

        if side == Side.BUY:
            self.cash -= notional + fee
            new_qty = self.position_qty + quantity
            if self.position_qty >= 0:
                self.avg_entry = (
                    (self.avg_entry * self.position_qty) + (fill_price * quantity)
                ) / max(new_qty, 1)
            self.position_qty = new_qty
        else:
            self.cash += notional - fee
            self.position_qty -= quantity
            if self.position_qty == 0:
                self.avg_entry = 0.0

        fill = Fill(
            timestamp=candle.timestamp.isoformat(),
            side=side,
            quantity=quantity,
            price=fill_price,
            fee=fee,
            slippage_bps=slippage_bps,
        )
        self.fills.append(fill)
        return fill

    def close_position(self, candle: Candle, slippage_bps: float) -> float:
        if self.position_qty == 0:
            return 0.0
        qty = abs(self.position_qty)
        side = Side.SELL if self.position_qty > 0 else Side.BUY
        entry = self.avg_entry
        fill = self.execute_market(side=side, quantity=qty, candle=candle, slippage_bps=slippage_bps)
        pnl = (fill.price - entry) * qty if side == Side.SELL else (entry - fill.price) * qty
        self.realized_pnl += pnl - fill.fee
        return pnl - fill.fee
