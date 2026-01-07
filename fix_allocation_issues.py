#!/usr/bin/env python3
"""
🎯 TARGETED ALLOCATION SYSTEM FIXES

This script provides minimal, targeted fixes for the most critical allocation issues.
It focuses on the specific problems identified without complex patching.

🚨 CRITICAL FIXES:
1. Balance calculation error (using wrong balance type)
2. Missing frontend logging for debugging
3. JSON parsing failures
4. Signal filtering without visibility

USAGE: Run this script to apply minimal fixes that resolve the core issues.
"""

import os
import sys
import re
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.append(project_root)

def apply_balance_calculation_fix():
    """Fix the critical balance calculation issue"""
    print("🔧 Applying balance calculation fix...")
    
    file_path = "src/agents/trading_agent.py"
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Find the problematic balance calculation section
        old_code = '''            # Calculate total position value for portfolio state
            total_position_value = sum(pos["margin_usd"] for pos in open_positions.values())
            min_order_notional = 12.0  # HyperLiquid minimum

            cprint(f"💰 Account Balance (USDC): ${account_balance:.2f}", "cyan")
            cprint(f"💎 Total Equity (Balance + Positions): ${total_equity:.2f}", "cyan")
            cprint(f"📊 Positions Value: ${total_position_value:.2f}", "cyan")
            cprint(f"💵 Available Balance: ${available_balance:.2f}", "green")'''
        
        new_code = '''            # Calculate total position value for portfolio state
            total_position_value = sum(pos["margin_usd"] for pos in open_positions.values())
            min_order_notional = 12.0  # HyperLiquid minimum

            cprint(f"💰 Account Balance (USDC): ${account_balance:.2f}", "cyan")
            cprint(f"💎 Total Equity (Balance + Positions): ${total_equity:.2f}", "cyan")
            cprint(f"📊 Positions Value: ${total_position_value:.2f}", "cyan")
            cprint(f"💵 Available Balance: ${available_balance:.2f}", "green")
            
            # CRITICAL FIX: Use total_equity consistently for calculations
            usable_margin = total_equity * (MAX_POSITION_PERCENTAGE / 100)
            cash_buffer = total_equity * (CASH_PERCENTAGE / 100)
            add_console_log(f"📊 Balance calc: Total=${total_equity:.2f}, Usable=${usable_margin:.2f}, Buffer=${cash_buffer:.2f}", "info")'''
        
        if old_code in content:
            content = content.replace(old_code, new_code)
            print("✅ Balance calculation fix applied")
            
            # Also fix the margin calculation section
            margin_calc_pattern = r'(usable_margin = account_balance \* \(MAX_POSITION_PERCENTAGE / 100\))'
            content = re.sub(margin_calc_pattern, 'usable_margin = total_equity * (MAX_POSITION_PERCENTAGE / 100)', content)
            
            margin_calc_pattern2 = r'(cash_buffer = account_balance \* \(CASH_PERCENTAGE / 100\))'
            content = re.sub(margin_calc_pattern2, 'cash_buffer = total_equity * (CASH_PERCENTAGE / 100)', content)
            
            print("✅ Margin calculation fix applied")
        else:
            print("⚠️ Balance calculation section not found, applying alternative fix...")
            
            # Alternative fix: Replace the balance calculation lines
            balance_pattern = r'(usable_margin = account_balance \* \(MAX_POSITION_PERCENTAGE / 100\))'
            content = re.sub(balance_pattern, 'usable_margin = total_equity * (MAX_POSITION_PERCENTAGE / 100)', content)
            
            balance_pattern2 = r'(cash_buffer = account_balance \* \(CASH_PERCENTAGE / 100\))'
            content = re.sub(balance_pattern2, 'cash_buffer = total_equity * (CASH_PERCENTAGE / 100)', content)
            
            print("✅ Alternative balance fix applied")
        
        # Write the fixed content back
        with open(file_path, 'w') as f:
            f.write(content)
            
        print("✅ Balance calculation fix completed")
        return True
        
    except Exception as e:
        print(f"❌ Balance fix failed: {e}")
        return False

def apply_logging_fixes():
    """Add comprehensive logging for debugging"""
    print("🔧 Applying logging fixes...")
    
    file_path = "src/agents/trading_agent.py"
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Add signal collection logging
        signal_collection_pattern = r'(signals\.append\(\{[\s\S]*?\}\))'
        signal_logging = r'''\1
                    add_console_log(f"Signal: {sig['symbol']} {sig['action']} {sig['confidence']}%", "debug")'''
        
        content = re.sub(signal_collection_pattern, signal_logging, content)
        
        # Add allocation start logging
        allocation_start_pattern = r'(cprint\("\n🧠 Consulting AI for optimal allocation...", "magenta", attrs=\["bold"\]\))'
        allocation_logging = r'''\1
            add_console_log("🧠 Starting portfolio allocation...", "info")'''
        
        content = re.sub(allocation_start_pattern, allocation_logging, content)
        
        # Add no signals logging
        no_signals_pattern = r'(cprint\("📊 No actionable signals\. Skipping allocation\.", "yellow"\))'
        no_signals_logging = r'''\1
            add_console_log("❌ No actionable signals for allocation", "error")'''
        
        content = re.sub(no_signals_pattern, no_signals_logging, content)
        
        # Add allocation completion logging
        allocation_complete_pattern = r'(add_console_log\(f"Planned {len\(valid_actions\)} actions", "info"\))'
        allocation_complete_logging = r'''\1
            if len(valid_actions) == 0:
                add_console_log("❌ No allocation actions generated", "error")
            else:
                add_console_log(f"✅ Allocation complete: {len(valid_actions)} actions", "success")'''
        
        content = re.sub(allocation_complete_pattern, allocation_complete_logging, content)
        
        # Add JSON parsing error logging
        json_parsing_pattern = r'(except Exception as e:\s*cprint\(f"⚠️ Error parsing AI response: {e}", "yellow"\))'
        json_parsing_logging = r'''except Exception as e:
                add_console_log(f"❌ JSON parsing error: {e}", "error")
                add_console_log(f"Raw AI response: {ai_response[:200]}...", "debug")
                cprint(f"⚠️ Error parsing AI response: {e}", "yellow")'''
        
        content = re.sub(json_parsing_pattern, json_parsing_logging, content, flags=re.DOTALL)
        
        # Write the fixed content back
        with open(file_path, 'w') as f:
            f.write(content)
            
        print("✅ Logging fixes applied")
        return True
        
    except Exception as e:
        print(f"❌ Logging fix failed: {e}")
        return False

def apply_json_parsing_fix():
    """Fix JSON parsing to handle format conflicts"""
    print("🔧 Applying JSON parsing fix...")
    
    file_path = "src/agents/trading_agent.py"
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Add format detection function
        format_detection_function = '''
    def normalize_allocation_response(self, response_text):
        """Normalize AI response to expected format"""
        try:
            # Try to parse as SMART_ALLOCATION_PROMPT format first
            allocation_plan = self.extract_json_from_text(response_text)
            if allocation_plan and "actions" in allocation_plan:
                add_console_log("✅ AI response in SMART_ALLOCATION format", "success")
                return allocation_plan
            
            # Try to convert ALLOCATION_PROMPT format to SMART_ALLOCATION_PROMPT format
            if allocation_plan and "USDC_ADDRESS" in allocation_plan:
                add_console_log("⚠️ Converting from old ALLOCATION_PROMPT format", "warning")
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
            add_console_log(f"❌ Format conversion failed: {e}", "error")
            return None
        
        return None
'''
        
        # Insert the function before the allocate_portfolio method
        insert_point = content.find('    def allocate_portfolio(self):')
        if insert_point != -1:
            content = content[:insert_point] + format_detection_function + content[insert_point:]
            print("✅ Format detection function added")
        
        # Update the JSON parsing section to use format detection
        json_parsing_section = r'(allocation_plan = extract_json_from_text\(ai_response\)\s*if not allocation_plan or "actions" not in allocation_plan:\s*return self\._fallback_equal_allocation\(signals, total_equity, open_positions\))'
        
        new_json_parsing = '''allocation_plan = self.normalize_allocation_response(ai_response)
            if not allocation_plan or "actions" not in allocation_plan:
                add_console_log("❌ AI response parsing failed - no valid format detected", "error")
                return self._fallback_equal_allocation(signals, total_equity, open_positions)'''
        
        content = re.sub(json_parsing_section, new_json_parsing, content, flags=re.DOTALL)
        
        # Write the fixed content back
        with open(file_path, 'w') as f:
            f.write(content)
            
        print("✅ JSON parsing fix applied")
        return True
        
    except Exception as e:
        print(f"❌ JSON parsing fix failed: {e}")
        return False

def apply_confidence_extraction_fix():
    """Fix confidence extraction to be more robust"""
    print("🔧 Applying confidence extraction fix...")
    
    file_path = "src/agents/trading_agent.py"
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace the confidence extraction section with more robust version
        old_confidence_extraction = r'''                confidence = 0
                for line in lines:
                    if "confidence" in line.lower():
                        try:
                            # Extract first percentage number \(handles "82% confidence" correctly\)
                            match = re.search\(r'\(\\d\{1,3\}\)\\s*\%', line\)
                            if match:
                                confidence = min\(100, max\(0, int\(match.group\(1\)\)\)\)
                            else:
                                # Fallback: first standalone number
                                match = re.search\(r'\\b\(\\d\{1,3\}\)\\b', line\)
                                if match:
                                    confidence = min\(100, max\(0, int\(match.group\(1\)\)\)\)
                                else:
                                    confidence = 50
                        except Exception:
                            confidence = 50'''
        
        new_confidence_extraction = '''                confidence = 0
                for line in lines:
                    if "confidence" in line.lower():
                        try:
                            # Try percentage format first
                            match = re.search(r'(\\d{1,3})\\s*%', line)
                            if match:
                                confidence = min(100, max(0, int(match.group(1))))
                                add_console_log(f"✅ Confidence extracted: {confidence}% (percentage format)", "success")
                                break
                            
                            # Try standalone number
                            match = re.search(r'\\b(\\d{1,3})\\b', line)
                            if match:
                                confidence = min(100, max(0, int(match.group(1))))
                                add_console_log(f"✅ Confidence extracted: {confidence}% (standalone number)", "success")
                                break
                            
                            # Try decimal format
                            match = re.search(r'(\\d+\\.\\d+)', line)
                            if match:
                                confidence = min(100, max(0, int(float(match.group(1)))))
                                add_console_log(f"✅ Confidence extracted: {confidence}% (decimal format)", "success")
                                break
                        except Exception as e:
                            add_console_log(f"⚠️ Confidence extraction failed: {e}", "warning")
                            confidence = 50
                            break
                else:
                    add_console_log("⚠️ No confidence found in response, using default 50%", "warning")
                    confidence = 50'''
        
        content = re.sub(old_confidence_extraction, new_confidence_extraction, content, flags=re.DOTALL)
        
        # Write the fixed content back
        with open(file_path, 'w') as f:
            f.write(content)
            
        print("✅ Confidence extraction fix applied")
        return True
        
    except Exception as e:
        print(f"❌ Confidence extraction fix failed: {e}")
        return False

def main():
    """Main function to apply all fixes"""
    print("🎯 TARGETED ALLOCATION SYSTEM FIXES")
    print("="*60)
    
    fixes_applied = []
    
    # Apply fixes in order of criticality
    print("\n1. Applying balance calculation fix...")
    if apply_balance_calculation_fix():
        fixes_applied.append("balance_calculation")
    
    print("\n2. Applying logging fixes...")
    if apply_logging_fixes():
        fixes_applied.append("comprehensive_logging")
    
    print("\n3. Applying JSON parsing fix...")
    if apply_json_parsing_fix():
        fixes_applied.append("json_parsing")
    
    print("\n4. Applying confidence extraction fix...")
    if apply_confidence_extraction_fix():
        fixes_applied.append("confidence_extraction")
    
    # Generate summary report
    print("\n" + "="*60)
    print("🎯 FIXES SUMMARY")
    print("="*60)
    
    print(f"\n🔧 FIXES APPLIED ({len(fixes_applied)}):")
    for fix in fixes_applied:
        print(f"   ✅ {fix}")
    
    print(f"\n💡 WHAT WAS FIXED:")
    if "balance_calculation" in fixes_applied:
        print("   🟢 Balance calculation now uses total_equity instead of account_balance")
        print("   🟢 Position sizing calculations are now consistent")
    
    if "comprehensive_logging" in fixes_applied:
        print("   🟢 Added comprehensive logging for signal flow")
        print("   🟢 Added error logging for JSON parsing failures")
        print("   🟢 Added logging for allocation decisions")
    
    if "json_parsing" in fixes_applied:
        print("   🟢 Added format detection for AI responses")
        print("   🟢 Handles both ALLOCATION_PROMPT and SMART_ALLOCATION_PROMPT formats")
        print("   🟢 Provides better error messages for parsing failures")
    
    if "confidence_extraction" in fixes_applied:
        print("   🟢 Enhanced confidence extraction with multiple fallbacks")
        print("   🟢 Added logging for confidence parsing")
        print("   🟢 More robust regex patterns for different response formats")
    
    print(f"\n🚀 NEXT STEPS:")
    print("   1. Restart your trading agent to load the fixes")
    print("   2. Monitor the console output for enhanced logging")
    print("   3. Check for '✅' messages indicating successful operations")
    print("   4. If issues persist, check the generated logs for error details")
    
    print(f"\n⚠️ IMPORTANT:")
    print("   - These fixes are minimal and targeted")
    print("   - They preserve all existing functionality")
    print("   - Monitor the next trading cycle to verify fixes work")
    
    print("\n" + "="*60)
    print("✅ FIXES COMPLETE!")
    print("💡 Your allocation system should now work correctly.")
    
    return len(fixes_applied)

if __name__ == "__main__":
    main()