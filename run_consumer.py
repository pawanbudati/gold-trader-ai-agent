"""
CLI Runner for the OCI Gold Signal Kafka Consumer
Usage:
  python run_consumer.py
  python run_consumer.py --servers 10.0.0.15:9092 --topic gold-trading-signals
  python run_consumer.py --from-beginning
"""

import sys
import argparse
import logging
from src.consumer import GoldSignalConsumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

def main():
    parser = argparse.ArgumentParser(description="Autonomous Gold AI Agent Kafka Consumer")
    parser.add_argument("--servers", type=str, default=None, help="Kafka Bootstrap Servers (e.g., localhost:9092 or 10.0.0.15:9092)")
    parser.add_argument("--topic", type=str, default=None, help="Kafka Topic to subscribe to (default: gold-trading-signals)")
    parser.add_argument("--group", type=str, default="gold-signal-consumers", help="Kafka Consumer Group ID")
    parser.add_argument("--from-beginning", action="store_true", help="Replay and read all messages from the beginning of the topic")

    args = parser.parse_args()

    offset_reset = "earliest" if args.from_beginning else "latest"

    consumer = GoldSignalConsumer(
        bootstrap_servers=args.servers,
        topic=args.topic,
        group_id=args.group,
        auto_offset_reset=offset_reset
    )
    
    try:
        consumer.start()
    except KeyboardInterrupt:
        print("\nConsumer stopped by user.")
        sys.exit(0)

if __name__ == "__main__":
    main()
