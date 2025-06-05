# Agent-0 Service Wrapper

OS-level service wrapper for Agent-0 AutoGen Council that ensures automatic startup on boot and automatic restarts on failure.

## Quick Start

### Windows Installation

1. Run as Administrator: Right-click PowerShell and select "Run as Administrator"
2. Install the service: `.\services\install_windows.ps1`
3. Verify: `sc query Agent0Council`

### Linux Installation

1. Run with sudo: `sudo ./services/install_linux.sh`
2. Verify: `sudo systemctl status agent0`

## Service Management

### Windows Commands
- Start: `python services\agent0_service.py start`
- Stop: `python services\agent0_service.py stop`
- Status: `sc query Agent0Council`

### Linux Commands
- Start: `sudo systemctl start agent0`
- Stop: `sudo systemctl stop agent0`
- Status: `sudo systemctl status agent0`
- Logs: `sudo journalctl -u agent0 -f`

## Testing

Run smoke test: `python services/test_service_wrapper.py`

This validates:
- Health endpoint responsiveness
- Service status and management
- Basic Agent-0 functionality
- Startup time performance
- Prometheus metrics exposure

## Key Features

- Auto-start on boot (survives Windows Updates/Linux reboots)
- Automatic restart on process crash
- Health monitoring with Prometheus metrics
- Cross-platform support (Windows service + Linux systemd)
- Comprehensive logging for troubleshooting
- Production-ready security settings

## Monitoring

Health check: `curl http://localhost:8000/health`
Metrics: `curl http://localhost:8000/metrics | grep service_`

Key metrics:
- `service_startups_total`: Number of service restarts
- `service_up`: Service status (1=up, 0=down)

## Troubleshooting

### Service Won't Start
1. Check logs: `logs\agent0_service.log` (Windows) or `journalctl -u agent0` (Linux)
2. Verify Python path and dependencies
3. Test manually: `python app\main.py`

### Health Check Fails
1. Check port 8000 availability: `netstat -an | findstr :8000`
2. Verify firewall settings
3. Check GPU and CUDA installation

See full troubleshooting guide in the complete documentation.

## Next Steps

After service installation:
1. Tauri Desktop UI - point to `ws://localhost:8765`
2. Sandbox Adapter - layer code execution safety
3. Alerts & Paging - connect to service restart counts
4. Auto-updater - package for distribution
