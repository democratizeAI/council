#!/bin/bash
# GitHub Branch Sweep - Weekly Housekeeping Script
# Usage: ./scripts/gh_branch_sweep.sh [--dry-run]

set -e

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "🔍 DRY RUN MODE - No changes will be made"
fi

echo "🧹 GitHub Branch Sweep - Weekly Housekeeping"
echo "=============================================="

# Fetch latest changes
git fetch --all --prune

# Find merged branches (exclude main/master/prod/stable*)
echo "📋 Finding merged branches..."
MERGED_BRANCHES=$(git branch -r --merged origin/master | \
    grep -v -E "(master|main|prod|stable)" | \
    grep -v "origin/HEAD" | \
    sed 's/origin\///' | \
    xargs)

if [[ -z "$MERGED_BRANCHES" ]]; then
    echo "✅ No merged branches to clean up!"
    exit 0
fi

echo "🎯 Found merged branches to clean up:"
for branch in $MERGED_BRANCHES; do
    echo "  - $branch"
done

if [[ "$DRY_RUN" == "true" ]]; then
    echo "🔍 DRY RUN: Would delete ${#MERGED_BRANCHES[@]} merged branches"
    exit 0
fi

# Confirm deletion
echo ""
read -p "⚠️  Delete these merged branches? [y/N]: " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Aborted - no branches deleted"
    exit 0
fi

# Delete merged branches
echo "🗑️  Deleting merged branches..."
for branch in $MERGED_BRANCHES; do
    echo "   Deleting origin/$branch..."
    if git push origin --delete "$branch" 2>/dev/null; then
        echo "   ✅ Deleted origin/$branch"
    else
        echo "   ⚠️  Failed to delete origin/$branch (may already be gone)"
    fi
done

# Show final state
echo ""
echo "📊 Branch cleanup complete!"
echo "   Active branches remaining:"
git branch -r | grep -v -E "(HEAD|merged)" | wc -l | xargs echo "   -"

echo ""
echo "🏆 Repository cleanup successful!"
echo "   Next run: git fetch --all --prune && git pull" 