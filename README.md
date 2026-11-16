# Autonomous OCI AI Gold Trading Agent
### Real-Time SMC Liquidity Breakout Engine with Cognitive Deliberation & Google Cloud Pub/Sub Streaming

An autonomous, multi-layered AI trading agent engineered for deployment on **Oracle Cloud Infrastructure (OCI) VMs**. The agent ingests live Gold (`XAUUSD`) tick and candlestick feeds, screens high-probability institutional Smart Money Concepts (SMC) breakouts, deliberates on market regime and risk confidence, and streams real-time trade signals and active management events directly to **Google Cloud Pub/Sub** (configured under Google's 100% **Always Free** tier).

---

## 1. Why This is an AI Agent vs Basic Python Code

A basic algorithmic script uses rigid, hardcoded rules (`if price < low: sell()`), making it fragile to market shifts, pre-market noise, and news fakeouts.

This project implements a **True Cognitive AI Agent** following the **Perception $\rightarrow$ Reasoning $\rightarrow$ Action $\rightarrow$ Memory** loop:

| Dimension | Basic Trading Script | Autonomous OCI AI Agent |
| :--- | :--- | :--- |
| **Cognitive Architecture** | Single-layer `if/else` | **Dual-System Thinking** (System 1 Fast Quant Screen + System 2 Cognitive Brain) |
| **Deliberation Layer** | None (fires blindly on price breach) | **Pre-Trade Deliberation**: Evaluates Asian box quality, volatility expansion, and assigns a **Confidence Score (0–100%)** |
| **Market Regime Awareness** | None (treats all candles identically) | **Regime Classification**: Identifies `HIGH_VELOCITY_EXPANSION` vs `CHOPPY_REVERSION` |
| **Episodic Memory** | Zero memory of past trades | Cross-references proposed setups against **69 historical trade cases** in `AgentMemory` |
| **Capital Defense Mechanism** | Static stop loss | **Active 15-Minute Stagnation Cut**: Automatically exits at -50 pips if momentum stalls, saving 100 pips of capital |
| **Event Distribution** | Terminal prints or fragile webhooks | **Google Cloud Pub/Sub (Always Free)**: Serverless, highly resilient event streaming (10 GB/month free tier, 0 server maintenance) |

---

## 2. Cognitive Agent Architecture

```
                                [ PERCEPTION ]
                         Live Gold Feed (PAXGUSDT / XAUUSD)
                                       │
                                       ▼
                   [ SYSTEM 1: QUANTITATIVE SMC SCREENER ]
                   • Asian Range Box (00:00 - 06:00 UTC)
                   • London / Asian Session Killzone Timing
                   • M5 Fair Value Gap (FVG) Detection
                   • ATR(14) > 28 Pips & EMA 21/50 Trend
                                       │ Candidate Setup
                                       ▼
                   [ SYSTEM 2: AI BRAIN & DELIBERATION ]
                   • Evaluates Asian Box Compression vs Extension
                   • Queries Episodic Memory (Historical Case Base)
                   • Classifies Market Regime
                   • Calculates Composite Confidence Score (0–100%)
                                       │
                         Confidence >= 70% ?
                                ┌──────┴──────┐
                                │ YES         │ NO
                                ▼             ▼
                     [ APPROVED & DISPATCHED ] [ DISCARDED / LOGGED ]
                                │
                                ▼
                   [ ACTION: GOOGLE CLOUD PUB/SUB ]
                     Topic: gold-trading-signals
                     • Event: TRADE_SIGNAL
                     • Event: TP1_HIT_BREAKEVEN_LOCKED
                     • Event: EARLY_INVALIDATION_CUT
                     • Event: HEARTBEAT
```

---

## 3. Project Directory Structure

```
oci-gold-ai-agent/
├── README.md                      # Complete architecture & deployment guide
├── requirements.txt               # Dependencies (google-cloud-pubsub, urllib3)
├── .env.example                   # Pub/Sub, Asset, and AI configuration template
├── main.py                        # Clean runtime entrypoint
├── Dockerfile                     # Production container image
├── docker-compose.yml             # Single-command Docker deployment
├── deploy_oci.sh                  # Automated bash installer for OCI VMs
├── gold-agent.service             # Systemd service unit for native Linux daemons
│
├── src/                           # Core Agent Source Code
│   ├── __init__.py
│   ├── agent.py                   # Main Agent Orchestrator (Lifecycle & Loop)
│   ├── brain.py                   # System 2 Cognitive Reasoning & Confidence Scoring
│   ├── memory.py                  # Episodic Memory holding historical trade knowledge
│   ├── strategy_engine.py         # SMC Asian Box, FVGs, EMAs, ATR quantitative scanner
│   ├── market_feed.py             # Live Gold Market Data Ingestor (WebSockets & REST)
│   └── pubsub_publisher.py        # Resilient Google Pub/Sub Publisher (Always Free)
│
├── tests/
│   ├── __init__.py
│   └── test_pubsub_subscriber.py  # Downstream Pub/Sub listener to verify live events
│
└── data/
    ├── historical_signals.json    # 69 reverse-engineered trade setups from @intradaybulls009
    └── strategy_report.json       # Macro statistical report (July 1 - Nov 15, 2026)
```

---

## 4. Google Cloud Pub/Sub Always Free Tier Setup

Google Cloud provides an **Always Free tier of 10 GiB of message ingestion and delivery per month** for standard Pub/Sub. Since gold trading signals and heartbeats consume only a few kilobytes per day, this setup is completely **$0.00/month**.

### Step 1: Create or Select a GCP Project
1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g. `gold-trading-agent`) or select an existing project.
3. Note your **Project ID** (e.g., `gold-trading-agent-412304`).

### Step 2: Enable the Pub/Sub API
- In the Cloud Console search bar, type **Cloud Pub/Sub API** and click **Enable** (or run `gcloud services enable pubsub.googleapis.com`).

### Step 3: Create the Pub/Sub Topic (Always Free Config)
1. In Cloud Console, navigate to **Pub/Sub $\rightarrow$ Topics**.
2. Click **Create Topic**.
3. **Topic ID**: `gold-trading-signals`
4. **Configuration (Ensure Always Free)**:
   - **Check** "Add a default subscription" (named `gold-trading-signals-sub`).
   - **Encryption**: Select **Google-managed encryption key** (Default, $0). *Do not select Customer-Managed Encryption Key (CMEK), which charges for KMS keys.*
   - **Message Retention**: Leave unchecked / default.
   - **Schema**: Leave unchecked (None).
5. Click **Create**.

### Step 4: Create a Service Account & JSON Key
To allow your OCI VM to authenticate securely with Google Cloud Pub/Sub:
1. Navigate to **IAM & Admin $\rightarrow$ Service Accounts**.
2. Click **Create Service Account**:
   - **Service account name**: `gold-agent-pubsub-sa`
   - Click **Create and Continue**.
3. **Grant Access**:
   - Role 1: **Pub/Sub Publisher** (`roles/pubsub.publisher`)
   - Role 2: *(Optional, for testing)* **Pub/Sub Subscriber** (`roles/pubsub.subscriber`)
   - Click **Continue** $\rightarrow$ **Done**.
4. Click on your newly created service account $\rightarrow$ Go to the **Keys** tab.
5. Click **Add Key $\rightarrow$ Create new key $\rightarrow$ JSON**.
6. Download the JSON key file and rename it to `service_account.json`. Keep this file secure (it is git-ignored).

---

## 5. Pub/Sub Event Schemas

Whenever the AI Agent executes an action or detects an event, it publishes a JSON payload to Google Cloud Pub/Sub:

### A. Primary Trade Signal (`TRADE_SIGNAL`)
```json
{
  "event_type": "TRADE_SIGNAL",
  "agent_id": "oci-gold-ai-agent-v1",
  "published_at_utc": "2026-11-12T06:55:35+00:00",
  "payload": {
    "symbol": "XAUUSD",
    "direction": "SELL",
    "entry_price": 3966.0,
    "sl": 3981.0,
    "tp1": 3955.0,
    "tp2": 3940.0,
    "sl_pips": 150.0,
    "tp1_pips": 110.0,
    "tp2_pips": 260.0,
    "session": "London Open Killzone",
    "confidence_score": 0.88,
    "market_regime": "HIGH_VELOCITY_BEARISH_EXPANSION",
    "box_quality": "OPTIMAL",
    "reasoning": "Deliberation on SELL Gold setup @ 3966.00: Asian Range is 228.0 pips (OPTIMAL). Institutional displacement is CONFIRMED with Fair Value Gap. ATR(14) expanded to 43.9 pips during London Open Killzone. Market regime identified as HIGH_VELOCITY_BEARISH_EXPANSION.",
    "timestamp_utc": "2026-11-12T06:55:35+00:00",
    "timestamp_ist": "2026-11-12T12:25:35+05:30",
    "summary": "SELL XAUUSD @ 3966.0 | SL: 3981.0 | TP1: 3955.0 | TP2: 3940.0 (Confidence: 88%)"
  }
}
```

### B. In-Trade Management Updates (`TRADE_UPDATE`)
- **`TP1_HIT_BREAKEVEN_LOCKED`**: Fired at +110 pips profit $\rightarrow$ Instructs downstream execution to close 50% lot size and move Stop Loss to Breakeven (0 risk).
- **`TP2_HIT_TARGET_REACHED`**: Fired at +260 pips profit $\rightarrow$ Instructs to bank final runner.
- **`EARLY_INVALIDATION_CUT`**: Fired if trade drops to -50 pips after 15 mins $\rightarrow$ Manual capital defense cut.

---

## 6. Deployment on Oracle Cloud Infrastructure (OCI)

### Automated CI/CD Deployment via GitHub Actions
Every time you push to `main` (or trigger **Run workflow**), GitHub Actions automatically copies updated code to your OCI VM, writes your `service_account.json` key securely from secrets, configures `.env`, and restarts the AI Agent.

#### 1. Add Secrets to Your GitHub Repository
Go to your repository on GitHub: **Settings $\rightarrow$ Secrets and variables $\rightarrow$ Actions $\rightarrow$ New repository secret**, and add:

| Secret Name | Value | Description |
| :--- | :--- | :--- |
| `GCP_PUBSUB_KEY` | Entire contents of `gcp-pubsub-key.json` | Used to authenticate with Google Cloud Pub/Sub from OCI |
| `OCI_VM_HOST` | Public IP address of your OCI VM (e.g. `140.238.xxx.xxx`) | Target VM host |
| `OCI_VM_USER` | SSH username (`opc` for Oracle Linux, `ubuntu` for Ubuntu) | VM login user |
| `OCI_SSH_KEY` | Your private SSH key (contents of `id_rsa` or `id_ed25519`) | SSH authentication |
| `OCI_VM_PORT` | *(Optional, defaults to 22)* | SSH Port |

---

### Verifying on OCI: Publishing & Subscribing

Once deployed on your OCI VM:

1. **Watch Live Agent Signals & Logs (Publisher)**:
   ```bash
   # If running via systemd:
   sudo journalctl -u gold-agent -f

   # If running via Docker:
   docker-compose logs -f
   ```

2. **Subscribe to Live Signals on OCI (Subscriber)**:
   You can run the listener directly on your OCI instance to monitor messages arriving in real time:
   ```bash
   # From ~/oci-gold-ai-agent:
   python listen.py
   # Or using the virtual environment:
   ./venv/bin/python listen.py
   ```

---

### Manual Deployment on OCI

1. SSH into your OCI VM:
   ```bash
   ssh -i ~/.ssh/id_rsa opc@<YOUR_OCI_VM_IP>
   ```
2. Navigate to the project directory:
   ```bash
   cd ~/oci-gold-ai-agent
   ```
3. Copy `service_account.json` to the VM:
   ```bash
   # From your local machine:
   scp -i ~/.ssh/id_rsa service_account.json opc@<YOUR_OCI_VM_IP>:~/oci-gold-ai-agent/service_account.json
   ```
4. Configure `.env`:
   ```bash
   cp .env.example .env
   nano .env
   ```
   *Set `GCP_PROJECT_ID` to your Google Cloud Project ID and `GOOGLE_APPLICATION_CREDENTIALS` to `service_account.json`.*

5. Run via systemd daemon:
   ```bash
   chmod +x deploy_oci.sh
   ./deploy_oci.sh
   ```
   Or run via Docker:
   ```bash
   docker-compose up -d --build
   ```

---

## 7. Verifying Pub/Sub Signal Receipt

To verify that trade signals, heartbeats, and updates are arriving in Google Cloud Pub/Sub, run the subscriber test:

```bash
# Set your environment variables
export GCP_PROJECT_ID="your-gcp-project-id"
export PUBSUB_SUBSCRIPTION_ID="gold-trading-signals-sub"
export GOOGLE_APPLICATION_CREDENTIALS="service_account.json"

# Run subscriber
python tests/test_pubsub_subscriber.py
```

---

## 8. Strategy Reference (Empirical Findings from 69 Signals)

- **Stop Loss**: 150 Pips ($15.00/oz)
- **Target 1**: 110 – 140 Pips ($11.00 – $14.00/oz)
- **Target 2**: 250 – 360 Pips ($25.00 – $36.00/oz)
- **Primary Killzone**: 06:30 – 09:30 UTC (12:00 – 15:00 IST) — London Open.
- **Secondary Killzone**: 03:30 – 05:00 UTC (09:00 – 10:30 IST) — Late Tokyo.
