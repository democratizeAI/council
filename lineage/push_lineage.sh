#!/usr/bin/env bash
set -euo pipefail

# Secure lineage push with integrity guarantees
echo "🔗 Pushing artifact lineage to IPFS..."

# Create timestamped artifact directory
ART_DIR="artifacts/$(date -u +%F_%H-%M-%S)"
mkdir -p "$ART_DIR"

# Ensure IPFS daemon is available
if ! curl -s http://127.0.0.1:5001/api/v0/version >/dev/null 2>&1; then
    echo "🐳 Starting IPFS daemon..."
    docker run -d --name ipfs-daemon -p 5001:5001 -p 4001:4001 ipfs/kubo:latest daemon --api /ip4/0.0.0.0/tcp/5001
    
    # Wait for daemon to be ready
    for i in {1..30}; do
        if curl -s http://127.0.0.1:5001/api/v0/version >/dev/null 2>&1; then
            echo "✓ IPFS daemon ready"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "❌ IPFS daemon failed to start"
            exit 1
        fi
        sleep 2
    done
fi

# Copy artifacts with verification
echo "📦 Collecting artifacts..."
if [ -d "docker" ] && ls docker/*.tar.gz >/dev/null 2>&1; then
    cp docker/*.tar.gz "$ART_DIR/"
elif command -v docker >/dev/null && docker images --format "table {{.Repository}}:{{.Tag}}" | grep -v REPOSITORY | head -1 >/dev/null; then
    echo "🏗️ No tar.gz found, capturing image digests..."
    docker images --format "{{.Repository}}:{{.Tag}}@{{.ID}}" > "$ART_DIR/image_digests.txt"
else
    echo "⚠️ No Docker artifacts found, creating placeholder"
    echo "no-artifacts-$(date -Is)" > "$ART_DIR/placeholder.txt"
fi

# Copy additional build artifacts
[ -f "requirements.txt" ] && cp requirements.txt "$ART_DIR/"
[ -f "package.json" ] && cp package.json "$ART_DIR/"
[ -f "Dockerfile" ] && cp Dockerfile "$ART_DIR/"

# Generate integrity checksums
echo "🔒 Generating integrity checksums..."
pushd "$ART_DIR" >/dev/null

# Create checksums with strict verification
if ! sha256sum --strict * > sha256sums.txt 2>/dev/null; then
    echo "❌ Checksum generation failed - files may have changed during copy"
    exit 1
fi

# Add metadata
cat > metadata.json <<EOF
{
    "timestamp": "$(date -Is)",
    "hostname": "$(hostname)",
    "git_commit": "${GITHUB_SHA:-$(git rev-parse HEAD 2>/dev/null || echo 'unknown')}",
    "git_branch": "${GITHUB_REF_NAME:-$(git branch --show-current 2>/dev/null || echo 'unknown')}",
    "build_env": "${CI:-false}"
}
EOF

# Push to IPFS and get root directory CID
echo "📡 Pushing to IPFS..."
if ! command -v ipfs >/dev/null; then
    # Use docker if ipfs binary not available
    CID=$(docker run --rm -v "$(pwd)":/data ipfs/kubo:latest add -Qr /data)
else
    CID=$(ipfs add -Qr .)  # -Q quiet, -r recursive, returns root CID only
fi

popd >/dev/null

# Validate CID format
if [[ ! "$CID" =~ ^Qm[1-9A-HJ-NP-Za-km-z]{44}$ ]] && [[ ! "$CID" =~ ^bafy[0-9a-z]{55}$ ]]; then
    echo "❌ Invalid CID format: $CID"
    exit 1
fi

echo "✓ Artifacts pushed to IPFS: $CID"

# Append to lineage log with proper JSON escaping
echo "📝 Updating lineage log..."
mkdir -p lineage
jq -nc \
    --arg timestamp "$(date -Is)" \
    --arg cid "$CID" \
    --arg commit "${GITHUB_SHA:-$(git rev-parse HEAD 2>/dev/null || echo 'unknown')}" \
    --arg branch "${GITHUB_REF_NAME:-$(git branch --show-current 2>/dev/null || echo 'unknown')}" \
    '{
        timestamp: $timestamp,
        cid: $cid,
        git_commit: $commit,
        git_branch: $branch,
        artifact_count: 1
    }' >> lineage/lineage_log.jsonl

# Push metric to Prometheus Pushgateway
echo "📊 Updating Prometheus metrics..."
if curl -s http://pushgateway:9091 >/dev/null 2>&1; then
    printf "lineage_last_push_timestamp %d\n" "$(date +%s)" | \
        curl --silent --fail --data-binary @- \
        http://pushgateway:9091/metrics/job/lineage/instance/$(hostname) || {
        echo "⚠️ Failed to push metrics to Pushgateway"
    }
else
    echo "⚠️ Pushgateway not available, skipping metric push"
fi

# Notify Slack with secure JSON
if [ -n "${SLACK_LINEAGE_WEBHOOK:-}" ]; then
    echo "📢 Notifying Slack..."
    jq -nc \
        --arg cid "$CID" \
        --arg env "${ENVIRONMENT:-prod}" \
        --arg branch "${GITHUB_REF_NAME:-$(git branch --show-current 2>/dev/null || echo 'unknown')}" \
        '{
            text: ("🔗 Lineage pushed: " + $cid),
            blocks: [{
                type: "section",
                fields: [
                    {type: "mrkdwn", text: ("*CID:* `" + $cid + "`")},
                    {type: "mrkdwn", text: ("*Environment:* " + $env)},
                    {type: "mrkdwn", text: ("*Branch:* " + $branch)},
                    {type: "mrkdwn", text: ("*IPFS Gateway:* https://ipfs.io/ipfs/" + $cid)}
                ]
            }]
        }' | \
        curl --silent --fail \
            -H 'Content-Type: application/json' \
            -d @- "$SLACK_LINEAGE_WEBHOOK" || {
        echo "⚠️ Failed to send Slack notification"
    }
else
    echo "⚠️ SLACK_LINEAGE_WEBHOOK not set, skipping notification"
fi

# Cleanup IPFS daemon if we started it
if docker ps --format "{{.Names}}" | grep -q "^ipfs-daemon$"; then
    echo "🧹 Cleaning up IPFS daemon..."
    docker stop ipfs-daemon >/dev/null 2>&1 || true
    docker rm ipfs-daemon >/dev/null 2>&1 || true
fi

echo "✅ Lineage push complete!"
echo "   CID: $CID"
echo "   Gateway: https://ipfs.io/ipfs/$CID"
echo "   Log: lineage/lineage_log.jsonl" 