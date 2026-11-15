"""
Market Feed Module
Provides real-time Gold (XAUUSD) candlestick data with zero authentication.
Default source: PAXGUSDT (1:1 physically backed London Gold token).
"""

import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger("GoldMarketFeed")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0"

class GoldMarketFeed:
    def __init__(self, symbol: str = "PAXGUSDT", interval: str = "5m"):
        self.symbol = symbol
        self.interval = interval
        self.base_url = "https://api.binance.com/api/v3/klines"

    def fetch_latest_candles(self, limit: int = 80) -> List[Dict[str, Any]]:
        """Fetches the latest M5 candlestick batch."""
        url = f"{self.base_url}?symbol={self.symbol}&interval={self.interval}&limit={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                candles = []
                for k in data:
                    candles.append({
                        "timestamp": int(k[0] / 1000),
                        "datetime_utc": datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc),
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5])
                    })
                return candles
        except Exception as e:
            logger.error(f"Failed to fetch market data from {url}: {e}")
            return []

    def get_latest_price(self) -> Optional[float]:
        """Fetches current tick price."""
        candles = self.fetch_latest_candles(limit=1)
        if candles:
            return candles[-1]["close"]
        return None
