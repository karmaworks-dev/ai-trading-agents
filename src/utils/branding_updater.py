#!/usr/bin/env python3
"""
🕉️ Karma Dev's Branding Update Script
Replaces Moon Dev references with Karma Dev and 🌙 emojis with 🕉️
Includes KUDOS acknowledgment to Moon Dev for proper attribution

Usage:
    python src/utils/branding_updater.py --dry-run    # Preview changes
    python src/utils/branding_updater.py --apply       # Apply changes
"""

import os
import sys
import re
import argparse
from pathlib import Path
from typing import List, Tuple, Dict

# ============================================================================
# CONFIGURATION
# ============================================================================

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# File patterns to process
FILE_PATTERNS = [
    "*.py", "*.md", "*.txt", "*.json", "*.js", "*.html", "*.css", "*.env"
]

# Directories to exclude from processing
EXCLUDE_DIRS = {
    ".git", ".vscode", "__pycache__", "node_modules", ".cache",
    "venv", "env", ".venv", ".env", "dist", "build", "logs"
}

# Directories to include (relative to project root)
INCLUDE_DIRS = {
    "src", "docs", "dashboard", "trading_venv", "scrap", "scripts"
}

# Branding replacements
BRANDING_REPLACEMENTS = [
    # Emoji replacements
    ("🌙", "🕉️"),
    
    # Case-sensitive replacements
    ("Moon Dev", "Karma Dev"),
    ("MoonDev", "KarmaDev"),
    ("Moondev", "Karmadev"),
    
    # Snake_case replacements
    ("moon_dev", "karma_dev"),
    
    # UPPER_CASE replacements
    ("MOON_DEV", "KARMA_DEV"),
    
    # Special cases (preserve in KUDOS sections)
    # Note: These will be handled separately to preserve KUDOS sections
]

# KUDOS acknowledgment text
KUDOS_TEXT = "KUDOS to Moon Dev"

# Files that need special KUDOS acknowledgment
KUDOS_FILES = {
    "trading_app.py",
    "src/agents/swarm_agent.py", 
    "src/agents/trading_agent.py",
    "src/agents/chat_agent.py",
    "src/agents/websearch_agent.py",
    "src/agents/rbi_agent_v3.py",
    "src/agents/code_runner_agent.py",
    "src/agents/sentiment_agent.py",
    "src/agents/video_agent.py",
    "src/agents/tiktok_agent.py",
    "src/agents/whale_agent.py",
    "src/agents/scraper_agent.py",
    "src/agents/sniper_agent.py",
    "src/agents/solana_agent.py",
    "src/agents/prompt_agent.py",
    "src/agents/clips_agent.py",
    "src/agents/polymarket_agent.py",
    "src/agents/chartanalysis_agent.py",
    "src/agents/clean_ideas.py",
    "src/agents/million_agent.py",
    "src/agents/giveaway_agent.py",
    "src/agents/stream_agent.py",
    "src/agents/tweet_agent.py",
    "src/agents/phone_agent.py",
    "src/agents/fundingarb_agent.py",
    "src/agents/listingarb_agent.py",
    "src/agents/copybot_agent.py",
    "src/agents/risk_agent.py",
    "src/agents/example_unified_agent.py",
    "src/agents/base_agent.py",
    "src/agents/shortvid_agent.py",
    "src/agents/chat_question_generator.py",
    "src/agents/scraper_agent.py",
    "src/agents/code_runner_agent.py",
    "src/agents/websearch_agent.py",
    "src/agents/rbi_agent_v3.py",
    "src/agents/sentiment_agent.py",
    "src/agents/video_agent.py",
    "src/agents/tiktok_agent.py",
    "src/agents/whale_agent.py",
    "src/agents/scraper_agent.py",
    "src/agents/sniper_agent.py",
    "src/agents/solana_agent.py",
    "src/agents/prompt_agent.py",
    "src/agents/clips_agent.py",
    "src/agents/polymarket_agent.py",
    "src/agents/chartanalysis_agent.py",
    "src/agents/clean_ideas.py",
    "src/agents/million_agent.py",
    "src/agents/giveaway_agent.py",
    "src/agents/stream_agent.py",
    "src/agents/tweet_agent.py",
    "src/agents/phone_agent.py",
    "src/agents/fundingarb_agent.py",
    "src/agents/listingarb_agent.py",
    "src/agents/copybot_agent.py",
    "src/agents/risk_agent.py",
    "src/agents/example_unified_agent.py",
    "src/agents/base_agent.py",
    "src/agents/shortvid_agent.py",
    "src/agents/chat_question_generator.py",
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def should_process_file(file_path: Path) -> bool:
    """Check if file should be processed based on directory and extension."""
    # Check if file is in excluded directories
    for parent in file_path.parents:
        if parent.name in EXCLUDE_DIRS:
            return False
    
    # Check if file is in included directories
    if file_path.parent.name not in INCLUDE_DIRS and file_path.parent.parent.name not in INCLUDE_DIRS:
        return False
    
    # Check file extension
    if file_path.suffix.lower() not in [".py", ".md", ".txt", ".json", ".js", ".html", ".css", ".env"]:
        return False
    
    # Skip this script itself
    if file_path.name == "branding_updater.py":
        return False
    
    return True

def find_files_to_process() -> List[Path]:
    """Find all files that need to be processed."""
    files_to_process = []
    
    for pattern in FILE_PATTERNS:
        for file_path in PROJECT_ROOT.rglob(pattern):
            if should_process_file(file_path):
                files_to_process.append(file_path)
    
    return sorted(files_to_process)

def create_kudos_section(file_path: Path, content: str) -> str:
    """Create or update KUDOS acknowledgment section in a file."""
    
    # KUDOS sections to add/update
    kudos_sections = {
        "trading_app.py": [
            "# Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev for the foundation",
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/swarm_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Swarm Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/trading_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Trading Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/chat_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Chat Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/websearch_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Web Search Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/rbi_agent_v3.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's RBI Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/code_runner_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Code Runner Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/sentiment_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Sentiment Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/video_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Video Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/tiktok_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's TikTok Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/whale_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Whale Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/scraper_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Scraper Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/sniper_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Sniper Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/solana_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Solana Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/prompt_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Prompt Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/clips_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Clips Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/polymarket_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Polymarket Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/chartanalysis_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Chart Analysis Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/clean_ideas.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Ideas Cleaner 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/million_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Million Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/giveaway_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Giveaway Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/stream_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Stream Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/tweet_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Tweet Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/phone_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Phone Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/fundingarb_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Funding Arb Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/listingarb_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Listing Arb Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/copybot_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's CopyBot Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/risk_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Risk Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/example_unified_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Unified Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/base_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Base Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/shortvid_agent.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Short Video Agent 🕉️ | KUDOS to Moon Dev"
        ],
        "src/agents/chat_question_generator.py": [
            "Built with love by Karma Dev 🕉️ | KUDOS to Moon Dev",
            "Karma Dev's Chat Question Generator 🕉️ | KUDOS to Moon Dev"
        ],
    }
    
    # Get the specific KUDOS sections for this file
    file_kudos_sections = kudos_sections.get(str(file_path), [])
    
    if not file_kudos_sections:
        return content
    
    # Remove existing KUDOS sections
    for kudos_text in file_kudos_sections:
        content = content.replace(kudos_text, "")
    
    # Add new KUDOS sections at appropriate locations
    for kudos_text in file_kudos_sections:
        # Add to the beginning of the file (after imports/comments)
        lines = content.split('\n')
        insert_index = 0
        
        # Find a good insertion point (after imports and initial comments)
        for i, line in enumerate(lines):
            if line.strip().startswith('"""') or line.strip().startswith("'''"):
                # Skip docstrings
                continue
            if line.strip().startswith('#'):
                # Skip comments
                continue
            if line.strip().startswith('import') or line.strip().startswith('from'):
                # Skip imports
                continue
            if not line.strip():
                # Skip empty lines
                continue
            insert_index = i
            break
        
        # Insert KUDOS section
        lines.insert(insert_index, f"# {kudos_text}")
        content = '\n'.join(lines)
    
    return content

def apply_branding_replacements(content: str, file_path: Path) -> str:
    """Apply branding replacements to file content."""
    original_content = content
    
    # Apply all replacements
    for old_text, new_text in BRANDING_REPLACEMENTS:
        content = content.replace(old_text, new_text)
    
    # Add KUDOS acknowledgment for specific files
    if file_path.name in KUDOS_FILES or str(file_path) in KUDOS_FILES:
        content = create_kudos_section(file_path, content)
    
    return content

def process_file(file_path: Path, dry_run: bool = False) -> Tuple[bool, str]:
    """Process a single file and return success status and message."""
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            original_content = f.read()
        
        # Apply branding replacements
        new_content = apply_branding_replacements(original_content, file_path)
        
        # Check if content changed
        if original_content == new_content:
            return True, f"No changes needed: {file_path}"
        
        # Apply changes if not dry run
        if not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        
        return True, f"{'[DRY RUN] ' if dry_run else ''}Updated: {file_path}"
        
    except Exception as e:
        return False, f"Error processing {file_path}: {str(e)}"

def main():
    """Main function to run the branding update."""
    parser = argparse.ArgumentParser(description="🕉️ Karma Dev's Branding Update Script")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying them")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default behavior)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    
    args = parser.parse_args()
    
    # Default to apply mode if no flags provided
    if not args.dry_run and not args.apply:
        args.apply = True
    
    print("🕉️ Karma Dev's Branding Update Script")
    print("=" * 60)
    print(f"Mode: {'DRY RUN (preview only)' if args.dry_run else 'APPLY CHANGES'}")
    print(f"Project Root: {PROJECT_ROOT}")
    print("=" * 60)
    
    # Find files to process
    files_to_process = find_files_to_process()
    print(f"Found {len(files_to_process)} files to process")
    
    if not files_to_process:
        print("No files found to process!")
        return
    
    # Process files
    successful = 0
    failed = 0
    changes_made = 0
    
    print("\nProcessing files...")
    for file_path in files_to_process:
        success, message = process_file(file_path, dry_run=args.dry_run)
        
        if success:
            successful += 1
            if args.verbose or "Updated:" in message:
                print(f"✅ {message}")
                if "Updated:" in message:
                    changes_made += 1
        else:
            failed += 1
            print(f"❌ {message}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total files processed: {len(files_to_process)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Changes made: {changes_made}")
    
    if args.dry_run:
        print("\n💡 Run with --apply to apply these changes")
    else:
        print("\n✅ Branding update complete!")
        print("🕉️ All Moon Dev references have been updated to Karma Dev")
        print("🕉️ KUDOS acknowledgment added to appropriate files")
        print("🕉️ 🌙 emojis have been replaced with 🕉️")

if __name__ == "__main__":
    main()