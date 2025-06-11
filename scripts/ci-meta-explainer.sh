#!/bin/bash
# scripts/ci-meta-explainer.sh - QA-301 CI Integration
# Runs after Sonnet generates PR to add meta explanation hash

set -euo pipefail

# Configuration
META_EXPLAINER_SCRIPT="${META_EXPLAINER_SCRIPT:-tools/explain_meta.py}"
PROMETHEUS_GATEWAY="${PROMETHEUS_GATEWAY:-localhost:9091}"
PR_META_DIR="${PR_META_DIR:-/pr_meta}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧠 QA-301: Meta Explainer CI Integration${NC}"
echo "============================================"

# Function to log with timestamp
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if meta explanation already exists
check_existing_meta() {
    if [[ -f "meta_hash.yaml" ]]; then
        log "${YELLOW}⚠️ meta_hash.yaml already exists, checking validity${NC}"
        
        # Validate existing meta hash
        if python3 -c "
import yaml
import sys
try:
    with open('meta_hash.yaml') as f:
        data = yaml.safe_load(f)
    required_fields = ['meta_hash', 'summary', 'logic_change_type', 'affected_modules']
    if all(field in data for field in required_fields):
        print('VALID')
        sys.exit(0)
    else:
        print('INVALID')
        sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
"; then
            log "${GREEN}✅ Existing meta_hash.yaml is valid${NC}"
            return 0
        else
            log "${RED}❌ Existing meta_hash.yaml is invalid, regenerating${NC}"
            rm -f meta_hash.yaml
            return 1
        fi
    else
        log "${BLUE}📝 No meta_hash.yaml found, generating new one${NC}"
        return 1
    fi
}

# Function to extract PR intent from commit messages or branch name
extract_intent() {
    local intent=""
    
    # Try to extract from commit message
    if git log --oneline -1 | grep -E "(Intent:|intent:)" > /dev/null 2>&1; then
        intent=$(git log --oneline -1 | sed -n 's/.*[Ii]ntent: *\([^|]*\).*/\1/p' | head -1)
    fi
    
    # Fallback to branch name
    if [[ -z "$intent" ]]; then
        local branch_name=$(git rev-parse --abbrev-ref HEAD)
        if [[ "$branch_name" =~ sws-scaffold-(.+)-[0-9]+ ]]; then
            intent="Scaffold ${BASH_REMATCH[1]} agent"
        elif [[ "$branch_name" =~ feature/(.+) ]]; then
            intent="Feature: ${BASH_REMATCH[1]}"
        else
            intent="Code changes for PR"
        fi
    fi
    
    echo "$intent"
}

# Function to generate meta explanation
generate_meta_explanation() {
    local intent="$1"
    
    log "${BLUE}🔄 Generating meta explanation...${NC}"
    log "Intent: $intent"
    
    # Check if explain_meta.py exists
    if [[ ! -f "$META_EXPLAINER_SCRIPT" ]]; then
        log "${RED}❌ Meta explainer script not found: $META_EXPLAINER_SCRIPT${NC}"
        return 1
    fi
    
    # Run meta explainer
    if timeout 60 python3 "$META_EXPLAINER_SCRIPT" \
        --intent="$intent" \
        --output=meta_hash.yaml \
        --verbose; then
        
        log "${GREEN}✅ Meta explanation generated successfully${NC}"
        
        # Display generated meta hash
        if [[ -f "meta_hash.yaml" ]]; then
            local meta_hash=$(grep "meta_hash:" meta_hash.yaml | cut -d' ' -f2)
            local summary=$(grep "summary:" meta_hash.yaml | cut -d' ' -f2- | tr -d '"')
            log "${GREEN}📋 Meta Hash: $meta_hash${NC}"
            log "${GREEN}📝 Summary: $summary${NC}"
        fi
        
        return 0
    else
        log "${RED}❌ Meta explanation generation failed${NC}"
        return 1
    fi
}

# Function to store meta hash in PR metadata directory
store_pr_metadata() {
    if [[ ! -f "meta_hash.yaml" ]]; then
        log "${RED}❌ meta_hash.yaml not found, cannot store metadata${NC}"
        return 1
    fi
    
    # Create PR metadata directory
    local pr_sha=$(git rev-parse HEAD)
    local pr_cid="${pr_sha:0:12}"
    local meta_dir="$PR_META_DIR/$pr_cid"
    
    if mkdir -p "$meta_dir" 2>/dev/null; then
        cp meta_hash.yaml "$meta_dir/meta_hash.yaml"
        log "${GREEN}✅ PR metadata stored in $meta_dir${NC}"
    else
        log "${YELLOW}⚠️ Failed to create PR metadata directory, continuing...${NC}"
    fi
}

# Function to validate meta hash format
validate_meta_hash() {
    if [[ ! -f "meta_hash.yaml" ]]; then
        log "${RED}❌ meta_hash.yaml not found for validation${NC}"
        return 1
    fi
    
    log "${BLUE}🔍 Validating meta hash format...${NC}"
    
    # Use Python to validate the YAML structure
    if python3 -c "
import yaml
import re
import sys

try:
    with open('meta_hash.yaml') as f:
        data = yaml.safe_load(f)
    
    # Check required fields
    required_fields = ['meta_hash', 'summary', 'logic_change_type', 'affected_modules', 'intent', 'timestamp', 'model', 'deterministic']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        print(f'Missing required fields: {missing_fields}')
        sys.exit(1)
    
    # Validate meta_hash format (8 hex characters)
    if not re.match(r'^[a-f0-9]{8}$', data['meta_hash']):
        print(f'Invalid meta_hash format: {data[\"meta_hash\"]}')
        sys.exit(1)
    
    # Validate change type
    valid_types = ['feature', 'bugfix', 'refactor', 'performance', 'security', 'config']
    if data['logic_change_type'] not in valid_types:
        print(f'Invalid change type: {data[\"logic_change_type\"]}')
        sys.exit(1)
    
    # Validate summary length
    if len(data['summary']) < 10 or len(data['summary']) > 200:
        print(f'Invalid summary length: {len(data[\"summary\"])} characters')
        sys.exit(1)
    
    # Validate deterministic flag
    if not data['deterministic']:
        print('Meta explanation is not marked as deterministic')
        sys.exit(1)
    
    print('VALID')
    sys.exit(0)
    
except Exception as e:
    print(f'Validation error: {e}')
    sys.exit(1)
"; then
        log "${GREEN}✅ Meta hash validation passed${NC}"
        return 0
    else
        log "${RED}❌ Meta hash validation failed${NC}"
        return 1
    fi
}

# Function to publish metrics
publish_metrics() {
    local result="$1"
    local change_type="$2"
    
    # Push metrics to Prometheus gateway
    if command -v curl > /dev/null 2>&1; then
        cat << EOF | curl -X POST --data-binary @- "http://$PROMETHEUS_GATEWAY/metrics/job/ci_meta_explainer" || true
# TYPE ci_meta_explanation_total counter
ci_meta_explanation_total{result="$result",change_type="$change_type"} 1
# TYPE ci_meta_explanation_timestamp gauge  
ci_meta_explanation_timestamp $(date +%s)
EOF
        log "${GREEN}📊 Metrics published to Prometheus${NC}"
    else
        log "${YELLOW}⚠️ curl not available, skipping metrics${NC}"
    fi
}

# Main execution
main() {
    log "${BLUE}Starting meta explainer CI integration${NC}"
    
    # Change to repository root
    cd "$(git rev-parse --show-toplevel)" || {
        log "${RED}❌ Not in a git repository${NC}"
        exit 1
    }
    
    # Check if we need to generate meta explanation
    if check_existing_meta; then
        log "${GREEN}✅ Valid meta explanation already exists, skipping generation${NC}"
        exit 0
    fi
    
    # Extract intent
    local intent=$(extract_intent)
    log "${BLUE}📋 Extracted intent: $intent${NC}"
    
    # Generate meta explanation
    if generate_meta_explanation "$intent"; then
        log "${GREEN}✅ Meta explanation generation completed${NC}"
    else
        log "${RED}❌ Meta explanation generation failed${NC}"
        publish_metrics "error" "unknown"
        exit 1
    fi
    
    # Validate generated meta hash
    if validate_meta_hash; then
        log "${GREEN}✅ Meta hash validation completed${NC}"
    else
        log "${RED}❌ Meta hash validation failed${NC}"
        publish_metrics "invalid" "unknown"
        exit 1
    fi
    
    # Store metadata
    store_pr_metadata
    
    # Extract change type for metrics
    local change_type=$(grep "logic_change_type:" meta_hash.yaml | cut -d' ' -f2 | tr -d '"')
    
    # Publish success metrics
    publish_metrics "success" "$change_type"
    
    # Add meta_hash.yaml to git
    git add meta_hash.yaml || {
        log "${YELLOW}⚠️ Failed to stage meta_hash.yaml${NC}"
    }
    
    log "${GREEN}🎉 Meta explainer CI integration completed successfully${NC}"
    echo "============================================"
}

# Error handler
error_handler() {
    log "${RED}❌ Script failed on line $1${NC}"
    publish_metrics "error" "unknown"
    exit 1
}

# Set error trap
trap 'error_handler $LINENO' ERR

# Run main function
main "$@" 