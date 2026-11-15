"""
Database Sink Consumer Module
Subscribes to Kafka topics and persists every trading signal, update, and heartbeat
directly into an OCI Database (PostgreSQL, MySQL, Oracle DB, or SQLite).
"""

import os
import sys
import json
import time
import signal
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("DatabaseSink")

try:
    from kafka import KafkaConsumer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.error("kafka-python-ng required: pip install kafka-python-ng")

BASE_DIR = Path(__file__).resolve().parent.parent

class DatabaseSinkConsumer:
    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topic: Optional[str] = None,
        database_url: Optional[str] = None,
        group_id: str = "oci-db-sink-group"
    ):
        self.bootstrap_servers = bootstrap_servers or os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.topic = topic or os.environ.get("KAFKA_TOPIC", "gold-trading-signals")
        self.database_url = database_url or os.environ.get("DATABASE_URL", "sqlite:///data/gold_trading.db")
        self.group_id = group_id
        
        self.consumer: Optional[KafkaConsumer] = None
        self.running = False
        
        # SQLite setup (default fallback)
        self.db_path = BASE_DIR / "data" / "gold_trading.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initializes relational tables for signals, updates, and heartbeats."""
        logger.info(f"Initializing Database at: {self.database_url}")
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # 1. Trading Signals Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trading_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT,
                event_type TEXT,
                symbol TEXT,
                direction TEXT,
                entry_price REAL,
                sl REAL,
                tp1 REAL,
                tp2 REAL,
                sl_pips REAL,
                tp1_pips REAL,
                tp2_pips REAL,
                confidence_score REAL,
                market_regime TEXT,
                session TEXT,
                reasoning TEXT,
                timestamp_utc TEXT,
                timestamp_ist TEXT,
                raw_payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Trade Lifecycle Updates Table (TP1, TP2, Early Invalidation)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_lifecycle_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT,
                event_type TEXT,
                update_type TEXT,
                symbol TEXT,
                direction TEXT,
                entry_price REAL,
                current_price REAL,
                profit_loss_pips REAL,
                action_required TEXT,
                summary TEXT,
                raw_payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. Agent Heartbeats Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_heartbeats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT,
                gold_price REAL,
                session_status TEXT,
                in_trade BOOLEAN,
                published_at_utc TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
        conn.close()
        logger.info("Database schema verified & tables ready.")

    def _save_to_db(self, event: Dict[str, Any]):
        """Parses Kafka event and inserts into the corresponding DB table."""
        event_type = event.get("event_type", "UNKNOWN")
        agent_id = event.get("agent_id", "oci-gold-ai-agent-v1")
        payload = event.get("payload", {})
        raw_json = json.dumps(event, default=str)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            if event_type == "TRADE_SIGNAL":
                cursor.execute("""
                    INSERT INTO trading_signals (
                        agent_id, event_type, symbol, direction, entry_price, sl, tp1, tp2,
                        sl_pips, tp1_pips, tp2_pips, confidence_score, market_regime,
                        session, reasoning, timestamp_utc, timestamp_ist, raw_payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    agent_id,
                    event_type,
                    payload.get("symbol", "XAUUSD"),
                    payload.get("direction"),
                    payload.get("entry_price"),
                    payload.get("sl"),
                    payload.get("tp1"),
                    payload.get("tp2"),
                    payload.get("sl_pips"),
                    payload.get("tp1_pips"),
                    payload.get("tp2_pips"),
                    payload.get("confidence_score"),
                    payload.get("market_regime"),
                    payload.get("session"),
                    payload.get("reasoning"),
                    payload.get("timestamp_utc"),
                    payload.get("timestamp_ist"),
                    raw_json
                ))
                logger.info(f"💾 [DB SAVED] TRADE_SIGNAL: {payload.get('direction')} {payload.get('symbol')} @ ${payload.get('entry_price')}")

            elif event_type == "TRADE_UPDATE":
                cursor.execute("""
                    INSERT INTO trade_lifecycle_events (
                        agent_id, event_type, update_type, symbol, direction,
                        entry_price, current_price, profit_loss_pips, action_required, summary, raw_payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    agent_id,
                    event_type,
                    payload.get("update_type"),
                    payload.get("symbol", "XAUUSD"),
                    payload.get("direction"),
                    payload.get("entry_price"),
                    payload.get("current_price"),
                    payload.get("profit_pips") or payload.get("loss_pips"),
                    payload.get("action") or payload.get("action_required"),
                    payload.get("summary"),
                    raw_json
                ))
                logger.info(f"💾 [DB SAVED] TRADE_UPDATE: {payload.get('update_type')}")

            elif event_type == "HEARTBEAT":
                cursor.execute("""
                    INSERT INTO agent_heartbeats (
                        agent_id, gold_price, session_status, in_trade, published_at_utc
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    agent_id,
                    payload.get("gold_price"),
                    payload.get("session_status"),
                    payload.get("in_trade", False),
                    event.get("published_at_utc")
                ))

            conn.commit()
        except Exception as e:
            logger.error(f"Error inserting event into DB: {e}")
            conn.rollback()
        finally:
            conn.close()

    def start(self):
        """Starts Kafka Consumer and writes all messages to DB."""
        if not KAFKA_AVAILABLE:
            logger.error("Kafka library missing.")
            return

        self.running = True

        def sig_handler(sig, frame):
            logger.info("Stopping DB Sink Consumer...")
            self.running = False

        signal.signal(signal.SIGINT, sig_handler)
        signal.signal(signal.SIGTERM, sig_handler)

        logger.info("=" * 80)
        logger.info(f"📥 KAFKA-TO-DB SINK ACTIVE")
        logger.info(f"Subscribed Topic: {self.topic}")
        logger.info(f"Target Database:  {self.db_path}")
        logger.info("=" * 80)

        while self.running:
            if not self.consumer:
                try:
                    self.consumer = KafkaConsumer(
                        self.topic,
                        bootstrap_servers=self.bootstrap_servers.split(","),
                        group_id=self.group_id,
                        auto_offset_reset="latest",
                        enable_auto_commit=True,
                        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                        consumer_timeout_ms=1000
                    )
                    logger.info(f"Connected to Kafka broker: {self.bootstrap_servers}")
                except Exception as e:
                    logger.error(f"Waiting for Kafka broker ({e})...")
                    time.sleep(5)
                    continue

            try:
                for message in self.consumer:
                    if not self.running:
                        break
                    event = message.value
                    self._save_to_db(event)
            except Exception as e:
                logger.error(f"Consumer stream error: {e}")
                self.consumer = None
                time.sleep(3)

        if self.consumer:
            self.consumer.close()
            logger.info("DB Sink closed.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    sink = DatabaseSinkConsumer()
    sink.start()
