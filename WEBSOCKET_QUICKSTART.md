# 🟢 WebSocket QuickStart Guide

## Verification Steps

### 1. Run the Integration Test Suite
```bash
python test_websocket_integration.py
```

**Expected Output:**
```
✅ TEST 1-10: All tests pass
✅ WebSocket package installed v1.9.0
✅ Module imports successful
✅ Data manager initialized
✅ Idempotency test passed
✅ WebSocket connected to Hyperliquid
✅ All execution paths covered
```

### 2. Start Trading Dashboard (with Real-Time WebSocket Data)
```bash
python trading_app.py
```

**Expected Output:**
```
🔌 Starting WebSocket feeds...
✅ WebSocket feeds connected (real-time positions enabled)
✅ Dashboard listeners registered for real-time updates
🚀 Starting async log writer...
✅ Log writer started
...
Dashboard URL: http://0.0.0.0:5000
```

**In Browser:**
- Navigate to `http://localhost:5000`
- Open browser console (F12) to see SSE logs
- Should see: `[SSE] Position stream connected`
- Any position changes will update in real-time (no 30s delay)

### 3. Start Standalone Trading Agent (with WebSocket)
```bash
python src/agents/trading_agent.py
```

**Expected Output:**
```
🔌 Starting WebSocket feeds...
🟢 WebSocket feeds started successfully
📍 Subscribed to user state: 0xA871D...
⚙️ Initializing Trading Agent...
✅ Using model: ...
✅ LLM Trading Agent initialized!
🚀 AI Trading System Starting Up! 🚀
Press Ctrl+C to stop.
```

### 4. Monitor WebSocket Activity in Console

**Look for these messages:**

#### ✅ Startup Messages
```
🔌 Starting WebSocket feeds...
🟢 WebSocket feeds started successfully
✅ Dashboard listeners registered for real-time updates
```

#### ✅ Connection Messages
```
WebSocket connected!
Starting price feed for: BTC, ETH, SOL, LTC, AAVE, HYPE
Starting order book feed for: BTC, ETH, SOL, LTC, AAVE, HYPE
Starting user state feed for 0xA871D5...
```

#### ✅ Data Flow Messages
```
📡 WebSocket: 2 positions (real-time)
📡 WebSocket position update broadcasted
📡 SSE client connected. Total clients: 1
[SSE] Position stream connected
```

#### ✅ Frontend Messages (Browser Console)
```
[Dashboard] Full update at 18:45:23
[SSE] Position update received: 2 positions
updatePositions called with 2 positions
```

## Data Flow Verification

### Backend → Frontend Real-Time Path

```
1. WebSocket receives position update from HyperLiquid
   └─ Price: 42,500 USD
   └─ Size: 0.5 BTC
   └─ PnL: +$250

2. on_position_update() callback fires
   └─ Data added to SSE client queues

3. Frontend receives SSE message
   └─ [SSE] Position update received

4. JavaScript updatePositions() called
   └─ DOM updated with new price/PnL

5. Dashboard displays in real-time
   └─ 🟢 Position updated instantly
```

## Troubleshooting

### Issue: "WebSocket module not available"

**Check:**
```bash
python -c "from src.websocket import start_websocket_feeds; print('✅ OK')"
```

**Fix:**
```bash
pip install websocket-client==1.9.0
```

---

### Issue: "WebSocket not connected"

**Check:**
1. Internet connection working
2. HyperLiquid API not blocked
3. No VPN/proxy issues

**Fix:**
```bash
# Check connection to Hyperliquid endpoint
python -c "
import websocket
try:
    ws = websocket.create_connection('wss://api.hyperliquid.xyz/ws')
    print('✅ HyperLiquid WebSocket reachable')
    ws.close()
except Exception as e:
    print(f'❌ Connection failed: {e}')
"
```

---

### Issue: "User state subscription failed"

**Check:**
```bash
# Verify private key is set
echo $HYPER_LIQUID_ETH_PRIVATE_KEY
# Should output your key, not empty
```

**Fix:**
1. Ensure `.env` has `HYPER_LIQUID_ETH_PRIVATE_KEY`
2. Key should not have quotes or extra spaces
3. Reload environment: `source .env`

---

### Issue: "SSE not receiving updates"

**Check:**
1. WebSocket is connected (see console output)
2. Dashboard listeners registered
3. Positions actually exist on account

**Fix:**
```bash
# Verify in browser console (F12):
if (positionEventSource && positionEventSource.readyState === 0) {
  console.log('✅ SSE connected and listening');
} else {
  console.log('❌ SSE not connected');
}
```

---

### Issue: Dashboard shows "updating..." but no data

**Check:**
```bash
# Verify WebSocket data manager working:
python -c "
from src.websocket import get_data_manager, is_websocket_connected
dm = get_data_manager()
print(f'Connected: {is_websocket_connected()}')
positions = dm.get_all_positions('0xYourAddress')
print(f'Positions: {len(positions)}')
"
```

**Fix:**
1. Verify `ACCOUNT_ADDRESS` in `.env` or auto-derived from key
2. Ensure account has open positions
3. Restart the app

## Performance Verification

### Check WebSocket is Actually Being Used

**In console output, look for:**
```
✅ WebSocket feeds connected (real-time positions enabled)
📡 WebSocket: 2 positions (real-time)
```

**NOT:**
```
⚠️ WebSocket not available - falling back to periodic polling
```

---

### Compare Latency (WebSocket vs Polling)

**With WebSocket:**
- Position update appears in < 200ms
- Price updates in < 100ms
- API calls: 1-2 per minute

**Without WebSocket (REST polling):**
- Position update appears in 2000ms
- Price updates in 30000ms
- API calls: 30 per minute

---

## Test Scenarios

### Scenario 1: Open/Close Position Manually
1. Open HyperLiquid app in another window
2. Execute a trade (BUY 0.01 BTC, etc.)
3. Watch dashboard - should update in < 1 second
4. Close the trade
5. Dashboard updates again in real-time

**Verification:** ✅ Position appears/disappears in real-time

---

### Scenario 2: Multiple Traders Using Dashboard
1. Terminal 1: `python trading_app.py`
2. Browser Tab 1: `http://localhost:5000` → Connect to SSE
3. Browser Tab 2: `http://localhost:5000` → Connect to SSE
4. Make a trade
5. Both tabs should update simultaneously

**Verification:** ✅ Broadcast working (check console: "Total clients: 2")

---

### Scenario 3: Restart App Mid-Update
1. Dashboard streaming positions
2. Press Ctrl+C in terminal
3. See: `🔌 WebSocket feeds stopped`
4. Restart: `python trading_app.py`
5. Dashboard reconnects automatically

**Verification:** ✅ Reconnection working (check: "Total clients: 1")

---

### Scenario 4: Network Interruption
1. Start dashboard
2. Disconnect internet / disable WiFi
3. Watch console - see reconnection attempts
4. Reconnect internet
5. WebSocket reconnects and resumes updates

**Verification:** ✅ Auto-reconnect working

---

## Configuration Checklist

### Required (must be set)
- [ ] `HYPER_LIQUID_ETH_PRIVATE_KEY` in `.env`
- [ ] `EXCHANGE='hyperliquid'` in `config.py`

### Optional (defaults work fine)
- [ ] `ACCOUNT_ADDRESS` in `.env` (auto-derived if not set)
- [ ] `USE_WEBSOCKET_FEEDS=True` (default)
- [ ] `WEBSOCKET_FALLBACK_TO_API=True` (default)

### Verify Configuration
```bash
python -c "
from src.config import EXCHANGE, USE_WEBSOCKET_FEEDS, WEBSOCKET_FALLBACK_TO_API
print(f'EXCHANGE: {EXCHANGE}')
print(f'USE_WEBSOCKET_FEEDS: {USE_WEBSOCKET_FEEDS}')
print(f'WEBSOCKET_FALLBACK_TO_API: {WEBSOCKET_FALLBACK_TO_API}')
"
```

**Expected Output:**
```
EXCHANGE: hyperliquid
USE_WEBSOCKET_FEEDS: True
WEBSOCKET_FALLBACK_TO_API: True
```

## Running All Three Paths Simultaneously

### Terminal 1: Web Dashboard
```bash
python trading_app.py
# Provides: Real-time positions via SSE to web frontend
```

### Terminal 2: Standalone Trading Agent
```bash
python src/agents/trading_agent.py
# Provides: Trading decisions with real-time market data
```

### Terminal 3: Orchestrator (Optional)
```bash
python src/main.py
# Provides: Multi-agent coordination with shared real-time data
```

**Result:** All paths share the same WebSocket connection (idempotent) ✅

---

## Success Criteria

### ✅ WebSocket is Properly Initialized
- [ ] `start_websocket_feeds()` called at startup
- [ ] Console shows "WebSocket connected!"
- [ ] No "WebSocket module not available" errors

### ✅ Data is Streaming Real-Time
- [ ] Positions update in < 200ms
- [ ] Prices update in < 100ms
- [ ] No polling delays (no 2-5 second latency)

### ✅ Frontend is Receiving Updates
- [ ] SSE client shows "connected"
- [ ] Browser console shows "[SSE] Position update received"
- [ ] Dashboard updates without page refresh

### ✅ Fallbacks are Working
- [ ] If WebSocket fails, system continues (REST fallback)
- [ ] Console shows "falling back to API polling"
- [ ] Dashboard still works (just slower)

### ✅ Performance is Optimal
- [ ] Position latency: 100-200ms (not 2000ms)
- [ ] API calls: < 5 per minute (not 30+ per minute)
- [ ] No "updating..." spinning wheel for > 1 second

---

## Support

### Check Integration Test
```bash
python test_websocket_integration.py
```

### Read Full Report
```bash
cat WEBSOCKET_VERIFICATION_REPORT.md
```

### View Recent Logs
```bash
tail -50 src/data/console_logs.json
```

### Monitor Live
```bash
python trading_app.py 2>&1 | grep -E "WebSocket|SSE|connected"
```

---

**Status:** All systems green and ready for trading! 🟢
