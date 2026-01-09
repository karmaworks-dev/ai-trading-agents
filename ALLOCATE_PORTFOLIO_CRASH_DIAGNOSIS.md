# ALLOCATE_PORTFOLIO CRASH DIAGNOSIS

**Issue**: `allocate_portfolio crashed: '\n "actions"'`

**Error Message Indicates**: KeyError where the key is literally the string `'\n "actions"'` (including the newline character)

---

## Root Cause Analysis

### The Error Pattern
```
[03:39:27] ✅ Trading cycle complete
[03:39:27] ℹ️ No allocation actions generated
[03:39:27] No allocation actions generated
❌ [03:39:27] allocate_portfolio crashed: '\n "actions"'
[03:39:25] Removed 7 strategy signals
[03:39:16] Closed 0, Held 0
```

The fact that it says "No allocation actions generated" THEN crashes suggests the allocation attempt completed but returned zero actions, then crashed on something else.

---

## Probable Causes (In Order of Likelihood)

### 1. **AI Returns Malformed JSON with Literal Newline in Key** (Most Likely)

The AI is returning JSON like this:
```json
{
  "reasoning": "Based on market conditions",
  "\n \"actions\"": [  // ← Invalid: unescaped newline!
    {"symbol": "BTC", "action": "OPEN_LONG"}
  ]
}
```

When `json.loads()` tries to parse this, it fails. Then somewhere in the code, an error occurs trying to access the key.

**Why this happens**:
- AI models sometimes return malformed JSON with escaped characters
- The prompt doesn't explicitly forbid this
- Some model providers return raw markdown output

### 2. **Greedy Regex Captures Multiple JSON Objects**

The `extract_json_from_text()` function uses:
```python
match = re.search(r"\{.*\}", text, re.DOTALL)
```

This greedy regex with `re.DOTALL` matches from the FIRST `{` to the LAST `}` in the entire response. If the AI response contains:

```
First attempt:
{
  "incomplete": "data"
}

Let me reconsider:
{
  "actions": [],
  "reasoning": "..."
}
```

The regex captures from first `{` to last `}` - mixing both objects into one invalid JSON.

### 3. **AI Returns List Instead of Dict**

The AI might return:
```json
[
  {"symbol": "BTC", "action": "OPEN_LONG"}
]
```

This is valid JSON but `extract_json_from_text()` extracts it as a list, not a dict. Then `allocation.get("actions", [])` crashes because lists don't have `.get()` method.

### 4. **Symbol Not in self.symbols**

You mentioned "we had a legitimate buy signal" but "Removed 7 strategy signals". This suggests:
- The signal was generated for a token
- But that token was filtered out (not in monitored symbols)
- So `signals` becomes empty after filtering
- AI is asked to allocate 0 signals
- AI returns `{"actions": [], "reasoning": "..."}` or something unexpected

---

## How to Diagnose

Add aggressive logging to `allocate_portfolio()` at line 2352-2355:

```python
# LOG RAW RESPONSE IMMEDIATELY (FOR DEBUGGING - ADD THIS)
add_console_log(f"\n🔍 RAW AI RESPONSE ({len(ai_response)} chars):", "debug")
add_console_log(f"START: {repr(ai_response[:200])}", "debug")
add_console_log(f"END: {repr(ai_response[-200:])}", "debug")
add_console_log(f"FULL: {ai_response}", "debug")  # Full response for analysis
```

Then modify the JSON parsing section (around line 2360-2365):

```python
try:
    add_console_log("Attempting JSON extraction...", "debug")
    allocation = extract_json_from_text(ai_response)

    add_console_log(f"Extracted type: {type(allocation).__name__}", "debug")
    if allocation:
        add_console_log(f"Extracted keys: {list(allocation.keys()) if isinstance(allocation, dict) else 'N/A'}", "debug")

    if not allocation:
        add_console_log("extract_json_from_text returned None", "error")
        return self._fallback_equal_allocation(signals, total_equity, open_positions)

    if not isinstance(allocation, dict):
        add_console_log(f"ERROR: Expected dict, got {type(allocation).__name__}: {allocation}", "error")
        return self._fallback_equal_allocation(signals, total_equity, open_positions)

    add_console_log(f"Getting 'actions' from allocation dict...", "debug")
    actions = allocation.get("actions", [])
    add_console_log(f"Actions count: {len(actions)}", "debug")

except KeyError as ke:
    add_console_log(f"KeyError: {repr(ke)}", "error")
    add_console_log(f"Available keys: {list(allocation.keys()) if isinstance(allocation, dict) else 'N/A'}", "error")
    import traceback
    traceback.print_exc()
    return self._fallback_equal_allocation(signals, total_equity, open_positions)
except Exception as e:
    add_console_log(f"JSON parsing failed: {str(e)}", "error")
    add_console_log(f"Exception type: {type(e).__name__}", "error")
    add_console_log(f"Full error: {repr(e)}", "error")
    import traceback
    traceback.print_exc()
    return self._fallback_equal_allocation(signals, total_equity, open_positions)
```

---

## Immediate Fixes to Implement

### Fix 1: Improve extract_json_from_text() Function

Replace the greedy regex approach:

```python
def extract_json_from_text(text):
    """Safely extract JSON object from AI model responses containing text."""
    # Try to find valid JSON by trying different strategies

    # Strategy 1: Look for JSON object between braces
    import re
    import json

    # Find all potential JSON objects (non-greedy)
    matches = re.finditer(r"\{[^{}]*\}", text, re.DOTALL)

    for match in matches:
        try:
            result = json.loads(match.group())
            # Validate it's the allocation response (has "actions" key)
            if isinstance(result, dict) and "actions" in result:
                return result
            # Also check if it's a response wrapper
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            continue

    # Strategy 2: Try to find JSON array (if AI returns array of actions)
    matches = re.finditer(r"\[[^\[\]]*\]", text, re.DOTALL)
    for match in matches:
        try:
            result = json.loads(match.group())
            if isinstance(result, list) and len(result) > 0:
                # Wrap in dict for consistency
                return {"actions": result}
        except json.JSONDecodeError:
            continue

    # Strategy 3: Clean up common issues and retry
    cleaned = text.replace('\n "', '\n"').replace('\n\'', '\n\'')
    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    add_console_log("No valid JSON found in AI response", "error")
    return None
```

### Fix 2: Validate AI Response Format

Add validation before using the response:

```python
try:
    allocation = extract_json_from_text(ai_response)

    # Validate extraction
    if not allocation:
        add_console_log("AI returned no valid JSON", "warning")
        return self._fallback_equal_allocation(signals, total_equity, open_positions)

    # Validate it's a dictionary
    if not isinstance(allocation, dict):
        add_console_log(f"Expected dict, got {type(allocation).__name__}", "error")
        return self._fallback_equal_allocation(signals, total_equity, open_positions)

    # Validate "actions" key exists and is a list
    if "actions" not in allocation:
        add_console_log(f"Missing 'actions' key. Available keys: {list(allocation.keys())}", "error")
        return self._fallback_equal_allocation(signals, total_equity, open_positions)

    actions = allocation.get("actions", [])

    if not isinstance(actions, list):
        add_console_log(f"'actions' must be list, got {type(actions).__name__}", "error")
        return self._fallback_equal_allocation(signals, total_equity, open_positions)

except Exception as e:
    add_console_log(f"JSON validation failed: {str(e)}", "error")
    import traceback
    traceback.print_exc()
    return self._fallback_equal_allocation(signals, total_equity, open_positions)
```

### Fix 3: Improve AI Prompt to Prevent Malformed JSON

Update the `SMART_ALLOCATION_PROMPT` to be more explicit:

```python
SMART_ALLOCATION_PROMPT = """
You are an expert crypto portfolio allocation AI.

YOUR TASK:
Return a FINAL, EXECUTABLE allocation plan based on the signals and portfolio state.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ RESPONSE FORMAT (MANDATORY AND STRICT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You MUST return ONLY valid JSON in this EXACT structure:

{{
  "actions": [
    {{
      "symbol": "HYPE",
      "action": "OPEN_LONG | OPEN_SHORT | REDUCE | CLOSE | INCREASE",
      "margin_usd": 123.45,
      "confidence": 65,
      "reason": "Short explanation"
    }}
  ],
  "cash_buffer_usd": 100.0,
  "reasoning": "Overall allocation logic summary"
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL REQUIREMENTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Do NOT wrap the JSON in any markdown code blocks (no ```json)
- Do NOT include ANY text before or after the JSON
- Do NOT escape characters in the JSON
- The JSON must be valid and parseable by Python's json.loads()
- "actions" must be an array (even if empty: [])
- Return ONLY the JSON object, nothing else

If you cannot generate valid actions, return:
{{"actions": [], "cash_buffer_usd": 0, "reasoning": "Unable to allocate at this time"}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PORTFOLIO STATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{portfolio_state}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AI TRADING SIGNALS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{signals}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ACCOUNT CONSTRAINTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Total Equity: ${available_balance:.2f}
- Leverage: {leverage}x
- Max Position %: {max_position_pct}%
- Required Cash Buffer: {cash_buffer_pct}%
- Minimum Order Size: ${min_order:.2f}
- Minimum Hold Time: {cycle_minutes} minutes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALLOCATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Higher confidence → larger allocation
2. Do not exceed max position %
3. Respect cash buffer
4. Prefer opening new positions over many small trades
5. If no good trade exists, CLOSE weakest position instead
6. Return ONLY executable actions

Remember: This JSON will be parsed by a Python script. It MUST be valid JSON.
"""
```

---

## Why the Signal Was Filtered Out

Based on your logs:
```
[03:39:25] Removed 7 strategy signals
[03:39:16] Closed 0, Held 0
we had a legitimate buy signal
```

**Possible reasons the signal was removed**:

1. **Symbol not in monitored tokens** - Line 2279-2281:
   ```python
   if token not in self.symbols:
       removed.append(f"{token}: not in symbols")
       continue
   ```
   Check if the BUY signal's token is in `monitored_tokens`.

2. **Action not BUY/SELL** - Line 2283-2285:
   ```python
   if action not in ["BUY", "SELL"]:
       removed.append(f"{token}: action {action} not actionable")
       continue
   ```
   What action did the AI recommend?

3. **LONG_ONLY mode blocking SELL** - Line 2287-2289:
   ```python
   if LONG_ONLY and action == "SELL" and token not in open_positions:
       removed.append(f"{token}: SELL blocked by LONG_ONLY")
       continue
   ```

4. **Confidence too low** - Checked later in allocation phase

---

## Testing the Fix

Create a test script to verify the fix works:

```python
import json

# Test case 1: Malformed JSON with newline in key
test1 = '''Based on analysis:
{
  "reasoning": "Test",
  "\n "actions": []
}'''

# Test case 2: Multiple JSON objects
test2 = '''First try:
{
  "incomplete": "data"
}

Better response:
{
  "actions": [],
  "reasoning": "test"
}'''

# Test case 3: Array instead of object
test3 = '''My allocation:
[
  {"symbol": "BTC", "action": "OPEN_LONG"}
]'''

# Test the improved extract_json_from_text()
for i, test_case in enumerate([test1, test2, test3], 1):
    result = extract_json_from_text(test_case)
    print(f"Test {i}: {result}")
    if result and "actions" in result:
        print(f"  Actions: {result['actions']}")
```

---

## Summary

The crash `allocate_portfolio crashed: '\n "actions"'` is a **KeyError** where the dictionary key literally contains a newline character. This happens when:

1. **AI returns malformed JSON** with escaped newlines in key names
2. **Regex extracts invalid JSON** by being too greedy
3. **AI returns a list instead of dict** and code tries to call `.get()` on it

**Solution**:
- Improve `extract_json_from_text()` to be more robust
- Add validation of extracted structure
- Improve AI prompt to prevent malformed responses
- Add comprehensive logging to diagnose future issues

The logs show "Removed 7 strategy signals" which means your signal was filtered out before reaching allocation. Check the symbol is in `monitored_tokens`.

