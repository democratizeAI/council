#!/bin/bash
# Post-installation script for Agent-0 service
# Configures firewall, SELinux, and system permissions for production deployment

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/agent0-postinstall.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

echo_log "${BLUE}🔧 Agent-0 Post-Installation Configuration${NC}"
echo_log "============================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo_log "${RED}❌ This script must be run as root${NC}"
   echo "Usage: sudo $0"
   exit 1
fi

# Detect distribution
if [ -f /etc/redhat-release ]; then
    DISTRO="rhel"
    FIREWALL_CMD="firewall-cmd"
elif [ -f /etc/debian_version ]; then
    DISTRO="debian"
    FIREWALL_CMD="ufw"
else
    echo_log "${YELLOW}⚠️ Unknown distribution, attempting generic configuration${NC}"
    DISTRO="unknown"
fi

echo_log "📋 Detected distribution: $DISTRO"

# Function to configure firewall
configure_firewall() {
    echo_log "${BLUE}🔥 Configuring firewall rules...${NC}"
    
    case $DISTRO in
        "rhel")
            # RHEL/CentOS/Fedora - firewalld
            if systemctl is-active --quiet firewalld; then
                echo_log "📋 Using firewalld (RHEL/CentOS/Fedora)"
                
                # Open required ports locally
                firewall-cmd --add-port=8000/tcp --permanent    # Agent-0 API
                firewall-cmd --add-port=8765/tcp --permanent    # WebSocket
                firewall-cmd --add-port=9091/tcp --permanent    # Prometheus metrics
                firewall-cmd --reload
                
                echo_log "${GREEN}✅ Firewall rules added:${NC}"
                echo_log "   - 8000/tcp (Agent-0 API)"
                echo_log "   - 8765/tcp (WebSocket)"
                echo_log "   - 9091/tcp (Prometheus metrics)"
            else
                echo_log "${YELLOW}⚠️ firewalld not running, skipping firewall configuration${NC}"
            fi
            ;;
            
        "debian")
            # Ubuntu/Debian - ufw
            if command -v ufw >/dev/null 2>&1; then
                echo_log "📋 Using ufw (Ubuntu/Debian)"
                
                # Enable UFW if not already enabled
                ufw --force enable
                
                # Open required ports
                ufw allow 8000/tcp comment "Agent-0 API"
                ufw allow 8765/tcp comment "Agent-0 WebSocket"  
                ufw allow 9091/tcp comment "Agent-0 Metrics"
                
                echo_log "${GREEN}✅ UFW rules added:${NC}"
                echo_log "   - 8000/tcp (Agent-0 API)"
                echo_log "   - 8765/tcp (WebSocket)"
                echo_log "   - 9091/tcp (Prometheus metrics)"
            else
                echo_log "${YELLOW}⚠️ ufw not available, skipping firewall configuration${NC}"
            fi
            ;;
            
        *)
            echo_log "${YELLOW}⚠️ Unknown firewall system, please manually open ports:${NC}"
            echo_log "   - 8000/tcp (Agent-0 API)"
            echo_log "   - 8765/tcp (WebSocket)"
            echo_log "   - 9091/tcp (Prometheus metrics)"
            ;;
    esac
}

# Function to configure SELinux
configure_selinux() {
    echo_log "${BLUE}🛡️ Configuring SELinux...${NC}"
    
    if command -v getenforce >/dev/null 2>&1; then
        SELINUX_STATUS=$(getenforce)
        echo_log "📋 SELinux status: $SELINUX_STATUS"
        
        if [[ "$SELINUX_STATUS" == "Enforcing" ]]; then
            echo_log "🔒 Configuring SELinux policies for Agent-0"
            
            # Set context for model directory
            if [ -d "/opt/agent0/models" ]; then
                chcon -R -t svirt_sandbox_file_t /opt/agent0/models
                echo_log "${GREEN}✅ Set SELinux context for /opt/agent0/models${NC}"
            fi
            
            # Set context for data directory
            if [ -d "/opt/agent0/data" ]; then
                chcon -R -t svirt_sandbox_file_t /opt/agent0/data
                echo_log "${GREEN}✅ Set SELinux context for /opt/agent0/data${NC}"
            fi
            
            # Set context for logs directory
            if [ -d "/opt/agent0/logs" ]; then
                chcon -R -t var_log_t /opt/agent0/logs
                echo_log "${GREEN}✅ Set SELinux context for /opt/agent0/logs${NC}"
            fi
            
            # Allow network access for the service
            setsebool -P httpd_can_network_connect 1
            echo_log "${GREEN}✅ Enabled SELinux network access${NC}"
            
        else
            echo_log "${YELLOW}⚠️ SELinux not enforcing, skipping policy configuration${NC}"
        fi
    else
        echo_log "📋 SELinux not available on this system"
    fi
}

# Function to set up log rotation
configure_log_rotation() {
    echo_log "${BLUE}📜 Configuring log rotation...${NC}"
    
    # Create logrotate configuration
    cat > /etc/logrotate.d/agent0 << 'EOF'
/opt/agent0/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        systemctl reload agent0 >/dev/null 2>&1 || true
    endscript
}

/var/log/agent0-*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
}
EOF
    
    echo_log "${GREEN}✅ Log rotation configured${NC}"
    echo_log "   - Application logs: 14 days retention"
    echo_log "   - System logs: 7 days retention"
}

# Function to create swap if needed (for low-memory systems)
configure_swap() {
    echo_log "${BLUE}💾 Checking swap configuration...${NC}"
    
    MEMORY_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    MEMORY_GB=$((MEMORY_KB / 1024 / 1024))
    SWAP_KB=$(grep SwapTotal /proc/meminfo | awk '{print $2}')
    SWAP_GB=$((SWAP_KB / 1024 / 1024))
    
    echo_log "📋 System memory: ${MEMORY_GB}GB, Swap: ${SWAP_GB}GB"
    
    # If system has < 8GB RAM and no swap, create swap
    if [[ $MEMORY_GB -lt 8 && $SWAP_GB -eq 0 ]]; then
        echo_log "${YELLOW}⚠️ Low memory system detected, creating swap file${NC}"
        
        # Create 4GB swap file
        dd if=/dev/zero of=/opt/agent0-swap bs=1M count=4096 status=progress
        chmod 600 /opt/agent0-swap
        mkswap /opt/agent0-swap
        swapon /opt/agent0-swap
        
        # Add to fstab
        echo "/opt/agent0-swap none swap sw 0 0" >> /etc/fstab
        
        echo_log "${GREEN}✅ Created 4GB swap file at /opt/agent0-swap${NC}"
    else
        echo_log "${GREEN}✅ Swap configuration adequate${NC}"
    fi
}

# Function to set up GPU permissions
configure_gpu() {
    echo_log "${BLUE}🎮 Configuring GPU access...${NC}"
    
    # Check if NVIDIA GPU is present
    if command -v nvidia-smi >/dev/null 2>&1; then
        echo_log "📋 NVIDIA GPU detected"
        
        # Add agent0 user to video group
        if id "agent0" >/dev/null 2>&1; then
            usermod -a -G video agent0
            echo_log "${GREEN}✅ Added agent0 user to video group${NC}"
        fi
        
        # Set up nvidia-persistenced if available
        if systemctl list-unit-files | grep -q nvidia-persistenced; then
            systemctl enable nvidia-persistenced
            systemctl start nvidia-persistenced
            echo_log "${GREEN}✅ Enabled nvidia-persistenced service${NC}"
        fi
        
        # Check GPU memory
        GPU_MEMORY=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
        echo_log "📋 GPU memory: ${GPU_MEMORY}MB"
        
    else
        echo_log "${YELLOW}⚠️ No NVIDIA GPU detected${NC}"
    fi
}

# Function to validate installation
validate_installation() {
    echo_log "${BLUE}✅ Validating installation...${NC}"
    
    # Check service files
    for service in agent0 swarm-metrics; do
        if [ -f "/etc/systemd/system/${service}.service" ]; then
            echo_log "${GREEN}✅ Service file exists: ${service}.service${NC}"
        else
            echo_log "${YELLOW}⚠️ Service file missing: ${service}.service${NC}"
        fi
    done
    
    # Check directories
    for dir in "/opt/agent0" "/opt/agent0/logs" "/opt/agent0/data" "/opt/agent0/models"; do
        if [ -d "$dir" ]; then
            echo_log "${GREEN}✅ Directory exists: $dir${NC}"
        else
            echo_log "${YELLOW}⚠️ Directory missing: $dir${NC}"
        fi
    done
    
    # Check agent0 user
    if id "agent0" >/dev/null 2>&1; then
        echo_log "${GREEN}✅ User agent0 exists${NC}"
    else
        echo_log "${YELLOW}⚠️ User agent0 missing${NC}"
    fi
}

# Main execution
main() {
    echo_log "🚀 Starting post-installation configuration..."
    
    configure_firewall
    configure_selinux
    configure_log_rotation
    configure_swap
    configure_gpu
    validate_installation
    
    echo_log ""
    echo_log "${GREEN}🎉 Agent-0 post-installation complete!${NC}"
    echo_log ""
    echo_log "📋 Next steps:"
    echo_log "1. Start services: systemctl start agent0 swarm-metrics"
    echo_log "2. Enable auto-start: systemctl enable agent0 swarm-metrics"
    echo_log "3. Check status: systemctl status agent0"
    echo_log "4. View logs: journalctl -u agent0 -f"
    echo_log ""
    echo_log "🌐 Access points:"
    echo_log "- API: http://localhost:8000/health"
    echo_log "- Metrics: http://localhost:9091/metrics"
    echo_log "- WebSocket: ws://localhost:8765"
    echo_log ""
    echo_log "📊 Monitoring:"
    echo_log "- Logs: /opt/agent0/logs/"
    echo_log "- Config: /opt/agent0/config/"
    echo_log "- Models: /opt/agent0/models/"
}

# Trap errors
trap 'echo_log "${RED}❌ Post-installation failed at line $LINENO${NC}"; exit 1' ERR

# Run main function
main "$@" 