"""
Kafka Publisher Module
Handles resilient message publishing to OCI Kafka clusters with automatic retries.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger("KafkaPublisher")

try:
    from kafka import KafkaProducer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.warning("kafka-python-ng not installed. Events will log to console.")

class KafkaPublisher:
    def __init__(self, bootstrap_servers: str, topic: str):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.producer: Optional[KafkaProducer] = None
        self._connect()

    def _connect(self):
        if not KAFKA_AVAILABLE:
            return
        try:
            logger.info(f"Connecting to Kafka at {self.bootstrap_servers}...")
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers.split(","),
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: str(k).encode("utf-8") if k else None,
                retries=5,
                acks="all",
                request_timeout_ms=10000
            )
            logger.info(f"Connected to Kafka! Publishing on topic '{self.topic}'")
        except Exception as e:
            logger.error(f"Kafka connection failure: {e}")
            self.producer = None

    def publish_event(self, event_type: str, payload: Dict[str, Any], key: str = "XAUUSD") -> bool:
        """Publishes a structured event message to the Kafka topic."""
        event = {
            "event_type": event_type,
            "agent_id": "oci-gold-ai-agent-v1",
            "published_at_utc": datetime.now(timezone.utc).isoformat(),
            "payload": payload
        }

        logger.info(f"📢 [KAFKA EVENT: {event_type}] {payload.get('summary', '')}")

        if self.producer:
            try:
                self.producer.send(self.topic, key=key, value=event)
                self.producer.flush(timeout=5)
                logger.info(f"Successfully published {event_type} to Kafka '{self.topic}'")
                return True
            except Exception as e:
                logger.error(f"Kafka send error: {e}")
                self._connect()
                return False
        else:
            logger.warning("Kafka producer unavailable. Event output logged locally.")
            return False
