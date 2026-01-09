"""
🕉️ Karma Dev's AI Trading System
Main entry point for running trading agents
"""

import os
import sys
from termcolor import cprint
from dotenv import load_dotenv
import time
from datetime import datetime, timedelta
from src import config
from src.config import *

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Import agents
from src.agents.trading_agent import TradingAgent
from src.agents.risk_agent import RiskAgent
from src.agents.strategy_agent import StrategyAgent
from src.agents.copybot_agent import CopyBotAgent
from src.agents.sentiment_agent import SentimentAgent

# Import WebSocket infrastructure
try:
    from src.websocket import (
        start_websocket_feeds,
        stop_websocket_feeds,
        is_websocket_enabled,
        get_data_manager
    )
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    def start_websocket_feeds(*args, **kwargs): pass
    def stop_websocket_feeds(*args, **kwargs): pass
    def is_websocket_enabled(): return False
    def get_data_manager(): return None

# Load environment variables
load_dotenv()

# Agent Configuration
ACTIVE_AGENTS = {
    'risk': False,      # Risk management agent
    'trading': False,   # LLM trading agent
    'strategy': False,  # Strategy-based trading agent
    'copybot': False,   # CopyBot agent
    'sentiment': False, # Run sentiment_agent.py directly instead
    # whale_agent is run from whale_agent.py
    # Add more agents here as we build them:
    # 'portfolio': False,  # Future portfolio optimization agent
}

def run_agents():
    """Run all active agents in sequence"""
    try:
        # 🚀 WebSocket Startup (ONCE, early in the execution flow)
        if WEBSOCKET_AVAILABLE and EXCHANGE == 'hyperliquid':
            try:
                cprint("\n🔌 Starting WebSocket feeds...", "cyan")
                start_websocket_feeds()

                if is_websocket_enabled():
                    cprint("🟢 WebSocket feeds started successfully", "green")

                    # Subscribe to user state for real-time account updates
                    try:
                        from eth_account import Account as EthAccount
                        private_key = os.getenv('HYPER_LIQUID_ETH_PRIVATE_KEY')
                        if private_key:
                            clean_key = private_key.strip().replace('"', '').replace("'", "")
                            account = EthAccount.from_key(clean_key)
                            account_address = account.address

                            # Set the account address in environment for WebSocket
                            os.environ['ACCOUNT_ADDRESS'] = account_address
                            cprint(f"📍 User state feed active for: {account_address[:6]}...{account_address[-4:]}", "green")
                        else:
                            cprint("⚠️  HYPER_LIQUID_ETH_PRIVATE_KEY not found in .env", "yellow")
                    except Exception as e:
                        cprint(f"⚠️  User state setup failed: {e}", "yellow")
                else:
                    cprint("🟡 WebSocket feeds not enabled — using REST fallback", "yellow")
            except Exception as e:
                cprint(f"⚠️  WebSocket initialization failed: {e}", "red")

        # Initialize active agents
        trading_agent = TradingAgent() if ACTIVE_AGENTS['trading'] else None
        risk_agent = RiskAgent() if ACTIVE_AGENTS['risk'] else None
        strategy_agent = StrategyAgent() if ACTIVE_AGENTS['strategy'] else None
        copybot_agent = CopyBotAgent() if ACTIVE_AGENTS['copybot'] else None
        sentiment_agent = SentimentAgent() if ACTIVE_AGENTS['sentiment'] else None

        while True:
            try:
                # Run Risk Management
                if risk_agent:
                    cprint("\n🛡️ Running Risk Management...", "cyan")
                    risk_agent.run()

                # Run Trading Analysis
                if trading_agent:
                    cprint("\n📊 Running Trading Analysis...", "cyan")
                    trading_agent.run()

                # Run Strategy Analysis
                if strategy_agent:
                    cprint("\n📊 Running Strategy Analysis...", "cyan")
                    # Use get_active_tokens() to get the appropriate token list based on exchange
                    active_tokens = get_active_tokens()
                    for token in active_tokens:
                        if token not in EXCLUDED_TOKENS:  # Skip USDC and other excluded tokens
                            cprint(f"\n🔍 Analyzing {token}...", "cyan")
                            strategy_agent.get_signals(token)

                # Run CopyBot Analysis
                if copybot_agent:
                    cprint("\n📊 Running CopyBot Portfolio Analysis...", "cyan")
                    copybot_agent.run_analysis_cycle()

                # Run Sentiment Analysis
                if sentiment_agent:
                    cprint("\n🎭 Running Sentiment Analysis...", "cyan")
                    sentiment_agent.run()

                # Sleep until next cycle
                next_run = datetime.now() + timedelta(minutes=SLEEP_BETWEEN_RUNS_MINUTES)
                cprint(f"\n😴 Sleeping until {next_run.strftime('%H:%M:%S')}", "cyan")
                time.sleep(60 * SLEEP_BETWEEN_RUNS_MINUTES)

            except Exception as e:
                cprint(f"\n❌ Error running agents: {str(e)}", "red")
                cprint("🔄 Continuing to next cycle...", "yellow")
                time.sleep(60)  # Sleep for 1 minute on error before retrying

    except KeyboardInterrupt:
        cprint("\n👋 Gracefully shutting down...", "yellow")
        if WEBSOCKET_AVAILABLE:
            try:
                stop_websocket_feeds()
                cprint("🔌 WebSocket feeds stopped", "cyan")
            except Exception as e:
                cprint(f"⚠️  Error stopping WebSocket feeds: {e}", "yellow")
    except Exception as e:
        cprint(f"\n❌ Fatal error in main loop: {str(e)}", "red")
        if WEBSOCKET_AVAILABLE:
            try:
                stop_websocket_feeds()
            except Exception as cleanup_err:
                cprint(f"⚠️  Error stopping WebSocket feeds: {cleanup_err}", "yellow")
        raise

if __name__ == "__main__":
    cprint("\n🕉️ Karma Dev AI Agent Trading System Starting...", "white", "on_blue")
    cprint("\n📊 Active Agents:", "white", "on_blue")
    for agent, active in ACTIVE_AGENTS.items():
        status = "✅ ON" if active else "❌ OFF"
        cprint(f"  • {agent.title()}: {status}", "white", "on_blue")
    print("\n")

    run_agents()