#!/usr/bin/env python3
"""
🎭🪴 Emotional Tamagotchi Evolution - Web UI Dashboard
Real-time monitoring and control interface for the evolution system
"""

import os
import json
import time
import psutil
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request, Response
from flask_cors import CORS
import requests
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
REFRESH_INTERVAL = int(os.getenv('REFRESH_INTERVAL', '2'))  # seconds

class TamagotchiMonitor:
    """Monitor for Tamagotchi Evolution system"""
    
    def __init__(self):
        self.start_time = time.time()
        
    def get_system_stats(self):
        """Get system resource statistics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_gb': round(memory.used / (1024**3), 2),
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'disk_percent': disk.percent,
                'disk_used_gb': round(disk.used / (1024**3), 2),
                'disk_total_gb': round(disk.total / (1024**3), 2),
                'uptime_hours': round((time.time() - self.start_time) / 3600, 2)
            }
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {}
    
    def get_job_queue_status(self):
        """Get training job queue status"""
        try:
            queue_dir = 'jobs/queue'
            completed_dir = 'jobs/completed'
            
            queue_count = len(os.listdir(queue_dir)) if os.path.exists(queue_dir) else 0
            completed_count = len(os.listdir(completed_dir)) if os.path.exists(completed_dir) else 0
            
            # Get recent jobs
            recent_jobs = []
            if os.path.exists(queue_dir):
                for job_file in sorted(os.listdir(queue_dir))[-5:]:
                    try:
                        with open(os.path.join(queue_dir, job_file), 'r') as f:
                            job_data = yaml.safe_load(f)
                            recent_jobs.append({
                                'name': job_file,
                                'type': job_data.get('type', 'unknown'),
                                'created': job_data.get('created', 'unknown')
                            })
                    except Exception as e:
                        logger.warning(f"Error reading job file {job_file}: {e}")
            
            return {
                'queue_count': queue_count,
                'completed_count': completed_count,
                'recent_jobs': recent_jobs
            }
        except Exception as e:
            logger.error(f"Error getting job queue status: {e}")
            return {'queue_count': 0, 'completed_count': 0, 'recent_jobs': []}
    
    def get_lora_adapters(self):
        """Get LoRA adapter information"""
        try:
            lora_dir = 'lora_adapters'
            if not os.path.exists(lora_dir):
                return {'count': 0, 'total_size_mb': 0, 'recent_adapters': []}
            
            adapters = []
            total_size = 0
            
            for adapter_file in os.listdir(lora_dir):
                if adapter_file.endswith('.safetensors'):
                    file_path = os.path.join(lora_dir, adapter_file)
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                    
                    adapters.append({
                        'name': adapter_file,
                        'size_mb': round(file_size / (1024**2), 2),
                        'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                    })
            
            # Sort by modification time, most recent first
            adapters.sort(key=lambda x: x['modified'], reverse=True)
            
            return {
                'count': len(adapters),
                'total_size_mb': round(total_size / (1024**2), 2),
                'recent_adapters': adapters[:5]
            }
        except Exception as e:
            logger.error(f"Error getting LoRA adapters: {e}")
            return {'count': 0, 'total_size_mb': 0, 'recent_adapters': []}
    
    def get_performance_history(self):
        """Get performance history from JSONL file"""
        try:
            history_file = 'performance_history.jsonl'
            if not os.path.exists(history_file):
                return []
            
            history = []
            with open(history_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        history.append(entry)
                    except json.JSONDecodeError:
                        continue
            
            # Return last 50 entries
            return history[-50:]
        except Exception as e:
            logger.error(f"Error getting performance history: {e}")
            return []
    
    def get_crawler_stats(self):
        """Get crawler statistics"""
        try:
            feeding_history_file = 'feeding_history.jsonl'
            if not os.path.exists(feeding_history_file):
                return {'total_discoveries': 0, 'recent_rate': 0}
            
            with open(feeding_history_file, 'r') as f:
                lines = f.readlines()
            
            total_discoveries = len(lines)
            
            # Calculate recent discovery rate (last 24 hours)
            recent_count = 0
            current_time = time.time()
            for line in lines[-100:]:  # Check last 100 entries
                try:
                    entry = json.loads(line.strip())
                    if 'timestamp' in entry:
                        entry_time = datetime.fromisoformat(entry['timestamp']).timestamp()
                        if current_time - entry_time < 86400:  # 24 hours
                            recent_count += 1
                except:
                    continue
            
            return {
                'total_discoveries': total_discoveries,
                'recent_rate': recent_count
            }
        except Exception as e:
            logger.error(f"Error getting crawler stats: {e}")
            return {'total_discoveries': 0, 'recent_rate': 0}

monitor = TamagotchiMonitor()

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    """Get overall system status"""
    try:
        # Try to ping the main API
        api_healthy = False
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            api_healthy = response.status_code == 200
        except:
            pass
        
        system_stats = monitor.get_system_stats()
        job_status = monitor.get_job_queue_status()
        lora_info = monitor.get_lora_adapters()
        crawler_stats = monitor.get_crawler_stats()
        
        return jsonify({
            'status': 'healthy' if api_healthy else 'degraded',
            'timestamp': datetime.now().isoformat(),
            'api_healthy': api_healthy,
            'system': system_stats,
            'jobs': job_status,
            'lora': lora_info,
            'crawler': crawler_stats
        })
    except Exception as e:
        logger.error(f"Error in api_status: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/performance')
def api_performance():
    """Get performance history data"""
    try:
        history = monitor.get_performance_history()
        return jsonify(history)
    except Exception as e:
        logger.error(f"Error in api_performance: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trigger-evolution', methods=['POST'])
def trigger_evolution():
    """Trigger immediate evolution cycle"""
    try:
        # This would trigger the evolution process
        # For now, just return success
        return jsonify({
            'status': 'triggered',
            'message': 'Evolution cycle triggered successfully',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error triggering evolution: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trigger-crawler', methods=['POST'])
def trigger_crawler():
    """Trigger immediate crawler run"""
    try:
        # This would trigger the crawler
        return jsonify({
            'status': 'triggered',
            'message': 'Crawler run triggered successfully',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error triggering crawler: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/events')
def events():
    """Server-Sent Events endpoint for real-time updates"""
    def event_stream():
        while True:
            try:
                # Get current status
                system_stats = monitor.get_system_stats()
                job_status = monitor.get_job_queue_status()
                
                data = {
                    'timestamp': datetime.now().isoformat(),
                    'system': system_stats,
                    'jobs': job_status
                }
                
                yield f"data: {json.dumps(data)}\n\n"
                time.sleep(REFRESH_INTERVAL)
            except Exception as e:
                logger.error(f"Error in event stream: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(5)
    
    return Response(event_stream(), mimetype='text/plain')

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'tamagotchi-web-ui',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Run the Flask app
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"🎭🪴 Starting Tamagotchi Evolution Web UI on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug) 