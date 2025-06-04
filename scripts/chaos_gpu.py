#!/usr/bin/env python3
"""
🧨 Chaos GPU - Controlled VRAM spike testing
Artificially increases GPU memory usage to test alert thresholds
"""

import time
import logging
import argparse
import subprocess
import threading
from typing import Optional
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChaosGPU:
    """Chaos engineering for GPU memory alerts"""
    
    def __init__(self):
        self.allocations = []
        self.target_usage = 0
        self.running = False
        self.thread = None
        
    def get_current_vram_usage(self) -> float:
        """Get current VRAM usage percentage"""
        try:
            # Try nvidia-smi first
            result = subprocess.run([
                'nvidia-smi', '--query-gpu=memory.used,memory.total', 
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if lines:
                    used, total = map(int, lines[0].split(', '))
                    usage_pct = (used / total) * 100
                    logger.info(f"📊 Current VRAM: {used}MB / {total}MB ({usage_pct:.1f}%)")
                    return usage_pct
        except Exception as e:
            logger.warning(f"nvidia-smi failed: {e}")
        
        # Fallback to mock data for testing
        logger.warning("🔄 Using mock VRAM data (no GPU detected)")
        return 45.0  # Mock baseline usage
    
    def simulate_vram_spike(self, target_percent: float, duration: int = 300):
        """Simulate VRAM usage spike"""
        logger.info(f"🧨 Starting VRAM chaos spike to {target_percent}%")
        
        current_usage = self.get_current_vram_usage()
        
        # If we have a real GPU, try to allocate memory
        if self.has_gpu():
            try:
                import torch
                if torch.cuda.is_available():
                    self._allocate_gpu_memory(target_percent)
                else:
                    self._simulate_metrics(target_percent, duration)
            except ImportError:
                logger.warning("PyTorch not available, simulating metrics")
                self._simulate_metrics(target_percent, duration)
        else:
            # Simulate by injecting metrics
            self._simulate_metrics(target_percent, duration)
    
    def has_gpu(self) -> bool:
        """Check if system has NVIDIA GPU"""
        try:
            result = subprocess.run(['nvidia-smi'], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _allocate_gpu_memory(self, target_percent: float):
        """Actually allocate GPU memory using PyTorch"""
        try:
            import torch
            
            # Get GPU memory info
            gpu_props = torch.cuda.get_device_properties(0)
            total_memory = gpu_props.total_memory
            
            # Calculate target allocation
            current_allocated = torch.cuda.memory_allocated(0)
            current_percent = (current_allocated / total_memory) * 100
            
            if target_percent > current_percent:
                additional_needed = ((target_percent - current_percent) / 100) * total_memory
                
                # Allocate tensors to consume memory
                chunk_size = min(additional_needed, 1024 * 1024 * 1024)  # 1GB chunks
                
                logger.info(f"🔥 Allocating {additional_needed / (1024**3):.2f} GB GPU memory")
                
                while additional_needed > 0:
                    try:
                        size = min(chunk_size, additional_needed)
                        tensor = torch.empty(int(size // 4), dtype=torch.float32, device='cuda')
                        self.allocations.append(tensor)
                        additional_needed -= size
                        
                        # Update current usage
                        current_allocated = torch.cuda.memory_allocated(0)
                        current_percent = (current_allocated / total_memory) * 100
                        logger.info(f"📈 VRAM now at {current_percent:.1f}%")
                        
                        if current_percent >= target_percent:
                            break
                            
                    except torch.cuda.OutOfMemoryError:
                        logger.warning("⚠️ Hit OOM, backing off")
                        break
            
        except Exception as e:
            logger.error(f"❌ GPU allocation failed: {e}")
            self._simulate_metrics(target_percent, 300)
    
    def _simulate_metrics(self, target_percent: float, duration: int):
        """Simulate VRAM metrics by updating Prometheus endpoint"""
        logger.info(f"🎭 Simulating VRAM spike to {target_percent}% for {duration}s")
        
        # In real implementation, this would push metrics to Prometheus pushgateway
        # or update the API's metrics endpoint
        
        self.target_usage = target_percent
        self.running = True
        
        # Start background thread to "report" high usage
        self.thread = threading.Thread(target=self._metric_reporter_thread, args=(duration,))
        self.thread.start()
        
        logger.info(f"✅ VRAM chaos simulation active - check Grafana!")
        logger.info(f"📊 Simulated VRAM usage: {target_percent}%")
        
        # In practice, you'd update your app's metrics here:
        # Example:
        # requests.post('http://localhost:8000/internal/chaos/vram', 
        #               json={'usage_percent': target_percent})
    
    def _metric_reporter_thread(self, duration: int):
        """Background thread to maintain simulated metrics"""
        start_time = time.time()
        
        while self.running and (time.time() - start_time) < duration:
            # Simulate metric reporting
            logger.info(f"📊 [CHAOS] Reporting VRAM usage: {self.target_usage}%")
            time.sleep(30)  # Report every 30s
        
        logger.info("🔄 Chaos simulation ending...")
        self.stop_chaos()
    
    def stop_chaos(self):
        """Stop chaos simulation and clean up"""
        logger.info("🛑 Stopping VRAM chaos...")
        
        self.running = False
        
        # Clean up GPU allocations
        if self.allocations:
            try:
                import torch
                for tensor in self.allocations:
                    del tensor
                torch.cuda.empty_cache()
                logger.info("🧹 GPU memory cleared")
            except:
                pass
            self.allocations.clear()
        
        # Reset simulated metrics
        self.target_usage = 0
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        logger.info("✅ Chaos cleanup complete")
    
    def escalation_test(self):
        """Run full escalation test sequence"""
        logger.info("🧪 Starting VRAM escalation test sequence...")
        
        try:
            # Step 1: Warning level (75%)
            logger.info("📊 Step 1: Triggering VRAM Warning (75%)")
            self.simulate_vram_spike(78, 180)  # Slightly above threshold
            
            logger.info("⏳ Waiting 3 minutes for warning alert burn-in...")
            time.sleep(180)
            
            # Step 2: Critical level (85%)
            logger.info("🚨 Step 2: Escalating to VRAM Critical (85%)")
            self.simulate_vram_spike(88, 120)  # Critical level
            
            logger.info("⏳ Waiting 2 minutes for critical alert burn-in...")
            time.sleep(120)
            
            # Step 3: Emergency level (95%)
            logger.info("🔥 Step 3: Triggering VRAM Emergency (95%)")
            self.simulate_vram_spike(97, 60)  # Emergency level
            
            logger.info("⏳ Waiting 30 seconds for emergency alert...")
            time.sleep(30)
            
            logger.info("✅ Escalation test complete!")
            
        except KeyboardInterrupt:
            logger.info("⏹️ Test interrupted by user")
        finally:
            self.stop_chaos()

def main():
    """Main chaos execution"""
    parser = argparse.ArgumentParser(description="Chaos GPU Memory Testing")
    parser.add_argument("--vram", type=float, default=80, help="Target VRAM percentage")
    parser.add_argument("--duration", type=int, default=300, help="Duration in seconds")
    parser.add_argument("--escalation-test", action="store_true", help="Run full escalation test")
    parser.add_argument("--stop", action="store_true", help="Stop any running chaos")
    
    args = parser.parse_args()
    
    chaos = ChaosGPU()
    
    if args.stop:
        chaos.stop_chaos()
        return
    
    if args.escalation_test:
        chaos.escalation_test()
    else:
        chaos.simulate_vram_spike(args.vram, args.duration)
        
        try:
            logger.info(f"⏳ Chaos running for {args.duration} seconds... (Ctrl+C to stop)")
            time.sleep(args.duration)
        except KeyboardInterrupt:
            logger.info("⏹️ Chaos interrupted by user")
        finally:
            chaos.stop_chaos()

if __name__ == "__main__":
    main() 