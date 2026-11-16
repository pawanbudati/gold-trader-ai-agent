"""
Google Cloud Pub/Sub Publisher Module
Handles resilient message publishing to Google Cloud Pub/Sub topics with automatic retries
and Always-Free tier optimization.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger("PubSubPublisher")

try:
    from google.cloud import pubsub_v1
    from google.oauth2 import service_account
    PUBSUB_AVAILABLE = True
except ImportError:
    PUBSUB_AVAILABLE = False
    logger.warning("google-cloud-pubsub not installed. Events will log locally to console.")


def find_credentials_file(path_hint: Optional[str] = None) -> Optional[str]:
    """Finds the service account credentials JSON file across candidate locations."""
    candidates = []
    if path_hint:
        candidates.extend([
            path_hint,
            os.path.abspath(path_hint),
            os.path.join(os.getcwd(), path_hint),
            os.path.join("/opt/oci-gold-ai-agent", os.path.basename(path_hint))
        ])

    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.extend([
        os.path.join(repo_dir, "service_account.json"),
        os.path.join(os.getcwd(), "service_account.json"),
        "/opt/oci-gold-ai-agent/service_account.json",
        os.path.expanduser("~/oci-gold-ai-agent/service_account.json"),
        os.path.join(repo_dir, "gcp-pubsub-key.json"),
        os.path.join(os.getcwd(), "gcp-pubsub-key.json")
    ])

    for path in candidates:
        if path and os.path.isfile(path):
            return os.path.abspath(path)
    return None


class PubSubPublisher:
    def __init__(
        self,
        project_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        credentials_path: Optional[str] = None
    ):
        raw_creds = credentials_path or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        self.credentials_path = find_credentials_file(raw_creds)

        # Infer project_id from credentials JSON if not explicitly provided
        self.project_id = project_id or os.environ.get("GCP_PROJECT_ID")
        if not self.project_id and self.credentials_path:
            try:
                with open(self.credentials_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.project_id = data.get("project_id")
            except Exception as e:
                logger.debug(f"Could not parse project_id from credentials file: {e}")

        # Default fallback to user's configured project and topic
        self.project_id = self.project_id or "fourth-arena-460820-s6"
        self.topic_id = topic_id or os.environ.get("PUBSUB_TOPIC_ID", "gold-trading-signals-agent-001")

        self.publisher: Optional[pubsub_v1.PublisherClient] = None
        self.topic_path: Optional[str] = None
        self._connect()

    def _connect(self):
        if not PUBSUB_AVAILABLE:
            return

        try:
            logger.info(f"Initializing Google Cloud Pub/Sub publisher for project '{self.project_id}'...")

            # Load credentials if found
            if self.credentials_path and os.path.isfile(self.credentials_path):
                logger.info(f"Loading service account credentials from: {self.credentials_path}")
                credentials = service_account.Credentials.from_service_account_file(self.credentials_path)
                self.publisher = pubsub_v1.PublisherClient(credentials=credentials)
            else:
                logger.info("Using Application Default Credentials (ADC)...")
                self.publisher = pubsub_v1.PublisherClient()

            self.topic_path = self.publisher.topic_path(self.project_id, self.topic_id)
            logger.info(f"Connected to Google Pub/Sub! Target Topic: {self.topic_path}")

        except Exception as e:
            logger.error(f"Google Pub/Sub initialization failure: {e}")
            self.publisher = None
            self.topic_path = None

    def publish_event(self, event_type: str, payload: Dict[str, Any], key: str = "XAUUSD") -> bool:
        """Publishes a structured event message to the Google Pub/Sub topic."""
        event = {
            "event_type": event_type,
            "agent_id": "oci-gold-ai-agent-v1",
            "published_at_utc": datetime.now(timezone.utc).isoformat(),
            "payload": payload
        }

        logger.info(f"📢 [PUBSUB EVENT: {event_type}] {payload.get('summary', '')}")

        if self.publisher and self.topic_path:
            try:
                data = json.dumps(event, default=str).encode("utf-8")
                # Pub/Sub attributes allow downstream subscribers to filter without parsing entire body
                future = self.publisher.publish(
                    self.topic_path,
                    data,
                    event_type=event_type,
                    symbol=str(payload.get("symbol", key))
                )
                message_id = future.result(timeout=10.0)
                logger.info(f"Successfully published {event_type} to Pub/Sub (Message ID: {message_id})")
                return True
            except Exception as e:
                logger.error(f"Google Pub/Sub publish error: {e}")
                return False
        else:
            logger.warning("Pub/Sub publisher not initialized. Event logged locally.")
            return False
