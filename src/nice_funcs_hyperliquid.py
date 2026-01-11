"""
🕉️ HyperLiquid Trading Functions
Focused functions for HyperLiquid perps trading
Built with love by Karma Dev 🚀

LEVERAGE & POSITION SIZING:
- All 'amount' parameters represent NOTIONAL position size (total exposure)
- Leverage is applied by the exchange, reducing required margin
- Example: $25 position at 5x leverage = $25 notional, $5 margin required
- Formula: Required Margin = Notional Position / Leverage
- Default leverage: 5x (configurable below)
"""

import os
import json
import time
import requests
import pandas as pd
import numpy as np
import pandas_ta as ta
import datetime
from datetime import timedelta
from termcolor import colored, cprint
from eth_account.signers.local import LocalAccount
import eth_account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

# Hide all warnings
import warnings
warnings.filterwarnings('ignore')

# Import logging from trading_app (module-level, not inside functions)
try:
    from trading_app import add_console_log
except ImportError:
    # Fallback if trading_app not available (standalone usage)
    def add_console_log(message, level="info"):
        """Fallback logger when trading_app not available"""
        print(f"[{level.upper()}] {message}")

# ============================================================================
# API RETRY & RATE LIMIT HANDLING
# ============================================================================

# Rate limit tracking
_api_call_times = []
_API_RATE_LIMIT = 50  # Max calls per minute
_API_RATE_WINDOW = 60  # Window in seconds

def _check_rate_limit():
    """Check if we're approaching rate limit and wait if needed."""
    global _api_call_times
    now = time.time()
    # Remove calls older than the window
    _api_call_times = [t for t in _api_call_times if now - t < _API_RATE_WINDOW]

    if len(_api_call_times) >= _API_RATE_LIMIT:
        wait_time = _API_RATE_WINDOW - (now - _api_call_times[0]) + 1
        if wait_time > 0:
            cprint(f"⏳ Rate limit approaching, waiting {wait_time:.1f}s...", "yellow")
            add_console_log(f"Rate limit: waiting {wait_time:.1f}s", "warning")
            time.sleep(wait_time)
            _api_call_times = []

    _api_call_times.append(now)

def api_request_with_retry(url, data, max_retries=4, base_delay=2):
    """
    Make an API request with exponential backoff retry logic.

    Handles:
    - 429 (Rate Limit) - waits and retries
    - 404 (Not Found) - retries in case of temporary issues
    - 500/502/503/504 (Server Errors) - retries with backoff
    - Network errors - retries with backoff

    Args:
        url: API endpoint URL
        data: JSON data to POST
        max_retries: Maximum number of retry attempts (default 4)
        base_delay: Base delay in seconds for exponential backoff (default 2)

    Returns:
        Response JSON on success

    Raises:
        Exception on final failure after all retries
    """
    headers = {'Content-Type': 'application/json'}
    last_error = None

    for attempt in range(max_retries):
        try:
            # Check rate limit before making call
            _check_rate_limit()

            response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)

            # Success
            if response.status_code == 200:
                return response.json()

            # Rate limited - wait longer
            if response.status_code == 429:
                delay = base_delay * (2 ** attempt) * 2  # Double the delay for rate limits
                cprint(f"⚠️ Rate limited (429), waiting {delay}s... (attempt {attempt + 1}/{max_retries})", "yellow")
                add_console_log(f"API rate limited - retry in {delay}s", "warning")
                time.sleep(delay)
                continue

            # Not found - might be temporary
            if response.status_code == 404:
                delay = base_delay * (2 ** attempt)
                cprint(f"⚠️ Not found (404), retrying in {delay}s... (attempt {attempt + 1}/{max_retries})", "yellow")
                time.sleep(delay)
                continue

            # Server errors - retry with backoff
            if response.status_code in [500, 502, 503, 504]:
                delay = base_delay * (2 ** attempt)
                cprint(f"⚠️ Server error ({response.status_code}), retrying in {delay}s... (attempt {attempt + 1}/{max_retries})", "yellow")
                add_console_log(f"API server error {response.status_code} - retry in {delay}s", "warning")
                time.sleep(delay)
                continue

            # Other errors - raise immediately
            last_error = f"API error: {response.status_code} - {response.text[:200]}"
            raise Exception(last_error)

        except requests.exceptions.Timeout:
            delay = base_delay * (2 ** attempt)
            cprint(f"⚠️ Request timeout, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})", "yellow")
            add_console_log(f"API timeout - retry in {delay}s", "warning")
            last_error = "Request timeout"
            time.sleep(delay)
            continue

        except requests.exceptions.ConnectionError as e:
            delay = base_delay * (2 ** attempt)
            cprint(f"⚠️ Connection error, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})", "yellow")
            add_console_log(f"API connection error - retry in {delay}s", "warning")
            last_error = f"Connection error: {e}"
            time.sleep(delay)
            continue

        except Exception as e:
            if "API error" in str(e):
                raise  # Re-raise API errors
            delay = base_delay * (2 ** attempt)
            last_error = str(e)
            time.sleep(delay)
            continue

    # All retries exhausted
    error_msg = f"API request failed after {max_retries} attempts: {last_error}"
    cprint(f"❌ {error_msg}", "red")
    add_console_log(f"API failed after {max_retries} retries", "error")
    raise Exception(error_msg)


# ============================================================================
# CONFIGURATION
# ============================================================================
DEFAULT_LEVERAGE = 20  # Change this to adjust leverage globally (1-50x on HyperLiquid)
                      # Higher leverage = less margin required, but higher liquidation risk
                      # Examples:
                      # - 5x: $25 position needs $5 margin
                      # - 10x: $25 position needs $2.50 margin
                      # - 20x: $25 position needs $1.25 margin

# Constants
BATCH_SIZE = 5000  # MAX IS 5000 FOR HYPERLIQUID
MAX_RETRIES = 3
MAX_ROWS = 5000
BASE_URL = 'https://api.hyperliquid.xyz/info'

# Global variable to store timestamp offset
timestamp_offset = None

def adjust_timestamp(dt):
    """Adjust API timestamps by subtracting the timestamp offset."""
    if timestamp_offset is not None:
        corrected_dt = dt - timestamp_offset
        return corrected_dt
    return dt

def get_hyperliquid_universe():
    """
    Get all available symbols from Hyperliquid universe.
    Returns a dict mapping symbol names to their metadata.
    Uses retry logic for resilience against API errors.
    """
    url = 'https://api.hyperliquid.xyz/info'
    data = {'type': 'meta'}

    try:
        meta = api_request_with_retry(url, data)
        universe = {coin['name']: coin for coin in meta.get('universe', [])}
        return universe
    except Exception as e:
        print(f"❌ Error getting Hyperliquid universe: {e}")
        return {}


def validate_symbol(symbol):
    """
    Validate that a symbol exists on Hyperliquid.
    Returns (is_valid, symbol_info) tuple.
    """
    universe = get_hyperliquid_universe()
    if symbol in universe:
        return True, universe[symbol]

    # Try uppercase
    symbol_upper = symbol.upper()
    if symbol_upper in universe:
        return True, universe[symbol_upper]

    return False, None


def get_asset_max_leverage(symbol):
    """
    Get the maximum allowed leverage for a symbol from Hyperliquid.

    Args:
        symbol: Token symbol (e.g., 'BTC', 'TAO')

    Returns:
        int: Maximum leverage allowed by the exchange for this asset
             Falls back to DEFAULT_LEVERAGE if unable to fetch
    """
    try:
        universe = get_hyperliquid_universe()

        # Try exact match first
        if symbol in universe:
            max_lev = universe[symbol].get('maxLeverage', DEFAULT_LEVERAGE)
            return int(max_lev)

        # Try uppercase
        symbol_upper = symbol.upper()
        if symbol_upper in universe:
            max_lev = universe[symbol_upper].get('maxLeverage', DEFAULT_LEVERAGE)
            return int(max_lev)

        # Symbol not found, return default
        return DEFAULT_LEVERAGE

    except Exception as e:
        print(f"⚠️ Error fetching max leverage for {symbol}: {e}")
        return DEFAULT_LEVERAGE


def get_effective_leverage(symbol, requested_leverage):
    """
    Get the effective leverage to use for a symbol, clamped to exchange max.

    Args:
        symbol: Token symbol
        requested_leverage: The leverage requested by the system/user

    Returns:
        tuple: (effective_leverage, was_clamped, exchange_max)
    """
    exchange_max = get_asset_max_leverage(symbol)
    effective = min(requested_leverage, exchange_max)
    was_clamped = effective < requested_leverage
    return effective, was_clamped, exchange_max


def ask_bid(symbol):
    """Get ask and bid prices for a symbol with retry logic."""
    url = 'https://api.hyperliquid.xyz/info'
    data = {
        'type': 'l2Book',
        'coin': symbol
    }

    try:
        l2_data = api_request_with_retry(url, data)

        # Validate response structure
        if 'levels' not in l2_data:
            raise Exception(f"Invalid API response: missing 'levels' key. Symbol '{symbol}' may not exist on Hyperliquid.")

        levels = l2_data['levels']

        # Validate levels structure
        if len(levels) < 2 or len(levels[0]) == 0 or len(levels[1]) == 0:
            raise Exception(f"Invalid order book structure for {symbol}. Symbol may not exist on Hyperliquid.")

        # get bid and ask
        bid = float(levels[0][0]['px'])
        ask = float(levels[1][0]['px'])

        # Validate prices are positive (prevents division by zero downstream)
        if bid <= 0 or ask <= 0:
            raise Exception(f"Invalid prices for {symbol}: bid={bid}, ask={ask}. Prices must be positive.")

        return ask, bid, levels

    except Exception as e:
        print(f"❌ Error getting ask/bid for {symbol}: {e}")
        raise

def get_sz_px_decimals(symbol):
    """
    Get size and price decimals for a symbol with retry logic.

    Raises:
        ValueError: If symbol is not found on Hyperliquid
        Exception: If API call fails
    """
    url = 'https://api.hyperliquid.xyz/info'
    data = {'type': 'meta'}

    try:
        meta_data = api_request_with_retry(url, data)
        symbols = meta_data['universe']
        symbol_info = next((s for s in symbols if s['name'] == symbol), None)

        # Also check uppercase version
        if not symbol_info:
            symbol_info = next((s for s in symbols if s['name'] == symbol.upper()), None)

        if symbol_info:
            sz_decimals = symbol_info['szDecimals']
        else:
            available_symbols = [s['name'] for s in symbols]
            error_msg = f"Symbol '{symbol}' not found on Hyperliquid. Available symbols: {', '.join(sorted(available_symbols)[:20])}..."
            print(f'❌ {error_msg}')
            add_console_log(f"❌ {symbol} not available on Hyperliquid", "error")
            raise ValueError(error_msg)

    except ValueError:
        raise
    except Exception as e:
        error_msg = f"API error when fetching symbol info: {e}"
        print(f'❌ {error_msg}')
        raise Exception(error_msg)

    try:
        ask = ask_bid(symbol)[0]
        ask_str = str(ask)

        if '.' in ask_str:
            px_decimals = len(ask_str.split('.')[1])
        else:
            px_decimals = 0

        print(f'{symbol} price: {ask} | sz decimals: {sz_decimals} | px decimals: {px_decimals}')
        return sz_decimals, px_decimals
    except Exception as e:
        # If we can't get price, use default price decimals
        print(f'⚠️ Could not get price for {symbol}, using default px_decimals=2: {e}')
        return sz_decimals, 2

def get_position(symbol_or_address, account=None):
    """
    Unified get_position. 
    CRITICAL FIX: Queries the 'ACCOUNT_ADDRESS' from env for positions,
    even if 'account' (API Wallet) is passed for signing.
    """
    try:
        from termcolor import colored
    except ImportError:
        def colored(text, color): return text

    import os
    
    # 1. DETECT EXCHANGE MODE
    is_solana_mode = len(str(symbol_or_address)) > 10

    # ==================================================
    # 🦁 SOLANA LOGIC (Keep as is)
    # ==================================================
    if is_solana_mode:
        token_mint_address = symbol_or_address
        # ... (Your existing Solana logic here) ...
        # (Paste the Solana block from the previous step if needed, 
        #  but the critical fix is below in the Hyperliquid section)
        
        # Placeholder for brevity if you already have the Solana part working:
        print(f"Checking Solana {token_mint_address[:8]}...")
        return ([], False, 0.0, token_mint_address, 0.0, 0.0, True)

    # ==================================================
    # 💧 HYPERLIQUID LOGIC
    # ==================================================
    else:
        symbol = symbol_or_address
        
        # 👇 CRITICAL FIX: Determine which address to QUERY
        # We must look at the MAIN Account (from .env), not the API Wallet (account.address)
        target_address = os.getenv("ACCOUNT_ADDRESS")
        
        # Fallback if .env is missing (but warn user)
        if not target_address and account:
            target_address = account.address
            print(colored("⚠️  Warning: Using API Wallet address for position check. Positions might be hidden!", "yellow"))
            
        print(f'{colored("Getting HYPERLIQUID position for", "cyan")} {colored(symbol, "yellow")}')
        print(f'   {colored("🔎 Querying Address:", "cyan")} {target_address}') # Debug print

        # Robust Imports
        try:
            from hyperliquid.info import Info
            from hyperliquid.utils import constants
        except ImportError:
            print(colored("❌ Error: hyperliquid-python-sdk not installed", "red"))
            return [], False, 0, symbol, 0, 0, True

        try:
            # Connect
            info = Info(constants.MAINNET_API_URL, skip_ws=True)
            user_state = info.user_state(target_address) # 👈 Query the TARGET address
        except Exception as e:
            print(f'{colored("❌ Error fetching user state:", "red")} {e}')
            return [], False, 0, symbol, 0, 0, True

        positions = []
        active_coins_debug = []

        for position in user_state["assetPositions"]:
            raw_pos = position["position"]
            coin = raw_pos["coin"]
            sz = float(raw_pos["szi"])
            
            if sz != 0:
                active_coins_debug.append(coin)

            if coin == symbol and sz != 0:
                positions.append(raw_pos)
                pos_size = sz
                entry_px = float(raw_pos["entryPx"])
                pnl_perc = float(raw_pos["returnOnEquity"]) * 100
                print(f'{colored(f"{coin} position:", "green")} Size: {pos_size} | Entry: ${entry_px} | PnL: {pnl_perc:.2f}%')

        im_in_pos = len(positions) > 0

        if not im_in_pos:
            print(f'{colored("No position in", "yellow")} {symbol}')
            if active_coins_debug:
                 print(f'   {colored("ℹ️  Found these instead:", "cyan")} {active_coins_debug}')
            return [], False, 0, symbol, 0, 0, True

        # --- NEW: Handle multiple open subpositions individually ---
        print(colored(f"📊 Found {len(positions)} open subposition(s) for {symbol}", "cyan"))

        for p in positions:
            sz = float(p["szi"])
            entry_px = float(p["entryPx"])
            pnl_perc = float(p["returnOnEquity"]) * 100
            direction = "LONG" if sz > 0 else "SHORT"
            print(colored(f"   • {direction} {abs(sz)} {symbol} @ ${entry_px:.2f} | PnL: {pnl_perc:.2f}%", "green" if pnl_perc > 0 else "red"))

        # Return all positions, plus a summary of the first one
        pos_size = float(positions[0]["szi"])
        pos_sym = positions[0]["coin"]
        entry_px = float(positions[0]["entryPx"])
        pnl_perc = float(positions[0]["returnOnEquity"]) * 100
        is_long = pos_size > 0

        return positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long



def set_leverage(symbol, leverage, account):
    """
    Set leverage for a symbol, clamped to exchange maximum.

    Args:
        symbol: Token symbol
        leverage: Requested leverage multiplier
        account: HyperLiquid account object

    Returns:
        tuple: (result, actual_leverage) - API result and the leverage actually set
    """
    # Get effective leverage (clamped to exchange max)
    effective_leverage, was_clamped, exchange_max = get_effective_leverage(symbol, leverage)

    if was_clamped:
        cprint(f'⚠️ Leverage clamped for {symbol}: requested {leverage}x but exchange max is {exchange_max}x → using {effective_leverage}x', 'yellow')
        add_console_log(f"⚠️ {symbol} leverage: {leverage}x → {effective_leverage}x (max: {exchange_max}x)", "warning")
    else:
        print(f'Setting leverage for {symbol} to {effective_leverage}x')

    exchange = Exchange(account, constants.MAINNET_API_URL)

    # Update leverage (is_cross=True for cross margin)
    result = exchange.update_leverage(effective_leverage, symbol, is_cross=True)
    print(f'✅ Leverage set to {effective_leverage}x for {symbol}')

    return result, effective_leverage

def adjust_leverage_usd_size(symbol, usd_size, leverage, account):
    """Adjust leverage and calculate position size"""
    print(f'Adjusting leverage for {symbol} to {leverage}x with ${usd_size} size')

    # Set the leverage (may be clamped to exchange max)
    _, actual_leverage = set_leverage(symbol, leverage, account)

    # Get current price
    ask, bid, _ = ask_bid(symbol)
    mid_price = (ask + bid) / 2

    # Calculate position size in coins
    pos_size = usd_size / mid_price

    # Get decimals for rounding
    sz_decimals, _ = get_sz_px_decimals(symbol)
    pos_size = round(pos_size, sz_decimals)

    print(f'Position size: {pos_size} {symbol} (${usd_size} at ${mid_price:.2f})')

    return actual_leverage, pos_size

def cancel_all_orders(account):
    """Cancel all open orders"""
    print(colored('🚫 Cancelling all orders', 'yellow'))
    exchange = Exchange(account, constants.MAINNET_API_URL)
    info = Info(constants.MAINNET_API_URL, skip_ws=True)

    # Get all open orders
    open_orders = info.open_orders(account.address)

    if not open_orders:
        print(colored('   No open orders to cancel', 'yellow'))
        return

    # Cancel each order
    for order in open_orders:
        try:
            exchange.cancel(order['coin'], order['oid'])
            print(colored(f'   ✅ Cancelled {order["coin"]} order', 'green'))
        except Exception as e:
            print(colored(f'   ⚠️ Could not cancel {order["coin"]} order: {str(e)}', 'yellow'))

    print(colored('✅ All orders cancelled', 'green'))
    return

def limit_order(coin, is_buy, sz, limit_px, reduce_only, account):
    """Place a limit order"""
    exchange = Exchange(account, constants.MAINNET_API_URL)

    rounding = get_sz_px_decimals(coin)[0]
    sz = round(sz, rounding)

    print(f"🕉️ Karma Dev placing order:")
    print(f"Symbol: {coin}")
    print(f"Side: {'BUY' if is_buy else 'SELL'}")
    print(f"Size: {sz}")
    print(f"Price: ${limit_px}")
    print(f"Reduce Only: {reduce_only}")

    order_result = exchange.order(coin, is_buy, sz, limit_px, {"limit": {"tif": "Gtc"}}, reduce_only=reduce_only)

    if isinstance(order_result, dict) and 'response' in order_result:
        print(f"✅ Order placed with status: {order_result['response']['data']['statuses'][0]}")
    else:
        print(f"✅ Order placed")

    return order_result

def kill_switch(symbol, account):
    """Close all open positions for a symbol at market price (supports multiple subpositions)"""
    print(colored(f'🔪 KILL SWITCH ACTIVATED for {symbol}', 'red', attrs=['bold']))

    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    exchange = Exchange(account, constants.MAINNET_API_URL)

    # Get all current open positions for the symbol
    positions, im_in_pos, _, _, _, _, _ = get_position(symbol, account)

    if not im_in_pos or not positions:
        print(colored('No position(s) to close', 'yellow'))
        return

    print(colored(f"🧹 Closing {len(positions)} open subposition(s) for {symbol}...", "cyan"))

    # Get current market prices
    ask, bid, _ = ask_bid(symbol)

    for p in positions:
        pos_size = abs(float(p["szi"]))
        entry_px = float(p["entryPx"])
        pnl_perc = float(p["returnOnEquity"]) * 100
        is_long = float(p["szi"]) > 0
        side = not is_long  # Opposite side to close

        print(f'Closing {"LONG" if is_long else "SHORT"} position: {pos_size} {symbol} (Entry ${entry_px:.2f}, PnL {pnl_perc:.2f}%)')

        # For closing positions with IOC orders:
        # - Closing long: Sell below bid (undersell)
        # - Closing short: Buy above ask (overbid)
        if is_long:
            close_price = bid * 0.999  # Undersell to close long
        else:
            close_price = ask * 1.001  # Overbid to close short

        # Round to appropriate decimals for BTC
        if symbol == 'BTC':
            close_price = round(close_price)
        else:
            close_price = round(close_price, 1)

        print(f'   Placing IOC at ${close_price} to close subposition')

        # Place reduce-only order to close this subposition
        try:
            order_result = exchange.order(symbol, side, pos_size, close_price, {"limit": {"tif": "Ioc"}}, reduce_only=True)
            print(colored('✅ Subposition closed successfully', 'green'))
        except Exception as e:
            print(colored(f'❌ Error closing subposition: {e}', 'red'))

    print(colored(f'✅ Kill switch executed - all {symbol} subpositions closed', 'green'))
    # Log to Dashboard
    try:
        add_console_log(f"\n✔️ Closed {symbol} position", "trade")
    except Exception:
        pass
    
    return order_result

def pnl_close(symbol, target, max_loss, account):
    """Close position if PnL target or stop loss is hit"""
    print(f'{colored("Checking PnL conditions", "cyan")}')
    print(f'Target: {target}% | Stop loss: {max_loss}%')

    # Get current position info
    positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = get_position(symbol, account)

    if not im_in_pos:
        print(colored('No position to check', 'yellow'))
        return False

    print(f'Current PnL: {colored(f"{pnl_perc:.2f}%", "green" if pnl_perc > 0 else "red")}')

    # Check if we should close
    if pnl_perc >= target:
        print(colored(f'✅ Target reached! Closing position WIN at {pnl_perc:.2f}%', 'green', attrs=['bold']))
        kill_switch(symbol, account)
        return True
    elif pnl_perc <= max_loss:
        print(colored(f'🛑 Stop loss hit! Closing position LOSS at {pnl_perc:.2f}%', 'red', attrs=['bold']))
        kill_switch(symbol, account)
        return True
    else:
        print(f'Position still open. PnL: {pnl_perc:.2f}%')
        return False

def get_current_price(symbol):
    """Get current price for a symbol"""
    ask, bid, _ = ask_bid(symbol)
    mid_price = (ask + bid) / 2
    return mid_price

def get_account_value(address):
    """
    Get total account value (equity) for an address
    Args:
        address (str or Account): HyperLiquid wallet address or Account object
    Returns:
        float: Total account value including positions
    """
    try:
        info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Handle both string addresses and Account objects
        if hasattr(address, 'address'):
            # It's an Account object, extract the address
            address_str = address.address
        else:
            # It's already a string
            address_str = address
        
        user_state = info.user_state(address_str)
        account_value = float(user_state["marginSummary"]["accountValue"])
        
        print(f'💎 Total equity for {address_str[:6]}...{address_str[-4:]}: ${account_value:,.2f}')
        return account_value
        
    except Exception as e:
        print(f'❌ Error getting account value: {e}')
        return 0.0

def market_buy(symbol, usd_size, account, slippage=None):
    """Market buy using HyperLiquid

    Raises:
        ValueError: If symbol is not found on Hyperliquid
        Exception: If order fails
    """
    print(colored(f'📈 Market BUY {symbol} for ${usd_size}', 'green'))

    # Validate symbol exists on Hyperliquid before attempting trade
    is_valid, symbol_info = validate_symbol(symbol)
    if not is_valid:
        error_msg = f"Symbol '{symbol}' not available on Hyperliquid. Cannot execute trade."
        print(colored(f'❌ {error_msg}', 'red'))
        add_console_log(f"❌ {symbol} not on Hyperliquid - trade skipped", "error")
        raise ValueError(error_msg)

    # Get current ask price
    ask, bid, _ = ask_bid(symbol)

    # Overbid by 0.1% to ensure fill (market buy needs to be above ask)
    buy_price = ask * 1.001

    # Round to appropriate decimals for BTC (whole numbers)
    if symbol == 'BTC':
        buy_price = round(buy_price)
    else:
        buy_price = round(buy_price, 1)

    # Calculate position size
    pos_size = usd_size / buy_price

    # Get decimals and round
    sz_decimals, _ = get_sz_px_decimals(symbol)
    pos_size = round(pos_size, sz_decimals)

    # Ensure minimum order value
    order_value = pos_size * buy_price
    if order_value < 10:
        print(f'   ⚠️ Order value ${order_value:.2f} below $10 minimum, adjusting...')
        pos_size = 11 / buy_price  # $11 to have buffer
        pos_size = round(pos_size, sz_decimals)

    print(f'   Placing IOC buy at ${buy_price} (0.1% above ask ${ask})')
    print(f'   Position size: {pos_size} {symbol} (value: ${pos_size * buy_price:.2f})')

    # Place IOC order above ask to ensure fill
    exchange = Exchange(account, constants.MAINNET_API_URL)
    order_result = exchange.order(symbol, True, pos_size, buy_price, {"limit": {"tif": "Ioc"}}, reduce_only=False)

    # Validate order result
    if order_result and order_result.get('status') == 'ok':
        print(colored(f'✅ Market buy executed: {pos_size} {symbol} at ${buy_price}', 'green'))
        # Log to dashboard
        try:
            position_value = pos_size * buy_price
            add_console_log(f"📈 LONG {symbol} for ${position_value:.2f}", "trade")
        except Exception:
            pass
    else:
        error_msg = order_result.get('response', {}).get('error', 'Unknown error') if order_result else 'No response'
        print(colored(f'❌ Market buy failed: {error_msg}', 'red'))
        raise Exception(f"Order failed: {error_msg}")

    return order_result

def market_sell(symbol, usd_size, account, slippage=None):
    """Market sell using HyperLiquid

    Raises:
        ValueError: If symbol is not found on Hyperliquid
        Exception: If order fails
    """
    print(colored(f'💸 Market SELL {symbol} for ${usd_size}', 'red'))

    # Validate symbol exists on Hyperliquid before attempting trade
    is_valid, symbol_info = validate_symbol(symbol)
    if not is_valid:
        error_msg = f"Symbol '{symbol}' not available on Hyperliquid. Cannot execute trade."
        print(colored(f'❌ {error_msg}', 'red'))
        add_console_log(f"❌ {symbol} not on Hyperliquid - trade skipped", "error")
        raise ValueError(error_msg)

    # Get current bid price
    ask, bid, _ = ask_bid(symbol)

    # Undersell by 0.1% to ensure fill (market sell needs to be below bid)
    sell_price = bid * 0.999

    # Round to appropriate decimals for BTC (whole numbers)
    if symbol == 'BTC':
        sell_price = round(sell_price)
    else:
        sell_price = round(sell_price, 1)

    # Calculate position size
    pos_size = usd_size / sell_price

    # Get decimals and round
    sz_decimals, _ = get_sz_px_decimals(symbol)
    pos_size = round(pos_size, sz_decimals)

    # Ensure minimum order value
    order_value = pos_size * sell_price
    if order_value < 10:
        print(f'   ⚠️ Order value ${order_value:.2f} below $10 minimum, adjusting...')
        pos_size = 11 / sell_price  # $11 to have buffer
        pos_size = round(pos_size, sz_decimals)

    print(f'   Placing IOC sell at ${sell_price} (0.1% below bid ${bid})')
    print(f'   Position size: {pos_size} {symbol} (value: ${pos_size * sell_price:.2f})')

    # Place IOC order below bid to ensure fill
    exchange = Exchange(account, constants.MAINNET_API_URL)
    order_result = exchange.order(symbol, False, pos_size, sell_price, {"limit": {"tif": "Ioc"}}, reduce_only=False)

    # Validate order result
    if order_result and order_result.get('status') == 'ok':
        print(colored(f'✅ Market sell executed: {pos_size} {symbol} at ${sell_price}', 'red'))
        try:
            position_value = pos_size * sell_price
            add_console_log(f"📉 SHORT {symbol} for ${position_value:.2f}", "trade")
        except Exception:
            pass
    else:
        error_msg = order_result.get('response', {}).get('error', 'Unknown error') if order_result else 'No response'
        print(colored(f'❌ Market sell failed: {error_msg}', 'red'))
        raise Exception(f"Order failed: {error_msg}")

    return order_result

def close_position(symbol, account):
    """Close any open position for a symbol"""
    positions, im_in_pos, pos_size, _, _, pnl_perc, is_long = get_position(symbol, account)

    if not im_in_pos:
        print(f'No position to close for {symbol}')
        return None

    print(f'Closing {"LONG" if is_long else "SHORT"} position with PnL: {pnl_perc:.2f}%')
    return kill_switch(symbol, account)

# Additional helper functions for agents
def get_balance(address):
    """
    Get USDC balance (alias for get_available_balance for backward compatibility)
    Args:
        address (str or Account): HyperLiquid wallet address or Account object
    Returns:
        float: Available balance in USD
    """
    try:
        info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Handle both string addresses and Account objects
        if hasattr(address, 'address'):
            address_str = address.address
        else:
            address_str = address
        
        user_state = info.user_state(address_str)
        balance = float(user_state["withdrawable"])
        
        print(f'💵 Available balance: ${balance:,.2f}')
        return balance
        
    except Exception as e:
        print(f'❌ Error getting balance: {e}')
        return 0.0
      
def get_available_balance(address):
    """
    Get available (withdrawable) USDC balance for an address
    Args:
        address (str): HyperLiquid wallet address (e.g., from ACCOUNT_ADDRESS env var)
    Returns:
        float: Available balance in USD
    """
    try:
        info = Info(constants.MAINNET_API_URL, skip_ws=True)
        user_state = info.user_state(address)
        
        # Get withdrawable balance (free balance not used in positions)
        balance = float(user_state["withdrawable"])
        
        print(f'💰 Available balance for {address[:6]}...{address[-4:]}: ${balance:,.2f}')
        return balance
        
    except Exception as e:
        print(f'❌ Error getting available balance: {e}')
        return 0.0

def get_all_positions(address):
    """
    Get all open positions for an address
    Args:
        address (str or Account): HyperLiquid wallet address or Account object
    Returns:
        list: List of position dictionaries
    """
    try:
        info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Handle both string addresses and Account objects
        if hasattr(address, 'address'):
            address_str = address.address
        else:
            address_str = address
        user_state = info.user_state(address_str)
        
        positions = []
        for position in user_state["assetPositions"]:
            pos_size = float(position["position"]["szi"])
            if pos_size != 0:
                positions.append({
                    'symbol': position["position"]["coin"],
                    'size': pos_size,
                    'entry_price': float(position["position"]["entryPx"]),
                    'pnl_percent': float(position["position"]["returnOnEquity"]) * 100,
                    'is_long': pos_size > 0
                })
        
        print(f'📊 Found {len(positions)} open position(s)')
        return positions
        
    except Exception as e:
        print(f'❌ Error getting positions: {e}')
        return []

# ============================================================================
# ADDITIONAL HELPER FUNCTIONS (from nice_funcs_hl.py)
# ============================================================================

def _get_exchange():
    """Get exchange instance"""
    # Load the key
    private_key = os.getenv('HYPER_LIQUID_ETH_PRIVATE_KEY')
    if not private_key:
        raise ValueError("HYPER_LIQUID_ETH_PRIVATE_KEY not found in .env file")
    
    # FIX: Clean the key of accidental quotes or spaces
    clean_key = private_key.strip().replace('"', '').replace("'", "")
    
    account = eth_account.Account.from_key(clean_key)
    return Exchange(account, constants.MAINNET_API_URL)

def _get_info():
    """Get info instance"""
    return Info(constants.MAINNET_API_URL, skip_ws=True)

def _get_account_from_env():
    """Initialize and return HyperLiquid account from env"""
    # Load the key
    private_key = os.getenv('HYPER_LIQUID_ETH_PRIVATE_KEY')
    if not private_key:
        raise ValueError("HYPER_LIQUID_ETH_PRIVATE_KEY not found in .env file")
        
    # FIX: Clean the key of accidental quotes or spaces
    clean_key = private_key.strip().replace('"', '').replace("'", "")
    
    return eth_account.Account.from_key(clean_key)
# ============================================================================
# OHLCV DATA FUNCTIONS
# ============================================================================

def _get_ohlcv(symbol, interval, start_time, end_time, batch_size=BATCH_SIZE):
    """Internal function to fetch OHLCV data from Hyperliquid"""
    global timestamp_offset
    print(f'\n🔍 Requesting data for {symbol}:')
    print(f'📊 Batch Size: {batch_size}')
    print(f'⏰ Interval: {interval}')
    print(f'🚀 Start: {start_time.strftime("%Y-%m-%d %H:%M:%S")} UTC')
    print(f'🎯 End: {end_time.strftime("%Y-%m-%d %H:%M:%S")} UTC')

    start_ts = int(start_time.timestamp() * 1000)
    end_ts = int(end_time.timestamp() * 1000)

    # Build request payload
    request_payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": symbol,
            "interval": interval,
            "startTime": start_ts,
            "endTime": end_ts,
            "limit": batch_size
        }
    }

    print(f'\n📤 API Request Payload:')
    print(f'   URL: {BASE_URL}')
    print(f'   Payload: {request_payload}')

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                BASE_URL,
                headers={'Content-Type': 'application/json'},
                json=request_payload,
                timeout=10
            )

            print(f'\n📥 API Response:')
            print(f'   Status Code: {response.status_code}')
            print(f'   Response Text: {response.text[:500]}...' if len(response.text) > 500 else f'   Response Text: {response.text}')

            if response.status_code == 200:
                snapshot_data = response.json()
                if snapshot_data:
                    # Handle timestamp offset
                    if timestamp_offset is None:
                        latest_api_timestamp = datetime.datetime.utcfromtimestamp(snapshot_data[-1]['t'] / 1000)
                        system_current_date = datetime.datetime.utcnow()
                        expected_latest_timestamp = system_current_date
                        timestamp_offset = latest_api_timestamp - expected_latest_timestamp
                        print(f"⏱️ Calculated timestamp offset: {timestamp_offset}")

                    # Adjust timestamps
                    for candle in snapshot_data:
                        dt = datetime.datetime.utcfromtimestamp(candle['t'] / 1000)
                        adjusted_dt = adjust_timestamp(dt)
                        candle['t'] = int(adjusted_dt.timestamp() * 1000)

                    first_time = datetime.datetime.utcfromtimestamp(snapshot_data[0]['t'] / 1000)
                    last_time = datetime.datetime.utcfromtimestamp(snapshot_data[-1]['t'] / 1000)
                    print(f'✨ Received {len(snapshot_data)} candles')
                    print(f'📈 First: {first_time}')
                    print(f'📉 Last: {last_time}')
                    return snapshot_data
                print('❌ No data returned by API')
                return None

            print(f'\n⚠️ HTTP Error {response.status_code}')
            print(f'❌ Error details: {response.text}')

            # Try to parse error as JSON for better readability
            try:
                error_json = response.json()
                print(f'📋 Parsed error: {error_json}')
            except:
                pass

        except requests.exceptions.RequestException as e:
            print(f'\n⚠️ Request failed (attempt {attempt + 1}): {e}')
            import traceback
            traceback.print_exc()
            time.sleep(1)
        except Exception as e:
            print(f'\n❌ Unexpected error (attempt {attempt + 1}): {e}')
            import traceback
            traceback.print_exc()
            time.sleep(1)

    print('\n❌ All retry attempts failed')
    return None

def _process_data_to_df(snapshot_data):
    """Convert raw API data to DataFrame"""
    if snapshot_data:
        columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        data = []
        for snapshot in snapshot_data:
            timestamp = datetime.datetime.utcfromtimestamp(snapshot['t'] / 1000)
            # Convert all numeric values to float
            data.append([
                timestamp,
                float(snapshot['o']),
                float(snapshot['h']),
                float(snapshot['l']),
                float(snapshot['c']),
                float(snapshot['v'])
            ])
        df = pd.DataFrame(data, columns=columns)

        # Ensure numeric columns are float64
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        df[numeric_cols] = df[numeric_cols].astype('float64')

        print("\n📊 OHLCV Data Types:")
        print(df.dtypes)

        print("\n📈 First 5 rows of data:")
        print(df.head())

        return df
    return pd.DataFrame()

def add_technical_indicators(df):
    """Add technical indicators to the dataframe"""
    if df.empty:
        return df

    try:
        print("\n🔧 Adding technical indicators...")

        # Ensure numeric columns are float64
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        df[numeric_cols] = df[numeric_cols].astype('float64')

        # Add basic indicators
        df['sma_20'] = ta.sma(df['close'], length=20)
        df['sma_50'] = ta.sma(df['close'], length=50)
        df['rsi'] = ta.rsi(df['close'], length=14)

        # Add MACD
        macd = ta.macd(df['close'])
        df = pd.concat([df, macd], axis=1)

        # Add Bollinger Bands
        bbands = ta.bbands(df['close'])
        df = pd.concat([df, bbands], axis=1)

        print("✅ Technical indicators added successfully")
        return df

    except Exception as e:
        print(f"❌ Error adding technical indicators: {str(e)}")
        traceback.print_exc()
        return df

def get_data(symbol, timeframe='15m', bars=100, add_indicators=True):
    """
    🕉️ Karma Dev's Hyperliquid Data Fetcher

    Args:
        symbol (str): Trading pair symbol (e.g., 'BTC', 'ETH')
        timeframe (str): Candle timeframe (default: '15m')
        bars (int): Number of bars to fetch (default: 100, max: 5000)
        add_indicators (bool): Whether to add technical indicators

    Returns:
        pd.DataFrame: OHLCV data with columns [timestamp, open, high, low, close, volume]
                     and technical indicators if requested
    """
    print("\n🕉️ Karma Dev's Hyperliquid Data Fetcher")
    print(f"🎯 Symbol: {symbol}")
    print(f"⏰ Timeframe: {timeframe}")
    print(f"📊 Requested bars: {min(bars, MAX_ROWS)}")

    # Ensure we don't exceed max rows
    bars = min(bars, MAX_ROWS)

    # Calculate time window
    end_time = datetime.datetime.utcnow()
    # Add extra time to ensure we get enough bars
    start_time = end_time - timedelta(days=60)

    data = _get_ohlcv(symbol, timeframe, start_time, end_time, batch_size=bars)

    if not data:
        print("❌ No data available.")
        return pd.DataFrame()

    df = _process_data_to_df(data)

    if not df.empty:
        # Get the most recent bars
        df = df.sort_values('timestamp', ascending=False).head(bars).sort_values('timestamp')
        df = df.reset_index(drop=True)

        # Add technical indicators if requested
        if add_indicators:
            df = add_technical_indicators(df)

        print("\n📊 Data summary:")
        print(f"📈 Total candles: {len(df)}")
        print(f"📅 Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print("✨ Thanks for using Karma Dev's Data Fetcher! ✨")

    return df

# ============================================================================
# MARKET INFO FUNCTIONS
# ============================================================================

def get_market_info():
    """Get current market info for all coins on Hyperliquid"""
    try:
        print("\n🔄 Sending request to Hyperliquid API...")
        response = requests.post(
            BASE_URL,
            headers={'Content-Type': 'application/json'},
            json={"type": "allMids"}
        )

        print(f"📡 Response status code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"📦 Raw response data: {data}")
            return data
        print(f"❌ Bad status code: {response.status_code}")
        print(f"📄 Response text: {response.text}")
        return None
    except Exception as e:
        print(f"❌ Error getting market info: {str(e)}")
        traceback.print_exc()
        return None

def test_market_info():
    print("\n💹 Testing Market Info...")
    try:
        print("🎯 Fetching current market prices...")
        info = get_market_info()

        print(f"\n📊 Response type: {type(info)}")
        if info is not None:
            print(f"📝 Response content: {info}")

        if info and isinstance(info, dict):
            print("\n💰 Current Market Prices:")
            print("=" * 50)
            # Target symbols we're interested in
            target_symbols = ["BTC", "ETH", "SOL", "ARB", "OP", "MATIC"]

            for symbol in target_symbols:
                if symbol in info:
                    try:
                        price = float(info[symbol])
                        print(f"Symbol: {symbol:8} | Price: ${price:,.2f}")
                    except (ValueError, TypeError) as e:
                        print(f"⚠️ Error processing price for {symbol}: {str(e)}")
                else:
                    print(f"⚠️ No price data for {symbol}")
        else:
            print("❌ No valid market info received")
            if info is None:
                print("📛 Response was None")
            else:
                print(f"❓ Unexpected response type: {type(info)}")
    except Exception as e:
        print(f"❌ Error in market info test: {str(e)}")
        print(f"🔍 Full error traceback:")
        traceback.print_exc()

# ============================================================================
# FUNDING RATE FUNCTIONS
# ============================================================================

def get_funding_rates(symbol):
    """
    Get current funding rate for a specific coin on Hyperliquid

    Args:
        symbol (str): Trading pair symbol (e.g., 'BTC', 'ETH', 'FARTCOIN')

    Returns:
        dict: Funding data including rate, mark price, and open interest
    """
    try:
        print(f"\n🔄 Fetching funding rate for {symbol}...")
        response = requests.post(
            BASE_URL,
            headers={'Content-Type': 'application/json'},
            json={"type": "metaAndAssetCtxs"}
        )

        if response.status_code == 200:
            data = response.json()
            if len(data) >= 2 and isinstance(data[0], dict) and isinstance(data[1], list):
                # Get universe (symbols) from first element
                universe = {coin['name']: i for i, coin in enumerate(data[0]['universe'])}

                # Check if symbol exists
                if symbol not in universe:
                    print(f"❌ Symbol {symbol} not found in Hyperliquid universe")
                    print(f"📝 Available symbols: {', '.join(universe.keys())}")
                    return None

                # Get funding data from second element
                funding_data = data[1]
                idx = universe[symbol]

                if idx < len(funding_data):
                    asset_data = funding_data[idx]
                    return {
                        'funding_rate': float(asset_data['funding']),
                        'mark_price': float(asset_data['markPx']),
                        'open_interest': float(asset_data['openInterest'])
                    }

            print("❌ Unexpected response format")
            return None
        print(f"❌ Bad status code: {response.status_code}")
        return None
    except Exception as e:
        print(f"❌ Error getting funding rate for {symbol}: {str(e)}")
        traceback.print_exc()
        return None

def test_funding_rates():
    print("\n💸 Testing Funding Rates...")
    try:
        # Test with some interesting symbols
        test_symbols = ["BTC", "ETH", "SOL"]

        for symbol in test_symbols:
            print(f"\n📊 Testing {symbol}:")
            print("=" * 50)
            data = get_funding_rates(symbol)

            if data:
                # The API returns the 8-hour funding rate
                # To get hourly rate: funding_rate
                # To get annual rate: hourly * 24 * 365
                hourly_rate = float(data['funding_rate']) * 100  # Convert to percentage
                annual_rate = hourly_rate * 24 * 365  # Convert hourly to annual

                print(f"Symbol: {symbol:8} | Hourly: {hourly_rate:7.4f}% | Annual: {annual_rate:7.2f}% | OI: {data['open_interest']:10.2f}")
            else:
                print(f"❌ No funding data received for {symbol}")

    except Exception as e:
        print(f"❌ Error in funding rates test: {str(e)}")
        print(f"🔍 Full error traceback:")
        traceback.print_exc()

# ============================================================================
# ADDITIONAL TRADING FUNCTIONS
# ============================================================================

def get_token_balance_usd(token_mint_address, account):
    """Get USD value of current position

    Args:
        token_mint_address: Token symbol (e.g., 'BTC', 'ETH')
        account: HyperLiquid account object

    Returns:
        float: USD value of position (absolute value)
    """
    try:
        positions, im_in_pos, pos_size, _, _, _, _ = get_position(token_mint_address, account)
        if not im_in_pos:
            return 0

        # Get current price
        mid_price = get_current_price(token_mint_address)
        return abs(float(pos_size) * mid_price)
    except Exception as e:
        cprint(f"❌ Error getting balance for {token_mint_address}: {e}", "red")
        return 0

def ai_entry(symbol, amount, max_chunk_size=None, leverage=DEFAULT_LEVERAGE, account=None):
    """Smart entry (HyperLiquid doesn't need chunking)

    Args:
        symbol: Token symbol
        amount: Total USD notional amount (will be adjusted if leverage is clamped)
        max_chunk_size: Ignored (kept for compatibility)
        leverage: Requested leverage multiplier (may be clamped to exchange max)
        account: HyperLiquid account object (optional, will create from env if not provided)

    Returns:
        tuple: (success: bool, actual_leverage: int) - success status and actual leverage used
    """
    if account is None:
        account = _get_account_from_env()

    # Set leverage (may be clamped to exchange max)
    _, actual_leverage = set_leverage(symbol, leverage, account)

    # If leverage was clamped, the margin requirement changes
    # Original: margin = amount / leverage
    # New margin requirement: margin = amount / actual_leverage
    # To maintain the same margin spend, we need to adjust the notional
    if actual_leverage != leverage:
        # Recalculate notional to use same margin with lower leverage
        original_margin = amount / leverage
        adjusted_amount = original_margin * actual_leverage
        cprint(f'📊 Adjusted notional for {symbol}: ${amount:.2f} → ${adjusted_amount:.2f} (to maintain ${original_margin:.2f} margin at {actual_leverage}x)', 'cyan')
        amount = adjusted_amount

    result = market_buy(symbol, amount, account)
    return result is not None, actual_leverage

def open_short(token, amount, slippage=None, leverage=DEFAULT_LEVERAGE, account=None):
    """Open SHORT position explicitly

    Args:
        token: Token symbol
        amount: USD NOTIONAL position size (will be adjusted if leverage is clamped)
        slippage: Not used (kept for compatibility)
        leverage: Requested leverage multiplier (may be clamped to exchange max)
        account: HyperLiquid account object (optional, will create from env if not provided)

    Raises:
        ValueError: If symbol is not found on Hyperliquid
        Exception: If order fails

    Returns:
        tuple: (order_result: dict, actual_leverage: int) - Order response and actual leverage used
    """
    if account is None:
        account = _get_account_from_env()

    # Validate symbol exists on Hyperliquid before attempting trade
    is_valid, symbol_info = validate_symbol(token)
    if not is_valid:
        error_msg = f"Symbol '{token}' not available on Hyperliquid. Cannot execute trade."
        print(colored(f'❌ {error_msg}', 'red'))
        add_console_log(f"❌ {token} not on Hyperliquid - trade skipped", "error")
        raise ValueError(error_msg)

    try:
        # Set leverage (may be clamped to exchange max)
        _, actual_leverage = set_leverage(token, leverage, account)

        # If leverage was clamped, adjust the notional to maintain same margin
        if actual_leverage != leverage:
            original_margin = amount / leverage
            amount = original_margin * actual_leverage
            cprint(f'📊 Adjusted SHORT notional for {token}: to ${amount:.2f} (to maintain ${original_margin:.2f} margin at {actual_leverage}x)', 'cyan')

        # Get current ask price
        ask, bid, _ = ask_bid(token)

        # Overbid to ensure fill (market short needs to sell below current price)
        # But we're opening a short, so we sell, which means we want to sell below bid
        sell_price = bid * 0.999

        # Round to appropriate decimals
        if token == 'BTC':
            sell_price = round(sell_price)
        else:
            sell_price = round(sell_price, 1)

        # Calculate quantity
        pos_size = amount / sell_price

        # Get decimals and round
        sz_decimals, _ = get_sz_px_decimals(token)
        pos_size = round(pos_size, sz_decimals)

        # Calculate required margin with actual leverage
        required_margin = amount / actual_leverage

        print(colored(f'📉 Opening SHORT: {pos_size} {token} @ ${sell_price}', 'red'))
        print(colored(f'💰 Notional Position: ${amount:.2f} | Margin Required: ${required_margin:.2f} ({actual_leverage}x)', 'cyan'))

        # Place market sell to open short
        exchange = Exchange(account, constants.MAINNET_API_URL)
        order_result = exchange.order(token, False, pos_size, sell_price, {"limit": {"tif": "Ioc"}}, reduce_only=False)

        # Validate order result
        if order_result and order_result.get('status') == 'ok':
            print(colored(f'✅ Short position opened!', 'green'))
            # Log to dashboard
            try:
                position_value = pos_size * sell_price
                add_console_log(f"📉 SHORT {token} for ${position_value:.2f}", "trade")
            except Exception:
                pass
            return order_result, actual_leverage
        else:
            error_msg = order_result.get('response', {}).get('error', 'Unknown error') if order_result else 'No response'
            print(colored(f'❌ Short position failed: {error_msg}', 'red'))
            raise Exception(f"Short order failed: {error_msg}")

    except Exception as e:
        print(colored(f'❌ Error opening short: {e}', 'red'))
        traceback.print_exc()
        raise  # Re-raise instead of returning None

def close_complete_position(symbol, account, slippage=0.01, max_retries=3):
    """
    Closes an entire position immediately using reduce-only orders.
    Auto-detects Long/Short and sends opposing Market Order.
    Includes retry logic for failed closes.
    """
    try:
        from termcolor import colored
    except ImportError:
        def colored(text, color): return text

    print(f'{colored(f"📉 Closing complete position for {symbol}...", "yellow")}')

    # 1. Get current position size & direction
    pos_data = get_position(symbol, account)
    _, im_in_pos, pos_size, _, _, _, is_long = pos_data

    if not im_in_pos or pos_size == 0:
        print(f'{colored("⚠️ No position found to close!", "yellow")}')
        return False

    side = "LONG" if is_long else "SHORT"
    original_size = abs(pos_size)

    # 2. Execute Opposing Order with retry logic
    for attempt in range(max_retries):
        try:
            # Re-check position before each attempt
            if attempt > 0:
                time.sleep(1)
                pos_data = get_position(symbol, account)
                _, im_in_pos, pos_size, _, _, _, is_long = pos_data
                if not im_in_pos or pos_size == 0:
                    print(f'{colored("✅ Position already closed!", "green")}')
                    return True

            current_price = get_current_price(symbol)
            usd_amount = abs(pos_size) * current_price

            # Use direct exchange API with reduce_only=True for reliable closing
            from hyperliquid.exchange import Exchange
            from hyperliquid.utils import constants

            exchange = Exchange(account, constants.MAINNET_API_URL)

            if is_long:
                # LONG -> SELL to close (reduce_only ensures we don't go short)
                print(f"   [{attempt+1}/{max_retries}] Selling {abs(pos_size)} {symbol} (${usd_amount:.2f}) to close LONG...")
                ask, bid, _ = ask_bid(symbol)
                sell_price = bid * 0.998  # 0.2% below bid for faster fill
                if symbol == 'BTC':
                    sell_price = round(sell_price)
                else:
                    sell_price = round(sell_price, 1)

                sz_decimals, _ = get_sz_px_decimals(symbol)
                order_size = round(abs(pos_size), sz_decimals)

                order_result = exchange.order(
                    symbol, False, order_size, sell_price,
                    {"limit": {"tif": "Ioc"}},
                    reduce_only=True  # CRITICAL: Ensures we only close
                )
            else:
                # SHORT -> BUY to close (reduce_only ensures we don't go long)
                print(f"   [{attempt+1}/{max_retries}] Buying {abs(pos_size)} {symbol} (${usd_amount:.2f}) to close SHORT...")
                ask, bid, _ = ask_bid(symbol)
                buy_price = ask * 1.002  # 0.2% above ask for faster fill
                if symbol == 'BTC':
                    buy_price = round(buy_price)
                else:
                    buy_price = round(buy_price, 1)

                sz_decimals, _ = get_sz_px_decimals(symbol)
                order_size = round(abs(pos_size), sz_decimals)

                order_result = exchange.order(
                    symbol, True, order_size, buy_price,
                    {"limit": {"tif": "Ioc"}},
                    reduce_only=True  # CRITICAL: Ensures we only close
                )

            # Check order result
            if order_result and order_result.get('status') == 'ok':
                # Verify position was closed
                time.sleep(0.5)
                new_pos_data = get_position(symbol, account)
                _, still_in_pos, new_size, _, _, _, _ = new_pos_data

                if not still_in_pos or abs(new_size) < 0.0001:
                    print(f'{colored("✅ Position closed successfully!", "green")}')
                    add_console_log(f"✔️ Closed {side} {symbol}", "trade")
                    return True
                else:
                    remaining_pct = (abs(new_size) / original_size) * 100
                    print(f'{colored(f"⚠️ Partial close: {remaining_pct:.1f}% remaining", "yellow")}')
                    if remaining_pct < 5:  # Less than 5% remaining is acceptable
                        add_console_log(f"✔️ Closed {side} {symbol} (dust remaining)", "trade")
                        return True
                    # Continue to retry
            else:
                error_msg = order_result.get('response', {}).get('error', 'Unknown error') if order_result else 'No response'
                print(f'{colored(f"❌ Order failed: {error_msg}", "red")}')

        except Exception as e:
            print(f'{colored(f"❌ Error on attempt {attempt+1}: {e}", "red")}')
            if attempt == max_retries - 1:
                import traceback
                traceback.print_exc()

    # All retries exhausted
    print(f'{colored(f"❌ Failed to close {symbol} after {max_retries} attempts", "red")}')
    add_console_log(f"❌ Failed to close {symbol}", "error")
    return False
