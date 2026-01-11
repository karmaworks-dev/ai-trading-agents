#!/bin/bash
# Robust deployment script for ai-trading-agents
# Handles common git pull issues automatically

set -e

BRANCH="${1:-main}"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "##########################################"
echo "### Deployment Script Started"
echo "### $(date -u)"
echo "##########################################"
echo ""

cd "$REPO_DIR"

echo "##########################################"
echo "### Checking git status"
echo "### $(date -u)"
echo "##########################################"

# Check if we're in a git repo
if [ ! -d ".git" ]; then
    echo "❌ Error: Not a git repository"
    exit 1
fi

# Show current branch
CURRENT_BRANCH=$(git branch --show-current)
echo "Current branch: $CURRENT_BRANCH"
echo "Target branch: $BRANCH"
echo ""

# Check for local changes
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Local changes detected, stashing..."
    git stash push -m "Auto-stash before deployment $(date -u)"
    STASHED=1
else
    echo "✅ Working directory clean"
    STASHED=0
fi

echo ""
echo "##########################################"
echo "### Fetching from origin"
echo "### $(date -u)"
echo "##########################################"

# Fetch with retry logic
MAX_RETRIES=4
RETRY_DELAY=2

for i in $(seq 1 $MAX_RETRIES); do
    if git fetch origin "$BRANCH" 2>&1; then
        echo "✅ Fetch successful"
        break
    else
        if [ $i -eq $MAX_RETRIES ]; then
            echo "❌ Fetch failed after $MAX_RETRIES attempts"
            exit 1
        fi
        echo "⚠️  Fetch failed, retrying in ${RETRY_DELAY}s... (attempt $i/$MAX_RETRIES)"
        sleep $RETRY_DELAY
        RETRY_DELAY=$((RETRY_DELAY * 2))
    fi
done

echo ""
echo "##########################################"
echo "### Switching to branch: $BRANCH"
echo "### $(date -u)"
echo "##########################################"

# Checkout branch
if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
    git checkout "$BRANCH" 2>&1 || {
        echo "⚠️  Checkout failed, trying to create tracking branch..."
        git checkout -b "$BRANCH" "origin/$BRANCH" 2>&1 || {
            echo "❌ Failed to checkout branch $BRANCH"
            exit 1
        }
    }
fi

echo ""
echo "##########################################"
echo "### Pulling changes"
echo "### $(date -u)"
echo "##########################################"

# Try normal pull first
if git pull origin "$BRANCH" 2>&1; then
    echo "✅ Pull successful"
else
    echo "⚠️  Normal pull failed, attempting reset to origin..."

    # Reset to origin (safe because we stashed changes)
    git reset --hard "origin/$BRANCH" 2>&1 || {
        echo "❌ Reset failed"
        exit 1
    }
    echo "✅ Reset to origin/$BRANCH successful"
fi

echo ""
echo "##########################################"
echo "### Verifying deployment"
echo "### $(date -u)"
echo "##########################################"

# Show current commit
echo "Current commit:"
git log -1 --oneline

# Verify key files exist
echo ""
echo "Verifying key files..."
KEY_FILES=(
    "src/agents/trading_agent.py"
    "src/nice_funcs_hyperliquid.py"
    "src/config.py"
)

ALL_OK=1
for file in "${KEY_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file MISSING"
        ALL_OK=0
    fi
done

# Quick syntax check on Python files
echo ""
echo "Running syntax checks..."
if python -m py_compile src/agents/trading_agent.py 2>&1; then
    echo "  ✅ trading_agent.py syntax OK"
else
    echo "  ❌ trading_agent.py syntax ERROR"
    ALL_OK=0
fi

if python -m py_compile src/nice_funcs_hyperliquid.py 2>&1; then
    echo "  ✅ nice_funcs_hyperliquid.py syntax OK"
else
    echo "  ❌ nice_funcs_hyperliquid.py syntax ERROR"
    ALL_OK=0
fi

echo ""
echo "##########################################"
if [ $ALL_OK -eq 1 ]; then
    echo "### ✅ Deployment Successful"
else
    echo "### ⚠️  Deployment completed with warnings"
fi
echo "### $(date -u)"
echo "##########################################"

# Restore stashed changes if any
if [ $STASHED -eq 1 ]; then
    echo ""
    echo "Note: Local changes were stashed. Run 'git stash pop' to restore them."
fi
