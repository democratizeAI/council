#!/usr/bin/env python3
"""
Simple Metrics Server for VRAM Alert Testing
Exposes metrics on /metrics endpoint for Prometheus scraping
"""
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from prometheus_client import generate_latest, Gauge, CONTENT_TYPE_LATEST

# Create VRAM metric
vram_usage_gauge = Gauge('swarm_gpu_memory_used_percent', 'GPU memory usage percentage')

# Global VRAM value that we can control
current_vram_percent = 25.0

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            # Update the metric with current value
            vram_usage_gauge.set(current_vram_percent)
            
            # Generate Prometheus format response
            output = generate_latest()
            self.send_response(200)
            self.send_header('Content-Type', CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(output)
            print(f"📊 Served metrics: VRAM = {current_vram_percent}%")
        elif self.path.startswith('/set_vram/'):
            # Allow setting VRAM via HTTP: /set_vram/85
            try:
                global current_vram_percent
                vram_value = float(self.path.split('/')[-1])
                current_vram_percent = vram_value
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"VRAM set to {vram_value}%\n".encode())
                print(f"🔧 VRAM manually set to {vram_value}%")
            except ValueError:
                self.send_response(400)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b"Invalid VRAM value\n")
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK\n")
        else:
            self.send_response(404)
            self.end_headers()

def run_escalation_test():
    """Run the automatic escalation test sequence"""
    global current_vram_percent
    
    print("🚀 Starting Automatic VRAM Escalation Test")
    print("==========================================")
    time.sleep(2)
    
    # Step 1: Warning (78%)
    print("⚠️  STEP 1: Setting VRAM to 78% (Warning threshold)")
    current_vram_percent = 78.0
    print("   ⏳ Waiting 3 minutes for warning alert...")
    time.sleep(180)  # 3 minutes
    
    # Step 2: Critical (88%)
    print("🚨 STEP 2: Setting VRAM to 88% (Critical threshold)")
    current_vram_percent = 88.0
    print("   ⏳ Waiting 2 minutes for critical alert...")
    time.sleep(120)  # 2 minutes
    
    # Step 3: Emergency (97%)
    print("🔥 STEP 3: Setting VRAM to 97% (Emergency threshold)")
    current_vram_percent = 97.0
    print("   ⏳ Waiting 30 seconds for emergency alert...")
    time.sleep(30)   # 30 seconds
    
    # Cleanup
    print("✅ CLEANUP: Resetting VRAM to 25%")
    current_vram_percent = 25.0
    
    print("\n🎉 Alert escalation test complete!")
    print("Check alerts at: http://localhost:9090/alerts")
    print("Check AlertManager: http://localhost:9093")

def start_server(port=8080):
    """Start the metrics server"""
    server = HTTPServer(('0.0.0.0', port), MetricsHandler)
    print(f"🚀 Metrics server starting on port {port}")
    print(f"📊 Metrics endpoint: http://localhost:{port}/metrics")
    print(f"🔧 Manual control: http://localhost:{port}/set_vram/VALUE")
    print(f"🏥 Health check: http://localhost:{port}/health")
    server.serve_forever()

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="VRAM Metrics Server for Alert Testing")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    parser.add_argument("--escalation-test", action="store_true", help="Run automatic escalation test")
    parser.add_argument("--vram", type=float, help="Set initial VRAM percentage")
    
    args = parser.parse_args()
    
    if args.vram:
        current_vram_percent = args.vram
        print(f"📊 Initial VRAM set to {args.vram}%")
    
    if args.escalation_test:
        # Start escalation test in background thread
        test_thread = threading.Thread(target=run_escalation_test, daemon=True)
        test_thread.start()
    
    try:
        start_server(args.port)
    except KeyboardInterrupt:
        print("\n👋 Metrics server stopped") 