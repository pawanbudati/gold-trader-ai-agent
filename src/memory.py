"""
Memory Module
Maintains episodic memory of past trade setups and experiential context.
Allows the AI agent to cross-reference proposed setups with historical win/loss cases.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("AgentMemory")
BASE_DIR = Path(__file__).resolve().parent.parent

class AgentMemory:
    def __init__(self):
        self.data_dir = BASE_DIR / "data"
        self.historical_signals: List[Dict[str, Any]] = []
        self.strategy_stats: Dict[str, Any] = {}
        self.recent_trade_history: List[Dict[str, Any]] = []
        self._load_memory()

    def _load_memory(self):
        signals_file = self.data_dir / "historical_signals.json"
        if signals_file.exists():
            try:
                with open(signals_file, "r", encoding="utf-8") as f:
                    self.historical_signals = json.load(f)
                logger.info(f"Loaded {len(self.historical_signals)} historical trade cases into episodic memory.")
            except Exception as e:
                logger.error(f"Error loading historical signals: {e}")

        stats_file = self.data_dir / "strategy_report.json"
        if stats_file.exists():
            try:
                with open(stats_file, "r", encoding="utf-8") as f:
                    self.strategy_stats = json.load(f)
            except Exception as e:
                logger.error(f"Error loading strategy stats: {e}")

    def query_similar_setups(self, direction: str, session: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Retrieves past trade setups with matching session and direction."""
        matches = [
            s for s in self.historical_signals 
            if s.get("direction") == direction
        ]
        return matches[-limit:] if matches else []

    def record_trade_execution(self, trade_event: Dict[str, Any]):
        """Records newly executed trade in live session memory."""
        self.recent_trade_history.append(trade_event)
        # Keep last 50 in memory
        if len(self.recent_trade_history) > 50:
            self.recent_trade_history.pop(0)
