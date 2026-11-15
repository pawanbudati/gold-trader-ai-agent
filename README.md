# Autonomous OCI AI Gold Trading Agent
### Real-Time SMC Liquidity Breakout Engine with Cognitive Deliberation & Kafka Dispatch

An autonomous, multi-layered AI trading agent engineered for deployment on **Oracle Cloud Infrastructure (OCI) VMs**. The agent ingests live Gold (`XAUUSD`) tick and candlestick feeds, screens high-probability institutional Smart Money Concepts (SMC) breakouts, deliberates on market regime and risk confidence, and streams real-time trade signals and active management events directly to your OCI Kafka cluster.

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
| **Event Distribution** | Terminal prints or basic webhook | **Production Kafka Streaming**: Streams structured JSON signals, auto-breakeven updates, and heartbeats |

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
                        [ ACTION: KAFKA ]
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
├── requirements.txt               # Minimal runtime dependencies
├── .env.example                   # Kafka, Asset, and AI configuration template
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
│   └── kafka_producer.py          # Resilient Kafka Publisher with automatic retries
│
├── tests/
│   ├── __init__.py
│   └── test_kafka_consumer.py     # Downstream Kafka listener to verify live events
│
└── data/
    ├── historical_signals.json    # 69 reverse-engineered trade setups from @intradaybulls009
    └── strategy_report.json       # Macro statistical report (July 1 - Nov 15, 2026)
```

---

## 4. Kafka Event Schemas

Whenever the AI Agent executes an action or detects an event, it publishes a JSON payload to your Kafka cluster:

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

## 5. Deployment on Oracle Cloud Infrastructure (OCI)

### Automated CI/CD Deployment via GitHub Actions (Recommended)
Every time you push to `main` (or click **Run Workflow** in GitHub Actions), the workflow automatically copies updated code to your OCI VM and restarts the AI Agent container.

#### 1. Add Secrets to Your GitHub Repository
Go to your repository on GitHub: **Settings $\rightarrow$ Secrets and variables $\rightarrow$ Actions $\rightarrow$ New repository secret**, and add:

| Secret Name | Value |
| :--- | :--- |
| `OCI_VM_HOST` | Public IP address of your OCI VM (e.g., `140.238.xxx.xxx`) |
| `OCI_VM_USER` | SSH username (`opc` for Oracle Linux, `ubuntu` for Ubuntu) |
| `OCI_SSH_KEY` | Your private SSH key (contents of `id_rsa` or `id_ed25519` used for OCI) |
| `OCI_VM_PORT` | *(Optional, defaults to 22)* SSH Port |

Once added, every `git push origin main` will automatically build and restart your AI Agent on your OCI VM!

---

### Manual Deployment on OCI

### Prerequisites on OCI
- 1 Compute Instance (VM.Standard.E4.Flex or VM.Standard.A1.Flex Always Free).
- Network Security Group (NSG) / Ingress rules permitting port `9092` between your Agent VM and Kafka VM.

### Option A: 1-Command Docker Deployment (Manual)

1. SSH into your OCI VM:
   ```bash
   ssh -i ~/.ssh/id_rsa opc@<YOUR_OCI_VM_IP>
   ```
2. Copy this project folder to the VM and navigate into it:
   ```bash
   cd ~/oci-gold-ai-agent
   ```
3. Configure your Kafka IP in `.env`:
   ```bash
   cp .env.example .env
   nano .env
   ```
   *Set `KAFKA_BOOTSTRAP_SERVERS` to your Kafka VM's private IP (e.g. `10.0.0.15:9092`).*
4. Start the container in background:
   ```bash
   docker-compose up -d --build
   ```
5. View streaming logs:
   ```bash
   docker-compose logs -f
   ```

---

### Option B: Native Linux Systemd Service (Ubuntu / Oracle Linux)

1. Run the automated installer:
   ```bash
   chmod +x deploy_oci.sh
   ./deploy_oci.sh
   ```
2. Check service health:
   ```bash
   sudo systemctl status gold-agent
   ```
3. Follow live streaming logs:
   ```bash
   sudo journalctl -u gold-agent -f
   ```

---

## 6. Verifying Kafka Signal Receipt

To verify that trade signals, heartbeats, and updates are being received by your Kafka cluster, run the consumer test:

```bash
python tests/test_kafka_consumer.py
```

---

## 7. Strategy Reference (Empirical Findings from 69 Signals)

- **Stop Loss**: 150 Pips ($15.00/oz)
- **Target 1**: 110 – 140 Pips ($11.00 – $14.00/oz)
- **Target 2**: 250 – 360 Pips ($25.00 – $36.00/oz)
- **Primary Killzone**: 06:30 – 09:30 UTC (12:00 – 15:00 IST) — London Open.
- **Secondary Killzone**: 03:30 – 05:00 UTC (09:00 – 10:30 IST) — Late Tokyo.
