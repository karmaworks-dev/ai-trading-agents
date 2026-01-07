# Copilot Instructions for AI Trading Dashboard

This file guides AI agents in understanding and interacting with our trading ecosystem. Follow these patterns for productive integration:

---

## Architecture Overview

1. **Core Components**
   - `trading_app.py`: Main Flask API handling requests
   - `src/agents`: 48+ specialized trading agents (see README.md)
   - `src/models`: AI integration layer (ollama/Google/OpenAI)
   - `src/utils/settings_manager.py`: Config handling

2. **Data Flow**
   Settings → Agent → AI Analysis → HyperLiquid Execution

---

## Agent Workflow Patterns

`src/agents/base_agent.py` demonstrates standard workflow:
1. Load settings from `.env` and user config
2. Fetch OHLCV data via `ohlcv_collector.py`
3. Generate analysis prompt using `model_factory.py`
4. Execute decisions based on consensus rules (Swarm Mode requires 4/6 votes)

**Example Prompt:**  
"Analyze SOL/USD 1H chart: Identify reversal patterns and calculate risk/reward ratio. Provide trading recommendation with confidence score."

---

## Swarm Mode Implementation

- **Model Selection**: Configure 4+ models in settings (example: Gemini+Claude+GPT4+Mixtral)
- **Decision Rule**: 4+ agreements required for trade execution
- **Fallback**: Use highest-confidence single model if Swarm fails

Configure via dashboard or `.env`:
```env
# Swarm Model Configuration
SWARM_MODE=true
MODELS=gpt-4o,claude-4-sonnet,mixtral-8x7b,deepseek-chat
```

---

## Configuration Essentials

**.env Requirements**
```env
# Required
HYPER_LIQUID_ETH_PRIVATE_KEY=your_key  # Must be HyperLiquid ETH key

# AI Providers (at least one required)
GEMINI_KEY=your_key
ANTHROPIC_KEY=your_key
```

BYOK Support: Enable in settings or add provider keys directly to `.env`.

---

## Operational Commands

**Setup Local AI (Free Option)**
```bash
# Install Ollama and models
bash scripts/setup_ollama.sh

# Or manual:
ollama serve
ollama pull deepseek-coder
```

**Start Trading**
```bash
python trading_app.py
# Open dashboard at http://localhost:5000
```

---

## Testing & Validation

- Run agent tests with:
```bash
python -m unittest src/agents/test_trading_agent.py
```
- Monitor performance in `data/execution_results/`

---

## Critical Patterns

1. Always read `README.md` for project scope
2. Use `src/utils/settings_manager.py` for config changes
3. For new agents, follow existing agent structure in `src/agents/`
4. Swarm Mode requires explicit configuration in dashboard settings
5. **Minimal Changes**: AI must only make necessary modifications and avoid unnecessary edits to existing code/configurations unless explicitly requested