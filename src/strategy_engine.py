"""
Strategy Engine Module
Quantitative Smart Money Concepts (SMC) & indicator screening.
Reverse-engineered from @intradaybulls009 (July 1 - Nov 15, 2026 dataset).
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

class StrategyEngine:
    def __init__(self, sl_pips: float = 150.0, tp1_pips: float = 120.0, tp2_pips: float = 260.0, min_atr_pips: float = 28.0):
        self.sl_pips = sl_pips
        self.tp1_pips = tp1_pips
        self.tp2_pips = tp2_pips
        self.min_atr_pips = min_atr_pips

    def get_asian_range(self, candles: List[Dict[str, Any]], current_date) -> Tuple[Optional[float], Optional[float]]:
        """Calculates Asian session (00:00 - 06:00 UTC) High & Low bounds."""
        asian_candles = [
            c for c in candles 
            if c["datetime_utc"].date() == current_date and 0 <= c["datetime_utc"].hour < 6
        ]
        if not asian_candles:
            return None, None
        return max(c["high"] for c in asian_candles), min(c["low"] for c in asian_candles)

    def scan_setup(self, candles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Scans current market structure against quantitative filters:
        1. Session Killzone Filter (London Open 06:30-09:30 UTC or Asian 03:30-05:00 UTC)
        2. Asian Range Breakout
        3. Fair Value Gap (FVG) confirmation
        4. ATR(14) Volatility Expansion
        5. EMA 21 / EMA 50 trend alignment
        6. RSI(14) momentum confirmation
        """
        if len(candles) < 30:
            return None

        curr = candles[-1]
        dt_utc = curr["datetime_utc"]
        hour = dt_utc.hour + dt_utc.minute / 60.0

        # Session Filters
        in_london = 6.5 <= hour <= 9.5
        in_asian = 3.5 <= hour <= 5.0
        if not (in_london or in_asian):
            return None

        # Indicator Calculations
        closes = [c["close"] for c in candles]
        ema21 = self._ema(closes, 21)[-1]
        ema50 = self._ema(closes, 50)[-1]
        atr14_pips = self._atr(candles, 14)[-1] * 10.0
        rsi14 = self._rsi(closes, 14)[-1]

        if atr14_pips < self.min_atr_pips:
            return None

        asian_high, asian_low = self.get_asian_range(candles, dt_utc.date())
        if not asian_high or not asian_low:
            return None

        c0, c1, c2 = candles[-3], candles[-2], candles[-1]
        price = curr["close"]

        # SELL Condition
        bearish_fvg = c2["high"] < c0["low"]
        is_breakout_sell = (c2["close"] < asian_low) and (c2["close"] < ema21 < ema50)
        is_fvg_sell = bearish_fvg and (c2["close"] < ema21) and (rsi14 <= 45)

        if is_breakout_sell or is_fvg_sell:
            sl = round(price + (self.sl_pips / 10.0), 2)
            tp1 = round(price - (self.tp1_pips / 10.0), 2)
            tp2 = round(price - (self.tp2_pips / 10.0), 2)
            return {
                "direction": "SELL",
                "entry_price": price,
                "sl": sl,
                "tp1": tp1,
                "tp2": tp2,
                "sl_pips": self.sl_pips,
                "tp1_pips": self.tp1_pips,
                "tp2_pips": self.tp2_pips,
                "session": "London Open Killzone" if in_london else "Asian Session",
                "asian_range": {"high": asian_high, "low": asian_low},
                "indicators": {"ema21": ema21, "ema50": ema50, "rsi14": rsi14, "atr_pips": atr14_pips},
                "fvg_detected": bearish_fvg,
                "timestamp_utc": dt_utc.isoformat(),
                "timestamp_ist": (dt_utc + timedelta(hours=5, minutes=30)).isoformat(),
            }

        # BUY Condition
        bullish_fvg = c2["low"] > c0["high"]
        is_breakout_buy = (c2["close"] > asian_high) and (c2["close"] > ema21 > ema50)
        is_fvg_buy = bullish_fvg and (c2["close"] > ema21) and (rsi14 >= 55)

        if is_breakout_buy or is_fvg_buy:
            sl = round(price - (self.sl_pips / 10.0), 2)
            tp1 = round(price + (self.tp1_pips / 10.0), 2)
            tp2 = round(price + (self.tp2_pips / 10.0), 2)
            return {
                "direction": "BUY",
                "entry_price": price,
                "sl": sl,
                "tp1": tp1,
                "tp2": tp2,
                "sl_pips": self.sl_pips,
                "tp1_pips": self.tp1_pips,
                "tp2_pips": self.tp2_pips,
                "session": "London Open Killzone" if in_london else "Asian Session",
                "asian_range": {"high": asian_high, "low": asian_low},
                "indicators": {"ema21": ema21, "ema50": ema50, "rsi14": rsi14, "atr_pips": atr14_pips},
                "fvg_detected": bullish_fvg,
                "timestamp_utc": dt_utc.isoformat(),
                "timestamp_ist": (dt_utc + timedelta(hours=5, minutes=30)).isoformat(),
            }

        return None

    def _ema(self, series: List[float], period: int) -> List[float]:
        n = len(series)
        ema = [None] * n
        if n < period: return ema
        ema[period - 1] = sum(series[:period]) / period
        mult = 2.0 / (period + 1.0)
        for i in range(period, n): ema[i] = (series[i] - ema[i - 1]) * mult + ema[i - 1]
        return ema

    def _rsi(self, series: List[float], period: int = 14) -> List[float]:
        n = len(series)
        rsi = [None] * n
        if n < period + 1: return rsi
        g = [max(0.0, series[i] - series[i - 1]) for i in range(1, n)]
        l = [max(0.0, series[i - 1] - series[i]) for i in range(1, n)]
        ag, al = sum(g[:period]) / period, sum(l[:period]) / period
        rsi[period] = 100.0 if al == 0 else 100.0 - (100.0 / (1.0 + ag / al))
        for i in range(period + 1, n):
            ag = (ag * (period - 1) + g[i - 1]) / period
            al = (al * (period - 1) + l[i - 1]) / period
            rsi[i] = 100.0 if al == 0 else 100.0 - (100.0 / (1.0 + ag / al))
        return rsi

    def _atr(self, candles: List[Dict[str, Any]], period: int = 14) -> List[float]:
        n = len(candles)
        atr = [None] * n
        if n < period + 1: return atr
        tr = [candles[0]["high"] - candles[0]["low"]]
        for i in range(1, n):
            tr.append(max(candles[i]["high"] - candles[i]["low"], abs(candles[i]["high"] - candles[i - 1]["close"]), abs(candles[i]["low"] - candles[i - 1]["close"])))
        atr[period - 1] = sum(tr[:period]) / period
        for i in range(period, n):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
        return atr
