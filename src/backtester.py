"""
Autonomous AI Gold Strategy Backtesting Engine
Simulates historical market conditions bar-by-bar using the exact SMC strategy rules:
- Asian Range Box (00:00 - 06:00 UTC)
- London / Asian Killzones
- Dual-Ticket Order Execution (TP1 +120p, TP2 +260p, SL 150p)
- Auto-Breakeven at +110 pips
- 15-minute stagnation cut at -50 pips
"""

import os
import sys
import json
import math
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0"
BASE_DIR = Path(__file__).resolve().parent.parent

class GoldBacktester:
    def __init__(
        self,
        symbol: str = "PAXGUSDT",
        initial_balance: float = 10000.0,
        risk_pct: float = 1.0,
        sl_pips: float = 150.0,
        tp1_pips: float = 120.0,
        tp2_pips: float = 260.0,
        min_atr_pips: float = 28.0
    ):
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.risk_pct = risk_pct
        self.sl_pips = sl_pips
        self.tp1_pips = tp1_pips
        self.tp2_pips = tp2_pips
        self.min_atr_pips = min_atr_pips
        self.cache_file = BASE_DIR / "data" / "cached_m5_candles.json"

    def fetch_historical_candles(self, start_date_str: str, end_date_str: str) -> List[Dict[str, Any]]:
        """Fetches and caches M5 historical gold candles."""
        dt_start = datetime.fromisoformat(start_date_str).replace(tzinfo=timezone.utc)
        dt_end = datetime.fromisoformat(end_date_str).replace(tzinfo=timezone.utc)
        start_ms = int(dt_start.timestamp() * 1000)
        end_ms = int(dt_end.timestamp() * 1000)

        # Check local cache first
        if self.cache_file.exists():
            print(f"Loading cached historical candles from {self.cache_file.name}...")
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                if cached and cached[0]["timestamp"] <= start_ms // 1000 and cached[-1]["timestamp"] >= end_ms // 1000:
                    filtered = [c for c in cached if start_ms // 1000 <= c["timestamp"] <= end_ms // 1000]
                    for c in filtered:
                        c["datetime_utc"] = datetime.fromtimestamp(c["timestamp"], tz=timezone.utc)
                    print(f"Loaded {len(filtered)} candles from cache.")
                    return filtered
            except Exception as e:
                print(f"Cache read error: {e}")

        print(f"Fetching historical M5 candles from {start_date_str} to {end_date_str}...")
        all_candles = []
        curr_start = start_ms

        while curr_start < end_ms:
            url = f"https://api.binance.com/api/v3/klines?symbol={self.symbol}&interval=5m&startTime={curr_start}&limit=1000"
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode())
                    if not data:
                        break
                    for k in data:
                        ts = int(k[0] / 1000)
                        if ts * 1000 > end_ms:
                            break
                        all_candles.append({
                            "timestamp": ts,
                            "open": float(k[1]),
                            "high": float(k[2]),
                            "low": float(k[3]),
                            "close": float(k[4]),
                            "volume": float(k[5])
                        })
                    last_ts = data[-1][0]
                    curr_start = last_ts + (5 * 60 * 1000)
                    print(f"  Fetched {len(all_candles)} candles (Current: {datetime.fromtimestamp(last_ts/1000, tz=timezone.utc).strftime('%Y-%m-%d')} )")
                    if len(data) < 1000:
                        break
            except Exception as e:
                print(f"Fetch error: {e}. Retrying in 2s...")
                import time
                time.sleep(2)

        # Cache to disk for instant re-runs
        if all_candles:
            try:
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(all_candles, f)
                print(f"Cached {len(all_candles)} candles to {self.cache_file}.")
            except Exception as e:
                print(f"Cache write error: {e}")

        for c in all_candles:
            c["datetime_utc"] = datetime.fromtimestamp(c["timestamp"], tz=timezone.utc)

        return all_candles

    def run_backtest(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Runs the bar-by-bar backtest simulation."""
        balance = self.initial_balance
        peak_balance = self.initial_balance
        max_drawdown_dollars = 0.0
        max_drawdown_pct = 0.0

        trades = []
        in_trade = False
        active_position = None
        last_trade_date = None

        print("\n" + "=" * 80)
        print("SIMULATING STRATEGY BAR-BY-BAR ON HISTORICAL GOLD DATA...")
        print("=" * 80)

        n = len(candles)
        for i in range(50, n):
            sub_candles = candles[:i + 1]
            curr = sub_candles[-1]
            dt_utc = curr["datetime_utc"]
            hour = dt_utc.hour + dt_utc.minute / 60.0

            # If inside a trade, manage it bar-by-bar
            if in_trade and active_position:
                pos = active_position
                direction = pos["direction"]
                entry = pos["entry"]
                c_high = curr["high"]
                c_low = curr["low"]
                c_close = curr["close"]

                # PnL in pips
                bar_max_pips = (c_high - entry) * 10.0 if direction == "BUY" else (entry - c_low) * 10.0
                bar_min_pips = (c_low - entry) * 10.0 if direction == "BUY" else (entry - c_high) * 10.0

                pos["duration_candles"] += 1
                elapsed_minutes = pos["duration_candles"] * 5

                # 1. Check Target 1 (+120 pips)
                if pos["t1_open"] and bar_max_pips >= self.tp1_pips:
                    pos["t1_open"] = False
                    pos["be_locked"] = True
                    pos["sl"] = entry  # Move SL to Breakeven
                    pos["t1_profit"] = pos["half_lot"] * self.tp1_pips * 10.0
                    pos["t1_exit_bar"] = i

                # 2. Check Target 2 (+260 pips)
                if pos["t2_open"] and bar_max_pips >= self.tp2_pips:
                    pos["t2_open"] = False
                    pos["t2_profit"] = pos["half_lot"] * self.tp2_pips * 10.0
                    pos["t2_exit_bar"] = i

                # If both targets hit -> Trade is fully closed with maximum profit
                if not pos["t1_open"] and not pos["t2_open"]:
                    total_pnl = pos["t1_profit"] + pos["t2_profit"]
                    balance += total_pnl
                    pos["exit_price"] = pos["tp2"]
                    pos["pnl"] = total_pnl
                    pos["pnl_pips"] = (self.tp1_pips + self.tp2_pips) / 2.0
                    pos["outcome"] = "WIN_FULL_TARGETS"
                    pos["exit_date"] = dt_utc.isoformat()
                    trades.append(pos)
                    in_trade = False
                    active_position = None
                    continue

                # 3. Check Stop Loss
                is_sl_hit = (direction == "BUY" and c_low <= pos["sl"]) or (direction == "SELL" and c_high >= pos["sl"])
                if is_sl_hit:
                    if pos["be_locked"]:
                        # Ticket 1 won at TP1, Ticket 2 stopped at Breakeven ($0)
                        total_pnl = pos.get("t1_profit", 0.0)
                        balance += total_pnl
                        pos["exit_price"] = entry
                        pos["pnl"] = total_pnl
                        pos["pnl_pips"] = self.tp1_pips / 2.0
                        pos["outcome"] = "WIN_TP1_BE_STOP"
                    else:
                        # Full Stop Loss hit on both tickets
                        total_pnl = -(pos["half_lot"] * 2.0) * self.sl_pips * 10.0
                        balance += total_pnl
                        pos["exit_price"] = pos["sl"]
                        pos["pnl"] = total_pnl
                        pos["pnl_pips"] = -self.sl_pips
                        pos["outcome"] = "FULL_STOP_LOSS"

                    pos["exit_date"] = dt_utc.isoformat()
                    trades.append(pos)
                    in_trade = False
                    active_position = None
                    continue

                # 4. Check 15-Minute Defense Rule (-50 pips stagnation cut)
                if elapsed_minutes >= 15 and bar_min_pips <= -50.0 and not pos["be_locked"]:
                    loss = -(pos["half_lot"] * 2.0) * 50.0 * 10.0
                    balance += loss
                    pos["exit_price"] = c_close
                    pos["pnl"] = loss
                    pos["pnl_pips"] = -50.0
                    pos["outcome"] = "EARLY_INVALIDATION_CUT"
                    pos["exit_date"] = dt_utc.isoformat()
                    trades.append(pos)
                    in_trade = False
                    active_position = None
                    continue

                # Track drawdown
                if balance > peak_balance:
                    peak_balance = balance
                dd_dollars = peak_balance - balance
                dd_pct = (dd_dollars / peak_balance) * 100.0 if peak_balance > 0 else 0
                if dd_pct > max_drawdown_pct:
                    max_drawdown_pct = dd_pct
                    max_drawdown_dollars = dd_dollars

                continue

            # If not in trade, scan for entry
            in_london = 6.5 <= hour <= 9.5
            in_asian = 3.5 <= hour <= 5.0
            if not (in_london or in_asian):
                continue

            if last_trade_date == dt_utc.date():
                continue

            # Asian Range
            asian_candles = [
                c for c in sub_candles 
                if c["datetime_utc"].date() == dt_utc.date() and 0 <= c["datetime_utc"].hour < 6
            ]
            if not asian_candles:
                continue
            asian_high = max(c["high"] for c in asian_candles)
            asian_low = min(c["low"] for c in asian_candles)

            closes = [c["close"] for c in sub_candles]
            ema21 = self._ema(closes, 21)[-1]
            ema50 = self._ema(closes, 50)[-1]
            atr14_pips = self._atr(sub_candles, 14)[-1] * 10.0
            rsi14 = self._rsi(closes, 14)[-1]

            if atr14_pips < self.min_atr_pips:
                continue

            c0, c1, c2 = sub_candles[-3], sub_candles[-2], sub_candles[-1]
            price = curr["close"]

            # SELL
            bearish_fvg = c2["high"] < c0["low"]
            if (c2["close"] < asian_low or bearish_fvg) and (c2["close"] < ema21 < ema50) and rsi14 <= 45:
                direction = "SELL"
                sl = round(price + (self.sl_pips / 10.0), 2)
                tp1 = round(price - (self.tp1_pips / 10.0), 2)
                tp2 = round(price - (self.tp2_pips / 10.0), 2)
            # BUY
            elif (c2["close"] > asian_high or (c2["low"] > c0["high"])) and (c2["close"] > ema21 > ema50) and rsi14 >= 55:
                direction = "BUY"
                sl = round(price - (self.sl_pips / 10.0), 2)
                tp1 = round(price + (self.tp1_pips / 10.0), 2)
                tp2 = round(price + (self.tp2_pips / 10.0), 2)
            else:
                continue

            # Calculate position size
            risk_dollars = balance * (self.risk_pct / 100.0)
            lot_size = round(risk_dollars / (self.sl_pips * 10.0), 2)
            half_lot = max(0.01, round(lot_size / 2.0, 2))

            in_trade = True
            last_trade_date = dt_utc.date()
            active_position = {
                "trade_num": len(trades) + 1,
                "direction": direction,
                "entry": price,
                "sl": sl,
                "tp1": tp1,
                "tp2": tp2,
                "half_lot": half_lot,
                "entry_date": dt_utc.isoformat(),
                "session": "London Open" if in_london else "Asian Killzone",
                "t1_open": True,
                "t2_open": True,
                "be_locked": False,
                "t1_profit": 0.0,
                "t2_profit": 0.0,
                "duration_candles": 0
            }

        # Calculate metrics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t["pnl"] > 0]
        losing_trades = [t for t in trades if t["pnl"] < 0]
        breakeven_trades = [t for t in trades if t["pnl"] == 0]

        gross_profit = sum(t["pnl"] for t in winning_trades)
        gross_loss = abs(sum(t["pnl"] for t in losing_trades))
        net_profit = gross_profit - gross_loss
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 999.0
        win_rate = round((len(winning_trades) / total_trades) * 100.0, 1) if total_trades > 0 else 0.0

        results = {
            "initial_balance": self.initial_balance,
            "final_balance": round(balance, 2),
            "net_profit_dollars": round(net_profit, 2),
            "net_return_pct": round((net_profit / self.initial_balance) * 100.0, 2),
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "breakeven_trades": len(breakeven_trades),
            "win_rate_pct": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "max_drawdown_dollars": round(max_drawdown_dollars, 2),
            "avg_win_dollars": round(gross_profit / len(winning_trades), 2) if winning_trades else 0.0,
            "avg_loss_dollars": round(gross_loss / len(losing_trades), 2) if losing_trades else 0.0,
            "trades": trades
        }

        # Save to disk
        out_json = BASE_DIR / "data" / "backtest_results.json"
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Saved full trade log to {out_json}")

        return results

    def _ema(self, s, p):
        n = len(s); ema = [None]*n
        if n < p: return ema
        ema[p-1] = sum(s[:p])/p; mult = 2.0/(p+1.0)
        for i in range(p, n): ema[i] = (s[i]-ema[i-1])*mult + ema[i-1]
        return ema

    def _rsi(self, s, p=14):
        n = len(s); rsi = [None]*n
        if n < p+1: return rsi
        g = [max(0.0, s[i]-s[i-1]) for i in range(1, n)]
        l = [max(0.0, s[i-1]-s[i]) for i in range(1, n)]
        ag, al = sum(g[:p])/p, sum(l[:p])/p
        rsi[p] = 100.0 if al == 0 else 100.0 - (100.0/(1.0+ag/al))
        for i in range(p+1, n):
            ag = (ag*(p-1)+g[i-1])/p; al = (al*(p-1)+l[i-1])/p
            rsi[i] = 100.0 if al == 0 else 100.0 - (100.0/(1.0+ag/al))
        return rsi

    def _atr(self, c, p=14):
        n = len(c); atr = [None]*n
        if n < p+1: return atr
        tr = [c[0]["high"]-c[0]["low"]]
        for i in range(1, n): tr.append(max(c[i]["high"]-c[i]["low"], abs(c[i]["high"]-c[i-1]["close"]), abs(c[i]["low"]-c[i-1]["close"])))
        atr[p-1] = sum(tr[:p])/p
        for i in range(p, n): atr[i] = (atr[i-1]*(p-1)+tr[i])/p
        return atr
