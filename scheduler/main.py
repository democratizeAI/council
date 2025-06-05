#!/usr/bin/env python3
"""
NVML VRAM Metrics Exporter (Ticket #206 - Hybrid Implementation)
Provides high-resolution GPU memory metrics via Prometheus endpoint.
Control actions handled by host systemd timer.
"""

import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import pynvml

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; version=0.0.4; charset=utf-8')
            self.end_headers()
            
            try:
                metrics = self.collect_gpu_metrics()
                self.wfile.write(metrics.encode('utf-8'))
            except Exception as e:
                logger.error(f"Failed to collect metrics: {e}")
                self.wfile.write(b"# ERROR: Failed to collect GPU metrics\n")
        
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK\n")
        
        else:
            self.send_response(404)
            self.end_headers()

    def collect_gpu_metrics(self):
        """Collect GPU VRAM metrics using NVML"""
        metrics = []
        
        # Add help and type metadata
        metrics.append("# HELP gpu_vram_used_mb GPU VRAM usage in megabytes")
        metrics.append("# TYPE gpu_vram_used_mb gauge")
        metrics.append("# HELP gpu_vram_total_mb Total GPU VRAM in megabytes")
        metrics.append("# TYPE gpu_vram_total_mb gauge")
        metrics.append("# HELP gpu_vram_utilization GPU VRAM utilization percentage")
        metrics.append("# TYPE gpu_vram_utilization gauge")
        
        try:
            # Get number of GPUs
            device_count = pynvml.nvmlDeviceGetCount()
            
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                
                # Get memory info
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                used_mb = mem_info.used // (1024 * 1024)
                total_mb = mem_info.total // (1024 * 1024)
                utilization = (mem_info.used / mem_info.total) * 100
                
                # Get device name for labeling
                try:
                    name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                except:
                    name = f"gpu{i}"
                
                # Export metrics with GPU index and name labels
                metrics.append(f'gpu_vram_used_mb{{gpu="{i}",name="{name}"}} {used_mb}')
                metrics.append(f'gpu_vram_total_mb{{gpu="{i}",name="{name}"}} {total_mb}')
                metrics.append(f'gpu_vram_utilization{{gpu="{i}",name="{name}"}} {utilization:.2f}')
                
                logger.debug(f"GPU {i} ({name}): {used_mb}MB / {total_mb}MB ({utilization:.1f}%)")
        
        except Exception as e:
            logger.error(f"NVML error: {e}")
            # Export error metric
            metrics.append('gpu_vram_used_mb{gpu="0"} 0')
            metrics.append('# ERROR: NVML collection failed')
        
        return '\n'.join(metrics) + '\n'

    def log_message(self, format, *args):
        # Suppress HTTP request logging for /metrics endpoint
        if '/metrics' not in args[0]:
            logger.info(format % args)

def main():
    # Initialize NVML
    try:
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        logger.info(f"NVML initialized successfully. Found {device_count} GPU(s)")
        
        # Log GPU details
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
            logger.info(f"GPU {i}: {name}")
            
    except Exception as e:
        logger.error(f"Failed to initialize NVML: {e}")
        logger.error("Make sure NVIDIA drivers are installed and accessible")
        return 1

    # Start HTTP server
    port = 8000
    server = HTTPServer(('0.0.0.0', port), MetricsHandler)
    
    logger.info(f"🚀 NVML VRAM metrics exporter started on port {port}")
    logger.info(f"📊 Metrics endpoint: http://localhost:{port}/metrics")
    logger.info(f"❤️ Health endpoint: http://localhost:{port}/health")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down metrics exporter...")
        server.shutdown()
        pynvml.nvmlShutdown()
        return 0

if __name__ == '__main__':
    exit(main()) 