from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class CSVDataProvider:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def historical(self) -> List[Candle]:
        if not self.file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.file_path}")
        candles: List[Candle] = []
        with self.file_path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            required = {"timestamp", "open", "high", "low", "close", "volume"}
            fieldnames = set(reader.fieldnames or [])
            missing = sorted(required - fieldnames)
            if missing:
                raise ValueError(f"CSV missing required columns: {', '.join(missing)}")

            for line_no, row in enumerate(reader, start=2):
                try:
                    ts = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
                    candles.append(
                        Candle(
                            timestamp=ts,
                            open=float(row["open"]),
                            high=float(row["high"]),
                            low=float(row["low"]),
                            close=float(row["close"]),
                            volume=float(row["volume"]),
                        )
                    )
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Invalid CSV data at line {line_no}: {exc}") from exc
        return candles

    def realtime(self) -> Iterable[Candle]:
        for candle in self.historical():
            yield candle


class DataPipeline:
    def __init__(self, timeframe_minutes: int):
        self.timeframe = timedelta(minutes=timeframe_minutes)

    @staticmethod
    def normalize_timestamps(candles: List[Candle]) -> List[Candle]:
        normalized: List[Candle] = []
        for c in candles:
            ts = c.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            else:
                ts = ts.astimezone(timezone.utc)
            normalized.append(
                Candle(ts, c.open, c.high, c.low, c.close, c.volume)
            )
        normalized.sort(key=lambda c: c.timestamp)
        return normalized

    def validate(self, candles: List[Candle]) -> None:
        if not candles:
            raise ValueError("No candles provided")
        for c in candles:
            if c.high < max(c.open, c.close) or c.low > min(c.open, c.close):
                raise ValueError(f"Invalid OHLC data at {c.timestamp.isoformat()}")
            if c.volume < 0:
                raise ValueError(f"Negative volume at {c.timestamp.isoformat()}")

    def detect_gaps(self, candles: List[Candle]) -> List[tuple[datetime, datetime]]:
        gaps: List[tuple[datetime, datetime]] = []
        for prev, nxt in zip(candles, candles[1:]):
            delta = nxt.timestamp - prev.timestamp
            if delta > self.timeframe:
                gaps.append((prev.timestamp, nxt.timestamp))
        return gaps

    def run(self, candles: List[Candle]) -> List[Candle]:
        normalized = self.normalize_timestamps(candles)
        self.validate(normalized)
        return normalized
