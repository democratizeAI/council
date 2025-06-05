#!/bin/bash
# 🎯 Ticket #222 - 5xx Noise-Window Fix
# Adds 'for: 3m' to API5xxSpike alert to prevent false positive noise

set -euo pipefail

ALERT_FILE="monitoring/api_alert.yml"

echo "🔧 Applying 5xx noise-window fix to $ALERT_FILE..."

# Safety check: Ensure alert file exists
if [[ ! -f "$ALERT_FILE" ]]; then
    echo "❌ Alert file $ALERT_FILE not found"
    exit 1
fi

# Guard: Check if 'for:' already exists in API5xxSpike section
echo "🔍 Checking for existing 'for:' clause in API5xxSpike..."
if grep -A 10 -B 2 "alert: API5xxSpike" "$ALERT_FILE" | grep -q "for:"; then
    echo "⚠️  'for:' clause already exists in API5xxSpike alert - skipping"
    grep -A 10 -B 2 "alert: API5xxSpike" "$ALERT_FILE"
    exit 0
fi

# Backup original file
cp "$ALERT_FILE" "${ALERT_FILE}.backup"
echo "📄 Created backup: ${ALERT_FILE}.backup"

# Apply the improved sed patch
# This version only inserts 'for: 3m' if it's missing
echo "🔨 Applying sed patch to add noise window..."
sed -i '/alert: API5xxSpike/{:a;n;/expr:/n;/for:/b; s/^/    for: 3m\n/;b}' "$ALERT_FILE"

# Verify the change was applied
echo "✅ Checking the modification..."
if grep -A 5 "alert: API5xxSpike" "$ALERT_FILE" | grep -q "for: 3m"; then
    echo "✅ Successfully added 'for: 3m' to API5xxSpike alert"
    echo ""
    echo "📋 Updated alert configuration:"
    grep -A 8 "alert: API5xxSpike" "$ALERT_FILE"
else
    echo "❌ Failed to apply patch - restoring backup"
    mv "${ALERT_FILE}.backup" "$ALERT_FILE"
    exit 1
fi

echo ""
echo "🎯 Next steps:"
echo "1. Reload Prometheus: scripts/reload_prometheus.sh"
echo "2. Verify reload: curl http://localhost:9090/-/reload"
echo "3. Test alert: scripts/test_5xx_alert.sh" 