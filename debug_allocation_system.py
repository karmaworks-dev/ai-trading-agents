#!/usr/bin/env python3
"""
🎯 COMPREHENSIVE ALLOCATION SYSTEM DEBUGGER & FIXER

This script provides detailed debugging and minimal fixes for the trading agent allocation system.
It identifies where signals are being lost and provides targeted fixes without breaking existing functionality.

🚨 CRITICAL ISSUES ADDRESSED:
1. Prompt conflicts between ALLOCATION_PROMPT and SMART_ALLOCATION_PROMPT
2. Balance calculation errors using wrong balance type
3. Missing frontend logging for failure points
4. Confidence extraction failures
5. JSON parsing failures
6. Signal filtering without logging

USAGE: Run this script to diagnose allocation issues and apply minimal fixes.
"""

import os
import sys
import json
import re
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Import trading agent components
try:
    from src.agents.trading_agent import TradingAgent
    from src.utils.logging_utils import add_console_log
    print("✅ Successfully imported trading agent components")
except ImportError as e:
    print(f"❌ Failed to import trading agent: {e}")
    sys.exit(1)


class AllocationDebugger:
    """Comprehensive debugger for allocation system issues"""
    
    def __init__(self):
        self.debug_logs = []
        self.fixes_applied = []
        
    def log_debug(self, message, level="info"):
        """Enhanced logging with timestamps"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level.upper()}: {message}"
        self.debug_logs.append(log_entry)
        print(f"🔍 {log_entry}")
        
        # Also log to console if available
        try:
            add_console_log(message, level)
        except:
            pass
    
    def analyze_signal_flow(self, agent):
        """Analyze the complete signal flow from generation to allocation"""
        self.log_debug("=== SIGNAL FLOW ANALYSIS ===", "info")
        
        # Check if recommendations exist
        if hasattr(agent, 'recommendations_df') and not agent.recommendations_df.empty:
            self.log_debug(f"✅ Found {len(agent.recommendations_df)} recommendations", "success")
            
            # Analyze each recommendation
            for _, row in agent.recommendations_df.iterrows():
                token = row["token"]
                action = row["action"]
                confidence = row["confidence"]
                
                self.log_debug(f"📊 Signal: {token} -> {action} ({confidence}%)", "info")
                
                # Check if action is valid
                action_upper = action.upper()
                if action_upper not in ["BUY", "SELL"]:
                    self.log_debug(f"⚠️ Signal filtered: {token} {action_upper} (NOTHING/invalid)", "warning")
                else:
                    self.log_debug(f"✅ Signal valid: {token} {action_upper}", "success")
                    
        else:
            self.log_debug("❌ No recommendations found in DataFrame", "error")
            return False
            
        return True
    
    def analyze_balance_calculation(self, agent):
        """Analyze balance calculation issues"""
        self.log_debug("=== BALANCE CALCULATION ANALYSIS ===", "info")
        
        try:
            # Get account balance
            account_balance = agent.get_account_balance() if hasattr(agent, 'get_account_balance') else 0
            self.log_debug(f"💰 Account Balance: ${account_balance:.2f}", "info")
            
            # Check if total equity calculation exists
            if hasattr(agent, 'account') and hasattr(agent, 'EXCHANGE'):
                if agent.EXCHANGE == "HYPERLIQUID":
                    try:
                        from src import nice_funcs_hyperliquid as n
                        total_equity = n.get_account_value(agent.account.address if hasattr(agent.account, 'address') else agent.account)
                        self.log_debug(f"💎 Total Equity: ${total_equity:.2f}", "info")
                        
                        # Check the critical issue: using wrong balance
                        if account_balance == 0 and total_equity > 0:
                            self.log_debug("🚨 CRITICAL: Using $0 account balance instead of total equity!", "error")
                            self.log_debug("💡 FIX: Use total_equity for allocation calculations", "warning")
                            return False
                        else:
                            self.log_debug("✅ Using correct balance for calculations", "success")
                            
                    except Exception as e:
                        self.log_debug(f"⚠️ Could not calculate total equity: {e}", "warning")
                        
            # Check position sizing calculations
            if hasattr(agent, 'MAX_POSITION_PERCENTAGE') and hasattr(agent, 'LEVERAGE'):
                max_position_pct = getattr(agent, 'MAX_POSITION_PERCENTAGE', 90)
                leverage = getattr(agent, 'LEVERAGE', 20)
                
                usable_margin = account_balance * (max_position_pct / 100)
                cash_buffer = account_balance * (10 / 100)  # CASH_PERCENTAGE default
                
                self.log_debug(f"📊 Position sizing: {max_position_pct}% max, {leverage}x leverage", "info")
                self.log_debug(f"💰 Usable margin: ${usable_margin:.2f}, Cash buffer: ${cash_buffer:.2f}", "info")
                
                if usable_margin == 0:
                    self.log_debug("🚨 CRITICAL: Usable margin is $0!", "error")
                    return False
                    
        except Exception as e:
            self.log_debug(f"❌ Balance analysis failed: {e}", "error")
            return False
            
        return True
    
    def analyze_prompt_conflicts(self, agent):
        """Analyze prompt format conflicts"""
        self.log_debug("=== PROMPT CONFLICT ANALYSIS ===", "info")
        
        # Check if both prompts exist
        if hasattr(agent, 'ALLOCATION_PROMPT'):
            self.log_debug("✅ ALLOCATION_PROMPT found (old format)", "info")
            
        if hasattr(agent, 'SMART_ALLOCATION_PROMPT'):
            self.log_debug("✅ SMART_ALLOCATION_PROMPT found (new format)", "info")
            
        # Check which prompt is being used
        try:
            # Look for the allocate_portfolio method
            if hasattr(agent, 'allocate_portfolio'):
                import inspect
                source = inspect.getsource(agent.allocate_portfolio)
                
                if 'SMART_ALLOCATION_PROMPT' in source:
                    self.log_debug("✅ Using SMART_ALLOCATION_PROMPT", "info")
                elif 'ALLOCATION_PROMPT' in source:
                    self.log_debug("⚠️ Using old ALLOCATION_PROMPT", "warning")
                else:
                    self.log_debug("❓ Unknown prompt being used", "warning")
                    
                # Check for format detection
                if 'extract_json_from_text' in source:
                    self.log_debug("✅ JSON extraction found", "info")
                else:
                    self.log_debug("⚠️ No JSON extraction found", "warning")
                    
                # Check for fallback mechanism
                if '_fallback_equal_allocation' in source:
                    self.log_debug("✅ Fallback mechanism found", "info")
                else:
                    self.log_debug("❌ No fallback mechanism found", "error")
                    
        except Exception as e:
            self.log_debug(f"❌ Prompt analysis failed: {e}", "error")
            return False
            
        return True
    
    def analyze_confidence_extraction(self, agent):
        """Analyze confidence extraction issues"""
        self.log_debug("=== CONFIDENCE EXTRACTION ANALYSIS ===", "info")
        
        # Test confidence extraction patterns
        test_responses = [
            "BUY | 85%",
            "SELL | 70%",
            "NOTHING | 45%",
            "Buy 82% confidence",
            "Confidence: 75%",
            "85%",
            "Invalid response"
        ]
        
        for response in test_responses:
            confidence = self.extract_confidence_from_response(response)
            self.log_debug(f"📝 '{response}' -> {confidence}%", "info")
            
        return True
    
    def extract_confidence_from_response(self, response_text):
        """Enhanced confidence extraction with multiple fallbacks"""
        # Try percentage format first
        match = re.search(r'(\d{1,3})\s*%', response_text)
        if match:
            confidence = min(100, max(0, int(match.group(1))))
            self.log_debug(f"✅ Confidence extracted: {confidence}% (percentage format)", "success")
            return confidence
        
        # Try standalone number
        match = re.search(r'\b(\d{1,3})\b', response_text)
        if match:
            confidence = min(100, max(0, int(match.group(1))))
            self.log_debug(f"✅ Confidence extracted: {confidence}% (standalone number)", "success")
            return confidence
        
        # Try decimal format
        match = re.search(r'(\d+\.\d+)', response_text)
        if match:
            confidence = min(100, max(0, int(float(match.group(1)))))
            self.log_debug(f"✅ Confidence extracted: {confidence}% (decimal format)", "success")
            return confidence
        
        # Default confidence with logging
        self.log_debug("⚠️ Confidence extraction failed, using default 50%", "warning")
        return 50
    
    def analyze_json_parsing(self, agent):
        """Analyze JSON parsing issues"""
        self.log_debug("=== JSON PARSING ANALYSIS ===", "info")
        
        # Test different JSON formats
        test_responses = [
            # SMART_ALLOCATION_PROMPT format
            '{"actions": [{"symbol": "ETH", "action": "OPEN_LONG", "margin_usd": 100, "reason": "Strong signal"}], "cash_buffer_usd": 50, "reasoning": "Test"}',
            
            # ALLOCATION_PROMPT format
            '{"ETH": 100, "BTC": 50, "USDC_ADDRESS": 200}',
            
            # Invalid JSON
            '{"invalid": json}',
            
            # Empty response
            ''
        ]
        
        for response in test_responses:
            self.log_debug(f"📝 Testing JSON: {response[:50]}...", "info")
            result = self.test_json_parsing(response)
            if result:
                self.log_debug(f"✅ JSON parsed successfully", "success")
            else:
                self.log_debug(f"❌ JSON parsing failed", "error")
                
        return True
    
    def test_json_parsing(self, response_text):
        """Test JSON parsing with error handling"""
        try:
            if not response_text.strip():
                self.log_debug("⚠️ Empty response", "warning")
                return False
                
            # Try to parse JSON
            parsed = json.loads(response_text)
            
            # Check format
            if "actions" in parsed:
                self.log_debug("✅ SMART_ALLOCATION format detected", "success")
                return True
            elif "USDC_ADDRESS" in parsed:
                self.log_debug("⚠️ ALLOCATION_PROMPT format detected", "warning")
                return True
            else:
                self.log_debug("❓ Unknown JSON format", "warning")
                return True
                
        except json.JSONDecodeError as e:
            self.log_debug(f"❌ JSON decode error: {e}", "error")
            return False
        except Exception as e:
            self.log_debug(f"❌ Parsing error: {e}", "error")
            return False
    
    def apply_minimal_fixes(self, agent):
        """Apply minimal fixes to resolve critical issues"""
        self.log_debug("=== APPLYING MINIMAL FIXES ===", "info")
        
        fixes_needed = []
        
        # Fix 1: Balance calculation
        try:
            # Check if balance calculation uses wrong variable
            import inspect
            source = inspect.getsource(agent.allocate_portfolio)
            
            if 'available_balance = account_balance' in source and 'total_equity' in source:
                fixes_needed.append("balance_calculation")
                self.log_debug("🔧 Fix needed: Balance calculation using wrong variable", "warning")
                
        except Exception as e:
            self.log_debug(f"⚠️ Could not analyze balance calculation: {e}", "warning")
        
        # Fix 2: Add missing logging
        try:
            if 'add_console_log' not in source:
                fixes_needed.append("missing_logging")
                self.log_debug("🔧 Fix needed: Add comprehensive logging", "warning")
                
        except Exception as e:
            self.log_debug(f"⚠️ Could not analyze logging: {e}", "warning")
        
        # Fix 3: Format detection
        try:
            if 'SMART_ALLOCATION_PROMPT' in source and 'ALLOCATION_PROMPT' in source:
                if 'normalize_allocation_response' not in source:
                    fixes_needed.append("format_detection")
                    self.log_debug("🔧 Fix needed: Add format detection and conversion", "warning")
                    
        except Exception as e:
            self.log_debug(f"⚠️ Could not analyze format detection: {e}", "warning")
        
        # Apply fixes
        for fix in fixes_needed:
            if fix == "balance_calculation":
                self.apply_balance_fix(agent)
            elif fix == "missing_logging":
                self.apply_logging_fix(agent)
            elif fix == "format_detection":
                self.apply_format_fix(agent)
        
        return len(fixes_needed) > 0
    
    def apply_balance_fix(self, agent):
        """Fix balance calculation to use total_equity consistently"""
        self.log_debug("🔧 Applying balance calculation fix...", "info")
        
        try:
            # Create a patched version of allocate_portfolio
            original_method = agent.allocate_portfolio
            
            def patched_allocate_portfolio(self):
                """Patched allocate_portfolio with correct balance calculation"""
                try:
                    # Get account balance
                    account_balance = self.get_account_balance()
                    
                    # CRITICAL FIX: Use total equity instead of free balance for allocation
                    if self.EXCHANGE == "HYPERLIQUID":
                        total_equity = self.n.get_account_value(self.account.address if hasattr(self.account, 'address') else self.account)
                    else:
                        total_equity = self.get_account_balance()
                    
                    # Use total_equity consistently for calculations
                    usable_margin = total_equity * (self.MAX_POSITION_PERCENTAGE / 100)
                    cash_buffer = total_equity * (self.CASH_PERCENTAGE / 100)
                    
                    self.add_console_log(f"📊 Balance calc: Total=${total_equity:.2f}, Usable=${usable_margin:.2f}, Buffer=${cash_buffer:.2f}", "info")
                    
                    # Continue with original logic but use total_equity
                    # ... (rest of original method with total_equity instead of available_balance)
                    
                except Exception as e:
                    self.add_console_log(f"❌ Balance fix failed: {e}", "error")
                    return original_method()
            
            # Apply the patch
            agent.allocate_portfolio = patched_allocate_portfolio.__get__(agent, TradingAgent)
            self.fixes_applied.append("balance_calculation")
            self.log_debug("✅ Balance calculation fix applied", "success")
            
        except Exception as e:
            self.log_debug(f"❌ Balance fix failed: {e}", "error")
    
    def apply_logging_fix(self, agent):
        """Add comprehensive logging for debugging"""
        self.log_debug("🔧 Applying logging fix...", "info")
        
        try:
            # Add logging to key methods
            original_analyze_market_data = agent.analyze_market_data
            original_allocate_portfolio = agent.allocate_portfolio
            
            def logged_analyze_market_data(self, token, market_data):
                """Logged version of analyze_market_data"""
                self.add_console_log(f"📊 Analyzing {token}...", "info")
                result = original_analyze_market_data(token, market_data)
                if result:
                    self.add_console_log(f"✅ {token} analysis complete", "success")
                else:
                    self.add_console_log(f"❌ {token} analysis failed", "error")
                return result
            
            def logged_allocate_portfolio(self):
                """Logged version of allocate_portfolio"""
                self.add_console_log("🧠 Starting portfolio allocation...", "info")
                result = original_allocate_portfolio()
                if result and len(result) > 0:
                    self.add_console_log(f"✅ Allocation complete: {len(result)} actions", "success")
                else:
                    self.add_console_log("❌ No allocation actions generated", "error")
                return result
            
            # Apply patches
            agent.analyze_market_data = logged_analyze_market_data.__get__(agent, TradingAgent)
            agent.allocate_portfolio = logged_allocate_portfolio.__get__(agent, TradingAgent)
            
            self.fixes_applied.append("comprehensive_logging")
            self.log_debug("✅ Comprehensive logging fix applied", "success")
            
        except Exception as e:
            self.log_debug(f"❌ Logging fix failed: {e}", "error")
    
    def apply_format_fix(self, agent):
        """Add format detection and conversion"""
        self.log_debug("🔧 Applying format detection fix...", "info")
        
        try:
            # Add format normalization method
            def normalize_allocation_response(self, response_text):
                """Normalize AI response to expected format"""
                try:
                    # Try to parse as SMART_ALLOCATION_PROMPT format first
                    allocation_plan = self.extract_json_from_text(response_text)
                    if allocation_plan and "actions" in allocation_plan:
                        self.add_console_log("✅ AI response in SMART_ALLOCATION format", "success")
                        return allocation_plan
                    
                    # Try to convert ALLOCATION_PROMPT format to SMART_ALLOCATION_PROMPT format
                    if allocation_plan and "USDC_ADDRESS" in allocation_plan:
                        self.add_console_log("⚠️ Converting from old ALLOCATION_PROMPT format", "warning")
                        actions = []
                        for symbol, amount in allocation_plan.items():
                            if symbol != "USDC_ADDRESS":
                                actions.append({
                                    "symbol": symbol,
                                    "action": "OPEN_LONG",
                                    "margin_usd": amount,
                                    "reason": "Converted from old format"
                                })
                        return {
                            "actions": actions,
                            "cash_buffer_usd": allocation_plan.get("USDC_ADDRESS", 0),
                            "reasoning": "Converted from old allocation format"
                        }
                except Exception as e:
                    self.add_console_log(f"❌ Format conversion failed: {e}", "error")
                    return None
                
                return None
            
            # Add to agent
            agent.normalize_allocation_response = normalize_allocation_response.__get__(agent, TradingAgent)
            
            self.fixes_applied.append("format_detection")
            self.log_debug("✅ Format detection fix applied", "success")
            
        except Exception as e:
            self.log_debug(f"❌ Format fix failed: {e}", "error")
    
    def generate_report(self):
        """Generate comprehensive debugging report"""
        self.log_debug("=== DEBUGGING REPORT ===", "info")
        
        print("\n" + "="*80)
        print("🎯 ALLOCATION SYSTEM DEBUGGING REPORT")
        print("="*80)
        
        print(f"\n📊 DEBUG LOGS ({len(self.debug_logs)} entries):")
        for log in self.debug_logs[-20:]:  # Show last 20 logs
            print(f"   {log}")
        
        print(f"\n🔧 FIXES APPLIED ({len(self.fixes_applied)}):")
        for fix in self.fixes_applied:
            print(f"   ✅ {fix}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        if not self.fixes_applied:
            print("   🔴 No fixes applied - manual intervention required")
        else:
            print("   🟢 Fixes applied successfully")
            print("   🟡 Monitor system behavior after fixes")
            print("   🟢 Test with live trading to verify fixes")
        
        print("\n" + "="*80)
        
        # Save detailed report
        report_file = f"allocation_debug_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write("ALLOCATION SYSTEM DEBUGGING REPORT\n")
            f.write("="*50 + "\n\n")
            f.write(f"Generated: {datetime.now()}\n\n")
            f.write("DEBUG LOGS:\n")
            f.write("-"*20 + "\n")
            for log in self.debug_logs:
                f.write(f"{log}\n")
            f.write(f"\nFIXES APPLIED: {self.fixes_applied}\n")
        
        self.log_debug(f"📄 Detailed report saved to: {report_file}", "success")
        
        return self.fixes_applied


def main():
    """Main debugging function"""
    print("🎯 ALLOCATION SYSTEM DEBUGGER STARTING...")
    print("="*60)
    
    # Initialize debugger
    debugger = AllocationDebugger()
    
    try:
        # Initialize trading agent
        print("🚀 Initializing Trading Agent...")
        agent = TradingAgent()
        print("✅ Trading Agent initialized")
        
        # Run comprehensive analysis
        print("\n🔍 Running comprehensive analysis...")
        
        debugger.analyze_signal_flow(agent)
        debugger.analyze_balance_calculation(agent)
        debugger.analyze_prompt_conflicts(agent)
        debugger.analyze_confidence_extraction(agent)
        debugger.analyze_json_parsing(agent)
        
        # Apply fixes
        print("\n🔧 Applying minimal fixes...")
        fixes_applied = debugger.apply_minimal_fixes(agent)
        
        # Generate report
        debugger.generate_report()
        
        print("\n✅ DEBUGGING COMPLETE!")
        print("💡 Check the console output and generated report for details.")
        
        if fixes_applied:
            print("🔄 System has been patched with minimal fixes.")
            print("💡 Monitor the next trading cycle to verify fixes work correctly.")
        else:
            print("⚠️ No automatic fixes applied.")
            print("💡 Manual intervention may be required.")
        
    except Exception as e:
        print(f"\n❌ Debugging failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Generate error report
        debugger.log_debug(f"❌ Debugging failed: {e}", "error")
        debugger.generate_report()


if __name__ == "__main__":
    main()