#!/usr/bin/env python3
"""
Unit tests for snapshot_prune.py (Ticket #207)
Tests both delete and retain paths with mocked time
"""

import tempfile
import shutil
import time
import subprocess
import pathlib
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add tools directory to path for importing
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "tools"))

def test_prune_logic_with_mocked_time(tmp_path, monkeypatch):
    """Test that old files are deleted and recent files are kept"""
    
    # Create test snapshot files
    old_snapshot = tmp_path / "old_conversation.jsonl.gz"
    recent_snapshot = tmp_path / "recent_conversation.jsonl.gz"
    
    old_snapshot.write_text("old conversation data")
    recent_snapshot.write_text("recent conversation data")
    
    # Set file modification times
    current_time = time.time()
    old_mtime = current_time - 31 * 86400  # 31 days ago (should be deleted)
    recent_mtime = current_time - 15 * 86400  # 15 days ago (should be kept)
    
    os.utime(old_snapshot, (old_mtime, old_mtime))
    os.utime(recent_snapshot, (recent_mtime, recent_mtime))
    
    # Mock the snapshot_prune module configuration
    import snapshot_prune
    monkeypatch.setattr(snapshot_prune, "SNAPSHOT_ROOT", tmp_path)
    monkeypatch.setattr(snapshot_prune, "KEEP_DAYS", 30)
    monkeypatch.setattr(snapshot_prune, "METRIC_DIR", str(tmp_path / "metrics"))
    
    # Run the prune logic
    result = snapshot_prune.main()
    
    # Verify results
    assert result == 0, "Prune script should succeed"
    assert not old_snapshot.exists(), "Old snapshot should be deleted"
    assert recent_snapshot.exists(), "Recent snapshot should be kept"
    
    # Check metrics file was created
    metrics_file = tmp_path / "metrics" / "snapshot_prune.prom"
    assert metrics_file.exists(), "Metrics file should be created"
    
    metrics_content = metrics_file.read_text()
    assert "snapshot_pruned_total 1" in metrics_content, "Should report 1 file pruned"
    assert "snapshot_prune_errors_total 0" in metrics_content, "Should report 0 errors"

def test_prune_no_files_to_delete(tmp_path, monkeypatch):
    """Test that when all files are recent, nothing is deleted"""
    
    # Create only recent files
    recent1 = tmp_path / "recent1.jsonl.gz"
    recent2 = tmp_path / "recent2.jsonl.gz"
    
    recent1.write_text("recent data 1")
    recent2.write_text("recent data 2")
    
    # Both files are recent (15 days old)
    current_time = time.time()
    recent_mtime = current_time - 15 * 86400
    
    os.utime(recent1, (recent_mtime, recent_mtime))
    os.utime(recent2, (recent_mtime, recent_mtime))
    
    # Mock configuration
    import snapshot_prune
    monkeypatch.setattr(snapshot_prune, "SNAPSHOT_ROOT", tmp_path)
    monkeypatch.setattr(snapshot_prune, "KEEP_DAYS", 30)
    monkeypatch.setattr(snapshot_prune, "METRIC_DIR", str(tmp_path / "metrics"))
    
    # Run prune
    result = snapshot_prune.main()
    
    # Verify nothing was deleted
    assert result == 0
    assert recent1.exists()
    assert recent2.exists()
    
    # Check metrics
    metrics_file = tmp_path / "metrics" / "snapshot_prune.prom"
    metrics_content = metrics_file.read_text()
    assert "snapshot_pruned_total 0" in metrics_content

def test_prune_missing_directory(tmp_path, monkeypatch):
    """Test behavior when snapshot directory doesn't exist"""
    
    non_existent_dir = tmp_path / "missing_snapshots"
    
    import snapshot_prune
    monkeypatch.setattr(snapshot_prune, "SNAPSHOT_ROOT", non_existent_dir)
    monkeypatch.setattr(snapshot_prune, "METRIC_DIR", str(tmp_path / "metrics"))
    
    # Run prune
    result = snapshot_prune.main()
    
    # Should succeed gracefully
    assert result == 0
    
    # Check metrics still created
    metrics_file = tmp_path / "metrics" / "snapshot_prune.prom"
    assert metrics_file.exists()
    
    metrics_content = metrics_file.read_text()
    assert "snapshot_pruned_total 0" in metrics_content
    assert "snapshot_prune_errors_total 0" in metrics_content

def test_prune_file_permission_error(tmp_path, monkeypatch):
    """Test error handling when file deletion fails"""
    
    # Create a test file
    test_file = tmp_path / "protected.jsonl.gz"
    test_file.write_text("protected data")
    
    # Make it old (should be deleted)
    old_mtime = time.time() - 31 * 86400
    os.utime(test_file, (old_mtime, old_mtime))
    
    import snapshot_prune
    monkeypatch.setattr(snapshot_prune, "SNAPSHOT_ROOT", tmp_path)
    monkeypatch.setattr(snapshot_prune, "KEEP_DAYS", 30)
    monkeypatch.setattr(snapshot_prune, "METRIC_DIR", str(tmp_path / "metrics"))
    
    # Mock unlink to raise permission error
    original_unlink = pathlib.Path.unlink
    def mock_unlink(self, missing_ok=False):
        if self.name == "protected.jsonl.gz":
            raise PermissionError("Access denied")
        return original_unlink(self, missing_ok)
    
    monkeypatch.setattr(pathlib.Path, "unlink", mock_unlink)
    
    # Run prune (should handle error gracefully)
    result = snapshot_prune.main()
    
    # Should succeed despite file error
    assert result == 0
    
    # Check error was recorded in metrics
    metrics_file = tmp_path / "metrics" / "snapshot_prune.prom"
    metrics_content = metrics_file.read_text()
    assert "snapshot_prune_errors_total 1" in metrics_content

def test_cron_file_exists():
    """Test that the cron file exists and has correct format"""
    cron_file = pathlib.Path("deploy/cron/snapshot_prune")
    assert cron_file.exists(), "Cron file should exist"
    
    content = cron_file.read_text()
    assert "10 2 * * *" in content, "Should run at 02:10 UTC"
    assert "/opt/lumina/tools/snapshot_prune.py" in content, "Should call the script"

def test_alert_rules_exist():
    """Test that snapshot alert rules exist"""
    alert_file = pathlib.Path("monitoring/snapshot_alerts.yml")
    assert alert_file.exists(), "Alert file should exist"
    
    content = alert_file.read_text()
    assert "SnapshotPurgeFailed" in content, "Should have error alert"
    assert "SnapshotNotPruned24h" in content, "Should have inactivity alert"
    assert "snapshot_prune_errors_total" in content, "Should monitor error metric"
    assert "snapshot_pruned_total" in content, "Should monitor pruned metric"

if __name__ == "__main__":
    # Quick smoke test
    print("Running snapshot prune tests...")
    # Note: For full test run, use: pytest tests/test_snapshot_prune.py -v
    print("✅ Use 'pytest tests/test_snapshot_prune.py -v' for full test suite") 