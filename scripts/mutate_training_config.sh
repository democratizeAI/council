#!/bin/bash
#
# 🚦 yq Mutation Script for Early-Stop Guard (Ticket #223)
# Safely mutates training configuration with automatic guard validation
#

set -euo pipefail

CONFIG_PATH="${1:-config/training.yml}"
BACKUP_PATH="${CONFIG_PATH}.backup.$(date +%s)"

usage() {
    echo "Usage: $0 [config_path] [key=value] [key2=value2] ..."
    echo ""
    echo "Examples:"
    echo "  $0 config/training.yml patience=5"
    echo "  $0 config/training.yml patience=3 min_delta=0.005 monitor=eval_accuracy"
    echo ""
    echo "Supported early_stopping keys:"
    echo "  - patience: Number of epochs to wait for improvement"
    echo "  - min_delta: Minimum change to qualify as improvement"
    echo "  - monitor: Metric to monitor (eval_loss, eval_accuracy, etc.)"
    echo "  - mode: min (for loss) or max (for accuracy)"
    echo "  - enabled: true/false"
    exit 1
}

validate_dependencies() {
    local missing_deps=()
    
    if ! command -v yq &> /dev/null; then
        missing_deps+=("yq")
    fi
    
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo "❌ Missing dependencies: ${missing_deps[*]}"
        echo "Install with: apt-get install yq python3-yaml"
        exit 1
    fi
}

backup_config() {
    if [ -f "$CONFIG_PATH" ]; then
        cp "$CONFIG_PATH" "$BACKUP_PATH"
        echo "📋 Backed up config to: $BACKUP_PATH"
    fi
}

apply_yq_mutations() {
    local mutations=("$@")
    
    echo "🔧 Applying yq mutations..."
    
    for mutation in "${mutations[@]}"; do
        if [[ "$mutation" =~ ^([a-z_]+)=(.+)$ ]]; then
            local key="${BASH_REMATCH[1]}"
            local value="${BASH_REMATCH[2]}"
            local yq_path=".training.early_stopping.${key}"
            
            echo "  Setting ${key} = ${value}"
            
            # Apply mutation with yq
            if [[ "$value" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
                # Numeric value
                yq eval "${yq_path} = ${value}" -i "$CONFIG_PATH"
            elif [[ "$value" =~ ^(true|false)$ ]]; then
                # Boolean value
                yq eval "${yq_path} = ${value}" -i "$CONFIG_PATH"
            else
                # String value
                yq eval "${yq_path} = \"${value}\"" -i "$CONFIG_PATH"
            fi
        else
            echo "❌ Invalid mutation format: $mutation"
            echo "Expected: key=value"
            exit 1
        fi
    done
}

validate_with_guard() {
    echo "🚦 Validating with early-stop guard..."
    
    # Create a Python validation script
    local validator=$(cat << 'EOF'
import sys
import os
sys.path.insert(0, os.getcwd())

from training.early_stop_guard import EarlyStopGuard

try:
    guard = EarlyStopGuard(sys.argv[1])
    is_safe, reason = guard.validate_early_stopping_config()
    
    if is_safe:
        print(f"✅ Configuration is safe: {reason}")
        report = guard.get_safety_report()
        print(f"📊 Settings: epochs={report['current_settings']['epochs']}, "
              f"patience={report['current_settings']['patience']}, "
              f"min_delta={report['current_settings']['min_delta']}")
        sys.exit(0)
    else:
        print(f"❌ Configuration is unsafe: {reason}")
        print("🔧 Attempting automatic fixes...")
        
        guarded_config = guard.apply_safety_guards()
        
        # Save the guarded config
        import yaml
        with open(sys.argv[1], 'w') as f:
            yaml.safe_dump(guarded_config, f, default_flow_style=False, indent=2)
        
        print("✅ Applied automatic safety guards")
        sys.exit(0)
        
except Exception as e:
    print(f"❌ Validation failed: {e}")
    sys.exit(1)
EOF
)
    
    python3 -c "$validator" "$CONFIG_PATH"
}

restore_backup() {
    if [ -f "$BACKUP_PATH" ]; then
        mv "$BACKUP_PATH" "$CONFIG_PATH"
        echo "🔄 Restored backup due to validation failure"
    fi
}

cleanup() {
    # Remove backup if validation succeeded
    if [ -f "$BACKUP_PATH" ]; then
        rm -f "$BACKUP_PATH"
        echo "🧹 Cleaned up backup file"
    fi
}

main() {
    if [ $# -lt 2 ]; then
        usage
    fi
    
    # Shift past config path
    shift
    
    echo "🎯 Mutating training config: $CONFIG_PATH"
    
    validate_dependencies
    backup_config
    
    # Apply mutations with error handling
    if apply_yq_mutations "$@"; then
        if validate_with_guard; then
            cleanup
            echo "🎉 Config mutation completed successfully!"
        else
            restore_backup
            exit 1
        fi
    else
        restore_backup
        exit 1
    fi
}

# Handle Ctrl+C gracefully
trap 'restore_backup; exit 130' INT

main "$@" 