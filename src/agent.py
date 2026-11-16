"""
Main Autonomous AI Gold Trading Agent
Orchestrates Perception -> Reasoning -> Action -> Reflection loop.
Runs 24/7 on OCI VM and dispatches trade events to Google Cloud Pub/Sub.
"""

import os
import sys
import time
import logging
from datetime import datetime, timezone

from .market_feed import GoldMarketFeed
from .strategy_engine import StrategyEngine
from .memory import AgentMemory
from .brain import AgentBrain
from .pubsub_publisher import PubSubPublisher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("AutonomousGoldAgent")

class AutonomousGoldAgent:
    def __init__(self):
        # Configuration
        self.symbol = os.environ.get("GOLD_SYMBOL", "XAUUSD")
        self.market_symbol = os.environ.get("MARKET_SYMBOL", "PAXGUSDT")
        self.gcp_project_id = os.environ.get("GCP_PROJECT_ID", "fourth-arena-460820-s6")
        self.pubsub_topic_id = os.environ.get("PUBSUB_TOPIC_ID", "gold-trading-signals-agent-001")
        self.credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "service_account.json")

        # Initialize Subsystems
        self.feed = GoldMarketFeed(symbol=self.market_symbol, interval="5m")
        self.strategy = StrategyEngine(
            sl_pips=float(os.environ.get("SL_PIPS", "150.0")),
            tp1_pips=float(os.environ.get("TP1_PIPS", "120.0")),
            tp2_pips=float(os.environ.get("TP2_PIPS", "260.0")),
            min_atr_pips=float(os.environ.get("MIN_ATR_PIPS", "28.0"))
        )
        self.memory = AgentMemory()
        self.brain = AgentBrain(self.memory)
        self.publisher = PubSubPublisher(
            project_id=self.gcp_project_id,
            topic_id=self.pubsub_topic_id,
            credentials_path=self.credentials_path
        )

        # In-flight State
        self.active_trade = None
        self.last_trade_date = None
        self.last_heartbeat = 0

    def start(self):
        logger.info("=" * 80)
        logger.info("🤖 AUTONOMOUS OCI AI GOLD TRADING AGENT ONLINE")
        logger.info(f"Target Asset:     {self.symbol}")
        logger.info(f"Market Feed:      {self.market_symbol} (Zero-auth live feed)")
        logger.info(f"Pub/Sub Project:  {self.gcp_project_id or '(Not Set - local log mode)'}")
        logger.info(f"Pub/Sub Topic:    {self.pubsub_topic_id}")
        logger.info(f"Confidence Gate:  {self.brain.min_confidence_threshold * 100}%")
        logger.info("=" * 80)

        # Send initial boot status to Google Cloud Pub/Sub
        self.publisher.publish_event("AGENT_STATUS", {
            "status": "ONLINE",
            "message": "AI Gold Agent booted on OCI VM. Streaming signals to Google Pub/Sub."
        })

        while True:
            try:
                candles = self.feed.fetch_latest_candles(limit=80)
                if candles:
                    curr = candles[-1]
                    price = curr["close"]
                    dt_utc = curr["datetime_utc"]
                    hour_utc = dt_utc.hour + dt_utc.minute / 60.0

                    self._check_heartbeat(price, hour_utc)

                    if self.active_trade:
                        self._manage_active_trade(price)
                    else:
                        self._scan_and_deliberate(candles, dt_utc)

                time.sleep(20)  # 20-second cadence
            except KeyboardInterrupt:
                logger.info("Agent stopped by user.")
                break
            except Exception as e:
                logger.error(f"Unexpected error in agent loop: {e}", exc_info=True)
                time.sleep(10)

    def _scan_and_deliberate(self, candles, dt_utc):
        # 1. System 1: Fast Quantitative SMC Screen
        setup = self.strategy.scan_setup(candles)
        if not setup:
            return

        # 1 Trade per day limit
        if self.last_trade_date == dt_utc.date():
            return

        # 2. System 2: AI Brain Cognitive Deliberation & Confidence Scoring
        logger.info(f"Candidate setup detected: {setup['direction']} Gold @ {setup['entry_price']}. Deliberating...")
        deliberation = self.brain.deliberate_on_setup(setup)

        logger.info(f"Deliberation Result: Approved={deliberation['approved']} | Confidence={deliberation['confidence_score'] * 100}% | Regime={deliberation['market_regime']}")

        if not deliberation["approved"]:
            logger.warning(f"Setup REJECTED by AI Brain (Confidence {deliberation['confidence_score']} < {self.brain.min_confidence_threshold}).")
            return

        # 3. Action Dispatch: Publish High-Confidence Signal to Google Pub/Sub
        signal_payload = {
            "symbol": self.symbol,
            "direction": setup["direction"],
            "entry_price": setup["entry_price"],
            "sl": setup["sl"],
            "tp1": setup["tp1"],
            "tp2": setup["tp2"],
            "sl_pips": setup["sl_pips"],
            "tp1_pips": setup["tp1_pips"],
            "tp2_pips": setup["tp2_pips"],
            "session": setup["session"],
            "confidence_score": deliberation["confidence_score"],
            "market_regime": deliberation["market_regime"],
            "box_quality": deliberation["box_quality"],
            "reasoning": deliberation["deliberation_reasoning"],
            "timestamp_utc": setup["timestamp_utc"],
            "timestamp_ist": setup["timestamp_ist"],
            "summary": f"{setup['direction']} {self.symbol} @ {setup['entry_price']} | SL: {setup['sl']} | TP1: {setup['tp1']} | TP2: {setup['tp2']} (Confidence: {deliberation['confidence_score']*100}%)"
        }

        self.publisher.publish_event("TRADE_SIGNAL", signal_payload)

        # 4. Record to live state & episodic memory
        self.active_trade = {
            "direction": setup["direction"],
            "entry_price": setup["entry_price"],
            "sl": setup["sl"],
            "tp1": setup["tp1"],
            "tp2": setup["tp2"],
            "tp1_hit": False,
            "entry_time": time.time(),
            "signal_details": signal_payload
        }
        self.memory.record_trade_execution(signal_payload)
        self.last_trade_date = dt_utc.date()

    def _manage_active_trade(self, current_price):
        t = self.active_trade
        direction = t["direction"]
        entry = t["entry_price"]

        pips = (entry - current_price) * 10.0 if direction == "SELL" else (current_price - entry) * 10.0
        elapsed_min = (time.time() - t["entry_time"]) / 60.0

        # Milestone 1: +110 to +120 Pips -> Move SL to Breakeven
        if not t["tp1_hit"] and pips >= self.strategy.tp1_pips:
            t["tp1_hit"] = True
            t["sl"] = entry # Breakeven
            self.publisher.publish_event("TRADE_UPDATE", {
                "update_type": "TP1_HIT_BREAKEVEN_LOCKED",
                "symbol": self.symbol,
                "direction": direction,
                "entry_price": entry,
                "current_price": current_price,
                "profit_pips": round(pips, 1),
                "action": "CLOSE_50_PERCENT_AND_MOVE_SL_TO_BREAKEVEN",
                "summary": f"🎯 TP1 HIT on {direction} {self.symbol} (+{pips:.1f} pips). SL moved to Breakeven."
            })

        # Milestone 2: +260 Pips -> Full Target Achieved
        if pips >= self.strategy.tp2_pips:
            self.publisher.publish_event("TRADE_UPDATE", {
                "update_type": "TP2_HIT_TARGET_REACHED",
                "symbol": self.symbol,
                "direction": direction,
                "entry_price": entry,
                "current_price": current_price,
                "profit_pips": round(pips, 1),
                "action": "CLOSE_REMAINING_POSITION",
                "summary": f"🚀 TP2 HIT on {direction} {self.symbol} (+{pips:.1f} pips). Trade Complete."
            })
            self.active_trade = None
            return

        # Stop Loss
        is_sl_hit = (direction == "BUY" and current_price <= t["sl"]) or (direction == "SELL" and current_price >= t["sl"])
        if is_sl_hit:
            self.publisher.publish_event("TRADE_UPDATE", {
                "update_type": "STOP_LOSS_HIT",
                "symbol": self.symbol,
                "direction": direction,
                "exit_price": current_price,
                "loss_pips": round(-abs(pips), 1),
                "summary": f"🛑 STOP LOSS HIT on {direction} {self.symbol} at {current_price}."
            })
            self.active_trade = None
            return

        # 15-Minute Stagnation Defense Cut (-50 pips)
        if elapsed_min >= 15.0 and pips <= -50.0 and not t["tp1_hit"]:
            self.publisher.publish_event("TRADE_UPDATE", {
                "update_type": "EARLY_INVALIDATION_CUT",
                "symbol": self.symbol,
                "direction": direction,
                "exit_price": current_price,
                "loss_pips": round(pips, 1),
                "action": "CLOSE_IMMEDIATELY",
                "summary": f"⚠️ EARLY CUT on {direction} {self.symbol}: Stalled after 15 mins (-50 pips). Exited early to protect capital."
            })
            self.active_trade = None
            return

    def _check_heartbeat(self, current_price, hour_utc):
        now = time.time()
        if now - self.last_heartbeat >= 900:  # Every 15 minutes
            session_status = "INSIDE_KILLZONE" if (6.5 <= hour_utc <= 9.5 or 3.5 <= hour_utc <= 5.0) else "OUTSIDE_KILLZONE"
            self.publisher.publish_event("HEARTBEAT", {
                "status": "HEALTHY",
                "gold_price": current_price,
                "session_status": session_status,
                "in_trade": bool(self.active_trade),
                "summary": f"Heartbeat: Gold @ ${current_price:.2f} | Status: {session_status}"
            })
            self.last_heartbeat = now

def run_agent():
    agent = AutonomousGoldAgent()
    agent.start()

if __name__ == "__main__":
    run_agent()
