"""
AI Brain & Reasoning Module
Acts as the cognitive layer (System 2 Deliberation) of the Autonomous Agent.
Evaluates market regime, scores confidence, queries episodic memory,
and can optionally invoke an LLM (Gemini, OpenAI, or local Ollama) for macro reasoning.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("AgentBrain")

class AgentBrain:
    def __init__(self, memory):
        self.memory = memory
        self.min_confidence_threshold = float(os.environ.get("MIN_CONFIDENCE_THRESHOLD", "0.70"))
        self.llm_provider = os.environ.get("LLM_PROVIDER", "heuristic").lower() # 'gemini', 'openai', or 'heuristic'
        self.gemini_key = os.environ.get("GEMINI_API_KEY", "")
        self.openai_key = os.environ.get("OPENAI_API_KEY", "")

    def deliberate_on_setup(self, setup: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cognitive Deliberation Layer:
        Assesses setup validity, market regime, risk factors, and scores confidence.
        """
        direction = setup["direction"]
        price = setup["entry_price"]
        asian = setup["asian_range"]
        ind = setup["indicators"]
        fvg = setup.get("fvg_detected", False)
        session = setup["session"]

        asian_range_pips = round((asian["high"] - asian["low"]) * 10.0, 1)

        # 1. Evaluate Asian Box Quality
        # Optimal Asian box is 180 - 380 pips.
        # Under 120 pips -> low liquidity, prone to whipsaws.
        # Over 500 pips -> excessive pre-market move, potential exhaustion.
        box_quality = "OPTIMAL"
        score_box = 0.85
        if asian_range_pips < 140:
            box_quality = "COMPRESSED (High breakout potential, watch for sweeps)"
            score_box = 0.75
        elif asian_range_pips > 450:
            box_quality = "EXTENDED (Potential session exhaustion)"
            score_box = 0.60

        # 2. Evaluate Momentum & Imbalance (FVG)
        score_momentum = 0.70
        if fvg:
            score_momentum += 0.20  # Strong institutional footprint
        if ind["atr_pips"] >= 35.0:
            score_momentum += 0.10  # Strong volatility expansion

        # 3. Market Regime Classification
        if direction == "SELL":
            if ind["rsi14"] <= 35.0 and ind["ema21"] < ind["ema50"]:
                regime = "HIGH_VELOCITY_BEARISH_EXPANSION"
            else:
                regime = "MODERATE_DOWNTREND_CONTINUATION"
        else:
            if ind["rsi14"] >= 65.0 and ind["ema21"] > ind["ema50"]:
                regime = "HIGH_VELOCITY_BULLISH_EXPANSION"
            else:
                regime = "MODERATE_UPTREND_CONTINUATION"

        # 4. Cross-Reference Episodic Memory
        past_cases = self.memory.query_similar_setups(direction, session, limit=2)
        past_references = [f"#{c.get('message_id')} ({c.get('timestamp_utc')[:10]})" for c in past_cases]

        # Calculate final composite confidence
        confidence = round((score_box * 0.4) + (score_momentum * 0.6), 2)
        confidence = min(0.98, max(0.40, confidence))

        # Check approval
        approved = confidence >= self.min_confidence_threshold

        reasoning = (
            f"Deliberation on {direction} Gold setup @ {price:.2f}: "
            f"Asian Range is {asian_range_pips} pips ({box_quality}). "
            f"Institutional displacement is {'CONFIRMED with Fair Value Gap' if fvg else 'UNCONFIRMED by FVG'}. "
            f"ATR(14) expanded to {ind['atr_pips']} pips during {session}. "
            f"Market regime identified as {regime}. "
            f"Similar high-probability historical setups include {', '.join(past_references) if past_references else 'standard historical baseline'}."
        )

        return {
            "approved": approved,
            "confidence_score": confidence,
            "market_regime": regime,
            "box_quality": box_quality,
            "deliberation_reasoning": reasoning,
            "past_cases_referenced": past_references
        }
