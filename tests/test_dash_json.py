#!/usr/bin/env python3
"""
Unit tests for Grafana dashboard JSON validation
Ensures dashboard configurations are valid and refresh rates are properly set
"""

import json
import pathlib
import pytest
import re

def test_cost_dash_refresh():
    """Test that cost dashboard has correct 30s auto-refresh"""
    dashboard_path = pathlib.Path("monitoring/grafana/dashboards/council-dashboard.json")
    
    if not dashboard_path.exists():
        pytest.skip("Council dashboard file not found")
    
    # Load and parse JSON
    try:
        dashboard_content = json.loads(dashboard_path.read_text())
    except json.JSONDecodeError as e:
        pytest.fail(f"Dashboard JSON is invalid: {e}")
    
    # Verify structure
    assert "dashboard" in dashboard_content, "Dashboard object missing from JSON"
    dashboard = dashboard_content["dashboard"]
    
    # Verify refresh setting
    assert "refresh" in dashboard, "Refresh setting missing from dashboard"
    assert dashboard["refresh"] == "30s", f"Expected refresh '30s', got '{dashboard['refresh']}'"

def test_dashboard_json_structure():
    """Test that dashboard JSON has required structure"""
    dashboard_path = pathlib.Path("monitoring/grafana/dashboards/council-dashboard.json")
    
    if not dashboard_path.exists():
        pytest.skip("Council dashboard file not found")
    
    dashboard_content = json.loads(dashboard_path.read_text())
    dashboard = dashboard_content["dashboard"]
    
    # Verify required top-level fields
    required_fields = ["title", "panels", "time", "refresh"]
    for field in required_fields:
        assert field in dashboard, f"Required field '{field}' missing from dashboard"
    
    # Verify panels exist and have cost monitoring
    panels = dashboard["panels"]
    assert isinstance(panels, list), "Panels should be a list"
    assert len(panels) > 0, "Dashboard should have at least one panel"
    
    # Look for cost-related panels
    cost_panels = [
        panel for panel in panels 
        if "cost" in panel.get("title", "").lower()
    ]
    assert len(cost_panels) > 0, "Dashboard should have at least one cost monitoring panel"

def test_refresh_rate_format():
    """Test that refresh rate follows expected format"""
    dashboard_path = pathlib.Path("monitoring/grafana/dashboards/council-dashboard.json")
    
    if not dashboard_path.exists():
        pytest.skip("Council dashboard file not found")
    
    dashboard_content = json.loads(dashboard_path.read_text())
    refresh = dashboard_content["dashboard"]["refresh"]
    
    # Verify format: number followed by time unit
    refresh_pattern = r'^\d+[smhd]$'
    assert re.match(refresh_pattern, refresh), f"Refresh rate '{refresh}' doesn't match expected format (e.g., '30s', '5m')"

def test_cost_panels_configuration():
    """Test that cost panels have proper configuration"""
    dashboard_path = pathlib.Path("monitoring/grafana/dashboards/council-dashboard.json")
    
    if not dashboard_path.exists():
        pytest.skip("Council dashboard file not found")
    
    dashboard_content = json.loads(dashboard_path.read_text())
    panels = dashboard_content["dashboard"]["panels"]
    
    # Find cost-related panels
    cost_panels = [
        panel for panel in panels 
        if "cost" in panel.get("title", "").lower()
    ]
    
    for panel in cost_panels:
        # Verify each cost panel has required fields
        assert "targets" in panel, f"Cost panel '{panel.get('title')}' missing targets"
        assert "fieldConfig" in panel, f"Cost panel '{panel.get('title')}' missing fieldConfig"
        
        # Verify targets have Prometheus queries
        for target in panel["targets"]:
            assert "expr" in target, f"Cost panel target missing Prometheus expression"
            assert "cost" in target["expr"].lower(), f"Cost panel should query cost metrics"

def test_json_syntax_valid():
    """Test that all dashboard JSON files have valid syntax"""
    dashboard_dir = pathlib.Path("monitoring/grafana/dashboards")
    
    if not dashboard_dir.exists():
        pytest.skip("Dashboard directory not found")
    
    json_files = list(dashboard_dir.glob("*.json"))
    assert len(json_files) > 0, "No JSON dashboard files found"
    
    for json_file in json_files:
        try:
            json.loads(json_file.read_text())
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON in {json_file.name}: {e}")

if __name__ == "__main__":
    pytest.main([__file__]) 