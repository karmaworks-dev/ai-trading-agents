# AI Trading Agents - Detailed Agent Guide

This document provides a comprehensive overview of the AI agents within the AI Trading Agents project. It details their functionalities, configurations, and usage.

## Core Agents

### 1. Trading Agent (`src/agents/trading_agent.py`)

- **Description**: The primary AI-driven trading agent responsible for analyzing market data, making trading decisions, and executing trades.
- **Functionality**:
  - Analyzes token data using AI models (Claude, GPT, Grok).
  - Makes buy/sell decisions based on AI analysis.
  - Manages portfolio allocation across different tokens.
  - Operates without hardcoded rules, relying solely on AI reasoning.
- **Configuration**:
  - `AI_MODEL_TYPE`: Specifies the AI provider (e.g., 'claude', 'openai', 'xai', 'groq').
  - `AI_MODEL_NAME`: Specifies the specific AI model to use (e.g., None for default).
- **Usage**:
  - Run directly: `python src/agents/trading_agent.py`
- **Key Functions**:
  - `analyze_market_data()`: Analyzes market data and determines trading action.
  - `allocate_portfolio()`: Allocates USD across different trading opportunities.
  - `execute_trades()`: Executes the AI-driven trading decisions.
- **Output**:
  - Saves trading decisions and logs to `src/data/trading_agent/[date]/`.

### 2. Swarm Agent (`src/agents/swarm_agent.py`)

- **Description**: A multi-model AI consensus system that queries multiple AI models in parallel to generate trading insights and decisions.
- **Functionality**:
  - Queries multiple AI models (Claude, GPT, Gemini, Grok, DeepSeek, Ollama) in parallel.
  - Returns individual responses from each AI model.
  - Generates an AI Consensus Summary (3-sentence synthesis by Claude).
- **Configuration**:
  - `SWARM_MODELS`: A dictionary that enables/disables models in the swarm.
  - `CONSENSUS_REVIEWER_MODEL`: Specifies the AI model used to synthesize the consensus summary.
  - `CONSENSUS_REVIEWER_PROMPT`: Customizes the prompt used for the consensus reviewer.
  - `DEFAULT_TEMPERATURE`: Adjusts the AI creativity (0.0-1.0).
  - `DEFAULT_MAX_TOKENS`: Sets the response length limit.
- **Usage**:
  - Run directly: `python src/agents/swarm_agent.py` (prompts for a query).
  - Import in other agents: `from src.agents.swarm_agent import SwarmAgent`
- **Response Structure**:
  - Includes a timestamp, the original prompt, a consensus summary, model mappings, individual model responses, and metadata.
- **Output**:
  - Saves all swarm queries to `src/data/swarm_agent/swarm_result_YYYYMMDD_HHMMSS.json`.

### 3. RBI Agent (`src/agents/rbi_agent_v3.py`)

- **Description**: An agent that automates the Research-Backtest-Implement (RBI) process for trading strategy development.
- **Functionality**:
  - Researches trading strategy ideas from various sources.
  - Creates backtest code using backtesting.py.
  - Packages the backtest code to resolve import/dependency issues.
  - Debugs the code to fix syntax and technical errors.
  - Executes backtests and captures results/errors.
  - Optimizes strategies based on backtest results.
- **Key Components**:
  - Research Agent: Generates strategy ideas.
  - Backtest Agent: Creates backtest code.
  - Package Agent: Fixes import/dependency issues.
  - Debug Agent: Fixes syntax and technical errors.
  - Execution Agent: Executes backtests in an isolated environment.
  - Optimization Agent: Analyzes backtest results and suggests improvements.
- **Workflow**:
  - Research → Backtest → Package → Debug → Execute → Optimize (iterative loop).

### 4. Risk Agent (`src/agents/risk_agent.py`)

- **Description**: An agent that manages risk by dynamically adjusting position sizes, setting stop losses, and taking profits.
- **Functionality**:
  - Calculates appropriate position sizes based on account balance and risk tolerance.
  - Sets stop loss and take profit levels based on market volatility and strategy.
  - Monitors open positions and adjusts risk parameters as needed.
- **Configuration**:
  - `CASH_PERCENTAGE`: Percentage of account balance to keep as cash reserve.
  - `MAX_POSITION_PERCENTAGE`: Maximum percentage of balance to allocate to a single position.
  - `STOP_LOSS_PERCENTAGE`: Percentage below entry price to set stop loss.
  - `TAKE_PROFIT_PERCENTAGE`: Percentage above entry price to set take profit.

### 5. Strategy Agent (`src/agents/strategy_agent.py`)

- **Description**: An agent that analyzes and optimizes trading strategies based on historical data and AI insights.
- **Functionality**:
  - Evaluates the performance of different trading strategies.
  - Identifies strengths and weaknesses of each strategy.
  - Suggests improvements to enhance strategy performance.
  - Integrates AI insights to refine strategy parameters.
- **Configuration**:
  - `ENABLE_STRATEGIES`: Enables or disables the use of trading strategies.
  - `STRATEGY_MIN_CONFIDENCE`: Minimum confidence threshold for strategy selection.

## Auxiliary Agents

### 1. Chart Analysis Agent (`src/agents/chartanalysis_agent.py`)

- **Description**: Analyzes trading charts and identifies patterns using AI.
- **Functionality**: Uses AI to interpret charts and indicators.

### 2. Chat Agent (`src/agents/chat_agent.py`)

- **Description**: Interactive AI assistant for market analysis via chat.
- **Functionality**: Provides market insights and answers user queries through a chat interface.

### 3. Compliance Agent (`src/agents/compliance_agent.py`)

- **Description**: Ensures trading activity complies with regulatory requirements.
- **Functionality**: Monitors trades for regulatory compliance.

### 4. Copybot Agent (`src/agents/copybot_agent.py`)

- **Description**: Copies trades from successful traders.
- **Functionality**: Replicates trades from specified wallets.

### 5. Funding Agent (`src/agents/funding_agent.py`)

- **Description**: Identifies funding rate arbitrage opportunities.
- **Functionality**: Monitors funding rates and identifies profitable arbitrage opportunities.

### 6. Giveaway Agent (`src/agents/giveaway_agent.py`)

- **Description**: Participates in token giveaways.
- **Functionality**: Automates participation in token giveaways.

### 7. Liquidation Agent (`src/agents/liquidation_agent.py`)

- **Description**: Capitalizes on liquidation events.
- **Functionality**: Identifies and trades liquidation clusters.

### 8. Listing Arb Agent (`src/agents/listingarb_agent.py`)

- **Description**: Exploits listing arbitrage opportunities.
- **Functionality**: Identifies price discrepancies after token listings.

### 9. New or Top Agent (`src/agents/new_or_top_agent.py`)

- **Description**: Monitors new and top-performing tokens.
- **Functionality**: Tracks newly listed and top-performing tokens.

### 10. Phone Agent (`src/agents/phone_agent.py`)

- **Description**: Provides trading updates via phone calls.
- **Functionality**: Delivers trading updates through phone calls.

### 11. Polymarket Agent (`src/agents/polymarket_agent.py`)

- **Description**: Trades on Polymarket prediction markets.
- **Functionality**: Automates trading on Polymarket.

### 12. Prompt Agent (`src/agents/prompt_agent.py`)

- **Description**: Generates and optimizes prompts for AI agents.
- **Functionality**: Creates and refines prompts for other agents.

### 13. Research Agent (`src/agents/research_agent.py`)

- **Description**: Conducts market research and gathers information.
- **Functionality**: Researches market trends and gathers data.

### 14. Scraper Agent (`src/agents/scraper_agent.py`)

- **Description**: Scrapes data from websites.
- **Functionality**: Extracts data from web pages.

### 15. Sentiment Agent (`src/agents/sentiment_agent.py`)

- **Description**: Analyzes market sentiment from social media.
- **Functionality**: Determines market sentiment from social media data.

### 16. Sniper Agent (`src/agents/sniper_agent.py`)

- **Description**: Snipes newly listed tokens.
- **Functionality**: Automates the purchase of newly listed tokens.

### 17. Solana Agent (`src/agents/solana_agent.py`)

- **Description**: Trades on the Solana blockchain.
- **Functionality**: Executes trades on Solana.

### 18. Tweet Agent (`src/agents/tweet_agent.py`)

- **Description**: Posts trading updates on Twitter.
- **Functionality**: Automates posting of trading updates on Twitter.

### 19. Volume Agent (`src/agents/volume_agent.py`)

- **Description**: Identifies high-volume tokens.
- **Functionality**: Monitors trading volume and identifies high-volume tokens.

### 20. Websearch Agent (`src/agents/websearch_agent.py`)

- **Description**: Searches the web for trading information.
- **Functionality**: Gathers trading information from the web.

## Claude Flow MCP Integration

### Key Principles
- **Concurrent Execution**: ALL operations MUST be batched in single messages
- **Parallel Processing**: Multiple agents work simultaneously
- **Memory Coordination**: Shared memory across agents
- **Hook System**: Pre/post operation coordination

### Mandatory Rules
1. **Batch Everything**: 5-10+ todos, multiple agents, all file ops in ONE message
2. **Parallel First**: Never sequential execution
3. **MCP Coordinates**: Claude Code executes all actual work
4. **Agent Count**: Auto-decide based on task complexity (3-12 agents)

### Agent Types (54 Total)
- **Core**: coder, reviewer, tester, planner, researcher
- **Swarm Coordination**: hierarchical, mesh, adaptive coordinators
- **Consensus**: byzantine, raft, gossip, crdt coordinators
- **Performance**: perf-analyzer, benchmarker, task-orchestrator
- **GitHub**: pr-manager, code-review-swarm, repo-architect
- **SPARC**: specification, pseudocode, architecture, refinement
- **Specialized**: backend-dev, mobile-dev, ml-developer, api-docs

This document provides a starting point for understanding the various agents available within the AI Trading Agents project. Further exploration of the source code and documentation is encouraged for a deeper understanding.