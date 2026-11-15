"""
Test Kafka Consumer for OCI Gold Trading Signals
Run this script to verify real-time messages published to your Kafka topic.
"""

import os
import sys
import json
from datetime import datetime

try:
    from kafka import KafkaConsumer
except ImportError:
    print("Please install kafka-python-ng: pip install kafka-python-ng")
    sys.exit(1)

KAFKA_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC", "gold-trading-signals")

print("=" * 80)
print("🎧 LISTENING FOR OCI GOLD TRADING SIGNALS VIA KAFKA")
print(f"Server: {KAFKA_SERVERS} | Topic: {KAFKA_TOPIC}")
print("=" * 80)

consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_SERVERS.split(","),
    auto_offset_reset="latest",
    enable_auto_commit=True,
    value_deserializer=lambda m: json.loads(m.decode("utf-8"))
)

for message in consumer:
    payload = message.value
    event_type = payload.get("event_type", "UNKNOWN")
    data = payload.get("payload", {})
    published_at = payload.get("published_at_utc", "")

    print(f"\n📩 [{published_at}] EVENT: {event_type}")
    if event_type == "TRADE_SIGNAL":
        print(f"🚨 ACTION:     {data.get('direction')} {data.get('symbol')}")
        print(f"   ENTRY:      ${data.get('entry_price')}")
        print(f"   SL:         ${data.get('sl')} ({data.get('sl_pips')} pips)")
        print(f"   TP1:        ${data.get('tp1')} ({data.get('tp1_pips')} pips)")
        print(f"   TP2:        ${data.get('tp2')} ({data.get('tp2_pips')} pips)")
        print(f"   CONFIDENCE: {data.get('confidence_score') * 100}%")
        print(f"   REGIME:     {data.get('market_regime')}")
        print(f"   REASONING:  {data.get('reasoning')}")
    elif event_type == "TRADE_UPDATE":
        print(f"📢 UPDATE:     {data.get('summary')}")
        print(f"   ACTION:     {data.get('action')}")
    elif event_type == "HEARTBEAT":
        print(f"💓 STATUS:     {data.get('summary')}")
    else:
        print(f"ℹ️  DETAILS:    {json.dumps(data, indent=2)}")
