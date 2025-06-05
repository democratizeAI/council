#!/usr/bin/env python3
"""
Snapshot GDPR Purge Script (Ticket #207)
Rolling 30-day deletion of old conversation snapshots
Enhanced with Prometheus metrics for observability
"""

import os
import time
import pathlib
import sys

# Configuration
KEEP_DAYS = 30
SNAPSHOT_ROOT = pathlib.Path("/snapshots")
METRIC_DIR = "/var/lib/node_exporter/textfile_collector"
METRIC_FILE = f"{METRIC_DIR}/snapshot_prune.prom"

def write_metrics(pruned_count: int, error_count: int):
    """Write Prometheus metrics to textfile collector"""
    os.makedirs(METRIC_DIR, exist_ok=True)
    
    with open(METRIC_FILE, 'w') as f:
        f.write("# HELP snapshot_pruned_total Snapshots deleted by GDPR purge\n")
        f.write("# TYPE snapshot_pruned_total counter\n")
        f.write(f"snapshot_pruned_total {pruned_count}\n")
        
        f.write("# HELP snapshot_prune_errors_total Errors during snapshot prune\n") 
        f.write("# TYPE snapshot_prune_errors_total counter\n")
        f.write(f"snapshot_prune_errors_total {error_count}\n")
        
        f.write("# HELP snapshot_prune_last_run_timestamp_seconds Last successful prune run\n")
        f.write("# TYPE snapshot_prune_last_run_timestamp_seconds gauge\n")
        f.write(f"snapshot_prune_last_run_timestamp_seconds {time.time()}\n")

def main():
    """Main prune logic with error handling and metrics"""
    cutoff_time = time.time() - KEEP_DAYS * 86400
    pruned_count = 0
    error_count = 0
    
    print(f"🗑️ Starting GDPR snapshot purge (keeping last {KEEP_DAYS} days)")
    print(f"📅 Cutoff time: {time.ctime(cutoff_time)}")
    
    try:
        if not SNAPSHOT_ROOT.exists():
            print(f"⚠️ Snapshot directory {SNAPSHOT_ROOT} does not exist")
            write_metrics(pruned_count, error_count)
            return 0
            
        # Find and process snapshot files
        for snapshot_file in SNAPSHOT_ROOT.glob("**/*.jsonl.gz"):
            try:
                file_mtime = snapshot_file.stat().st_mtime
                
                if file_mtime < cutoff_time:
                    print(f"🗑️ Deleting old snapshot: {snapshot_file.name} (age: {(time.time() - file_mtime) / 86400:.1f} days)")
                    snapshot_file.unlink()
                    pruned_count += 1
                else:
                    print(f"✅ Keeping recent snapshot: {snapshot_file.name}")
                    
            except Exception as e:
                print(f"❌ Error processing {snapshot_file}: {e}", file=sys.stderr)
                error_count += 1
                continue
        
        print(f"✅ GDPR purge complete: {pruned_count} files deleted, {error_count} errors")
        
    except Exception as e:
        error_count += 1
        print(f"❌ Fatal prune error: {e}", file=sys.stderr)
        write_metrics(pruned_count, error_count)
        return 1
    
    # Write metrics for Prometheus scraping
    write_metrics(pruned_count, error_count)
    return 0

if __name__ == "__main__":
    sys.exit(main()) 