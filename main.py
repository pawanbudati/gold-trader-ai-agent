"""
Entry point for the Autonomous OCI AI Gold Trading Agent.
Usage:
  python main.py
"""

from src.agent import AutonomousGoldAgent

if __name__ == "__main__":
    agent = AutonomousGoldAgent()
    agent.start()
