"""
CLI Entrypoint for the OCI Kafka-to-Database Sink
Usage:
  python run_db_sink.py
  python run_db_sink.py --servers 10.0.0.15:9092 --topic gold-trading-signals
"""

import sys
import argparse
import logging
from src.db_sink import DatabaseSinkConsumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

def main():
    parser = argparse.ArgumentParser(description="OCI Kafka-to-Database Sink Daemon")
    parser.add_argument("--servers", type=str, default=None, help="Kafka Bootstrap Servers (e.g. 10.0.0.15:9092)")
    parser.add_argument("--topic", type=str, default=None, help="Kafka Topic to persist (default: gold-trading-signals)")
    parser.add_argument("--db-url", type=str, default=None, help="Database Connection URL (default: sqlite:///data/gold_trading.db)")
    parser.add_argument("--group", type=str, default="oci-db-sink-group", help="Kafka Consumer Group ID")

    args = parser.parse_args()

    sink = DatabaseSinkConsumer(
        bootstrap_servers=args.servers,
        topic=args.topic,
        database_url=args.db_url,
        group_id=args.group
    )

    try:
        sink.start()
    except KeyboardInterrupt:
        print("\nDB Sink stopped by user.")
        sys.exit(0)

if __name__ == "__main__":
    main()
