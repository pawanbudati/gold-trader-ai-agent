"""
Test Google Cloud Pub/Sub Subscriber for OCI Gold Trading Signals
Run this script on your local machine or OCI VM to verify real-time messages received by your Google Pub/Sub subscription.
"""

import os
import sys
import json
import logging
from typing import Optional

# Add parent directory to path to import publisher helper
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PubSubTestSubscriber")

try:
    from google.cloud import pubsub_v1
    from google.oauth2 import service_account
except ImportError:
    print("Please install google-cloud-pubsub: pip install google-cloud-pubsub")
    sys.exit(1)

from src.pubsub_publisher import find_credentials_file

CREDENTIALS_PATH = find_credentials_file(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

# Infer Project ID from credentials file if available
PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
if not PROJECT_ID and CREDENTIALS_PATH:
    try:
        with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
            PROJECT_ID = json.load(f).get("project_id")
    except Exception:
        pass

PROJECT_ID = PROJECT_ID or "fourth-arena-460820-s6"
SUBSCRIPTION_ID = os.environ.get("PUBSUB_SUBSCRIPTION_ID", "gold-trading-signals-agent-001-sub-001")

print("=" * 80)
print("🎧 LISTENING FOR OCI GOLD TRADING SIGNALS VIA GOOGLE PUB/SUB")
print(f"Project ID:      {PROJECT_ID}")
print(f"Subscription ID: {SUBSCRIPTION_ID}")
print(f"Credentials:     {CREDENTIALS_PATH or 'ADC / Environment Default'}")
print("=" * 80)

if CREDENTIALS_PATH and os.path.isfile(CREDENTIALS_PATH):
    credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
    subscriber = pubsub_v1.SubscriberClient(credentials=credentials)
else:
    subscriber = pubsub_v1.SubscriberClient()

subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)

def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    try:
        data_str = message.data.decode("utf-8")
        payload = json.loads(data_str)
        event_type = payload.get("event_type", "UNKNOWN")
        data = payload.get("payload", {})
        published_at = payload.get("published_at_utc", "")

        print(f"\n📩 [{published_at}] PUBSUB EVENT: {event_type} (MsgID: {message.message_id})")
        if message.attributes:
            print(f"   Attributes: {dict(message.attributes)}")

        if event_type == "TRADE_SIGNAL":
            print(f"🚨 ACTION:     {data.get('direction')} {data.get('symbol')}")
            print(f"   ENTRY:      ${data.get('entry_price')}")
            print(f"   SL:         ${data.get('sl')} ({data.get('sl_pips')} pips)")
            print(f"   TP1:        ${data.get('tp1')} ({data.get('tp1_pips')} pips)")
            print(f"   TP2:        ${data.get('tp2')} ({data.get('tp2_pips')} pips)")
            print(f"   CONFIDENCE: {data.get('confidence_score', 0) * 100}%")
            print(f"   REGIME:     {data.get('market_regime')}")
            print(f"   REASONING:  {data.get('reasoning')}")
        elif event_type == "TRADE_UPDATE":
            print(f"📢 UPDATE:     {data.get('summary')}")
            print(f"   ACTION:     {data.get('action')}")
        elif event_type == "HEARTBEAT":
            print(f"💓 STATUS:     {data.get('summary')}")
        elif event_type == "AGENT_STATUS":
            print(f"🤖 STATUS:     {data.get('status')} - {data.get('message')}")
        else:
            print(f"ℹ️  DETAILS:    {json.dumps(data, indent=2)}")

        # Acknowledge receipt so Pub/Sub does not redeliver
        message.ack()
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        message.nack()

streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
print(f"Waiting for messages on {subscription_path} (Press Ctrl+C to stop)...")

try:
    streaming_pull_future.result()
except KeyboardInterrupt:
    streaming_pull_future.cancel()
    streaming_pull_future.result()
    print("\nSubscriber stopped.")
except Exception as e:
    streaming_pull_future.cancel()
    logger.error(f"Subscriber error: {e}")
