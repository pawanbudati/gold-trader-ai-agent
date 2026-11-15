"""
Production-Grade Kafka Consumer for OCI Gold Trading Signals
Subscribes to the Kafka topic, parses structured events, pretty-prints formatted
alerts, saves events to local persistent log, and exposes pluggable execution hooks.
"""

import os
import sys
import json
import time
import signal
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Callable, Optional

logger = logging.getLogger("GoldSignalConsumer")

try:
    from kafka import KafkaConsumer
    from kafka.errors import NoBrokersAvailable
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.error("kafka-python-ng is required: pip install kafka-python-ng")

BASE_DIR = Path(__file__).resolve().parent.parent

class GoldSignalConsumer:
    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topic: Optional[str] = None,
        group_id: str = "gold-signal-consumers",
        auto_offset_reset: str = "latest",
        on_signal_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_update_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        log_to_file: bool = True
    ):
        self.bootstrap_servers = bootstrap_servers or os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.topic = topic or os.environ.get("KAFKA_TOPIC", "gold-trading-signals")
        self.group_id = group_id
        self.auto_offset_reset = auto_offset_reset
        self.on_signal_callback = on_signal_callback
        self.on_update_callback = on_update_callback
        self.log_to_file = log_to_file
        
        self.consumer: Optional[KafkaConsumer] = None
        self.running = False
        
        # Persistent event log file
        self.log_file = BASE_DIR / "data" / "received_signals.jsonl"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def _init_consumer(self) -> bool:
        if not KAFKA_AVAILABLE:
            logger.error("kafka-python-ng library not available.")
            return False

        logger.info(f"Connecting Consumer to Kafka at '{self.bootstrap_servers}'...")
        logger.info(f"Subscribing to Topic: '{self.topic}' | Group ID: '{self.group_id}' | Offset: '{self.auto_offset_reset}'")

        try:
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers.split(","),
                group_id=self.group_id,
                auto_offset_reset=self.auto_offset_reset,
                enable_auto_commit=True,
                auto_commit_interval_ms=2000,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                key_deserializer=lambda k: k.decode("utf-8") if k else None,
                consumer_timeout_ms=1000  # Allows periodic check of self.running
            )
            logger.info(f"✅ Successfully subscribed to topic '{self.topic}'")
            return True
        except NoBrokersAvailable:
            logger.error(f"Kafka cluster at {self.bootstrap_servers} is not reachable. Retrying...")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}")
            return False

    def start(self):
        """Starts the consumer loop with automatic reconnection."""
        self.running = True

        # Handle graceful shutdown
        def sig_handler(sig, frame):
            logger.info("\nShutdown signal received. Stopping consumer...")
            self.stop()

        signal.signal(signal.SIGINT, sig_handler)
        signal.signal(signal.SIGTERM, sig_handler)

        logger.info("=" * 80)
        logger.info("🎧 KAFKA CONSUMER LISTENING FOR GOLD TRADING SIGNALS")
        logger.info("=" * 80)

        while self.running:
            if not self.consumer:
                if not self._init_consumer():
                    time.sleep(5)
                    continue

            try:
                for message in self.consumer:
                    if not self.running:
                        break
                    self._handle_message(message)
            except Exception as e:
                logger.error(f"Error reading from Kafka stream: {e}")
                self.consumer = None
                time.sleep(3)

        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer connection closed.")

    def stop(self):
        self.running = False

    def _handle_message(self, message):
        """Dispatches and formats incoming Kafka events."""
        try:
            event = message.value
            event_type = event.get("event_type", "UNKNOWN")
            payload = event.get("payload", {})
            published_at = event.get("published_at_utc", datetime.now(timezone.utc).isoformat())

            # 1. Log to persistent JSONL file
            if self.log_to_file:
                self._append_to_log(event)

            # 2. Pretty-print to console based on event type
            if event_type == "TRADE_SIGNAL":
                self._display_trade_signal(payload, published_at)
                if self.on_signal_callback:
                    self.on_signal_callback(payload)

            elif event_type == "TRADE_UPDATE":
                self._display_trade_update(payload, published_at)
                if self.on_update_callback:
                    self.on_update_callback(payload)

            elif event_type == "HEARTBEAT":
                self._display_heartbeat(payload, published_at)

            elif event_type == "AGENT_STATUS":
                logger.info(f"ℹ️ [AGENT STATUS] {payload.get('status')} - {payload.get('message')}")

            else:
                logger.info(f"📩 [{event_type}] {json.dumps(payload, default=str)}")

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    def _display_trade_signal(self, payload: Dict[str, Any], published_at: str):
        direction = payload.get("direction", "UNKNOWN")
        symbol = payload.get("symbol", "XAUUSD")
        entry = payload.get("entry_price")
        sl = payload.get("sl")
        tp1 = payload.get("tp1")
        tp2 = payload.get("tp2")
        confidence = payload.get("confidence_score", 0.0)
        session = payload.get("session")
        regime = payload.get("market_regime")
        reasoning = payload.get("reasoning")

        # Color cues (ANSI)
        color = "\033[92m" if direction == "BUY" else "\033[91m"  # Green for BUY, Red for SELL
        reset = "\033[0m"
        bold = "\033[1m"

        print("\n" + "=" * 80)
        print(f"{bold}{color}🚨 INCOMING ACTIONABLE TRADE SIGNAL: {direction} {symbol}{reset}")
        print("=" * 80)
        print(f"  {bold}Entry Price:{reset}    ${entry:.2f}")
        print(f"  {bold}Stop Loss:{reset}      ${sl:.2f} ({payload.get('sl_pips', 150)} pips)")
        print(f"  {bold}Target 1:{reset}       ${tp1:.2f} ({payload.get('tp1_pips', 120)} pips)")
        print(f"  {bold}Target 2:{reset}       ${tp2:.2f} ({payload.get('tp2_pips', 260)} pips)")
        print(f"  {bold}AI Confidence:{reset}  {confidence * 100:.0f}%")
        print(f"  {bold}Market Regime:{reset}  {regime}")
        print(f"  {bold}Session:{reset}        {session}")
        print(f"  {bold}Published (UTC):{reset}{published_at}")
        print(f"  {bold}AI Reasoning:{reset}   {reasoning}")
        print("=" * 80 + "\n")

    def _display_trade_update(self, payload: Dict[str, Any], published_at: str):
        update_type = payload.get("update_type", "")
        summary = payload.get("summary", "")
        action = payload.get("action", "")

        print("\n" + "-" * 70)
        print(f"📢 [IN-TRADE UPDATE: {update_type}]")
        print(f"   {summary}")
        if action:
            print(f"   Action Required: \033[1m{action}\033[0m")
        print("-" * 70 + "\n")

    def _display_heartbeat(self, payload: Dict[str, Any], published_at: str):
        price = payload.get("gold_price")
        status = payload.get("session_status")
        logger.info(f"💓 Heartbeat: Gold @ ${price:.2f} | Status: {status} | Published: {published_at}")

    def _append_to_log(self, event: Dict[str, Any]):
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to append event to {self.log_file}: {e}")
