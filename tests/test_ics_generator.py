#!/usr/bin/env python3
"""
Simplified unit tests for ICS Generator (Ticket #225)
Tests key feedback requirements: timezone, alarms, file size
"""

import pytest
import os
import sys
import tempfile
from datetime import datetime, timedelta

# Add parent directory to path to import scripts
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scripts.ics_generator import ICSGenerator


def test_timezone_america_new_york():
    """Test timezone correctly localizes to America/New_York"""
    generator = ICSGenerator(timezone="America/New_York")
    
    # Test with naive datetime
    test_time = datetime(2025, 6, 7, 10, 0, 0)
    event = generator.create_soak_test_event(start_time=test_time)
    
    # Should have timezone info
    assert event.begin.tzinfo is not None
    
    # Generator should use correct timezone
    assert generator.timezone.zone == "America/New_York"


def test_10_minute_alarm_trigger():
    """Test 10-minute alarm trigger renders correctly"""
    generator = ICSGenerator()
    test_time = datetime(2025, 6, 7, 10, 0, 0)
    
    event = generator.create_soak_test_event(start_time=test_time)
    
    # Should have exactly one alarm
    assert len(event.alarms) == 1
    
    # Alarm should trigger 10 minutes before
    alarm = list(event.alarms)[0]
    assert alarm.trigger == timedelta(minutes=-10)


def test_ics_file_size_under_4kb():
    """Test file size is under 4KB as specified in feedback"""
    generator = ICSGenerator()
    test_time = datetime(2025, 6, 7, 10, 0, 0)
    
    # Create a typical soak test event
    event = generator.create_soak_test_event(
        start_time=test_time,
        duration_hours=24,
        test_name="Size Test Event"
    )
    generator.add_event(event)
    
    # Generate ICS content
    ics_content = generator.generate_ics()
    content_size = len(ics_content.encode('utf-8'))
    
    # Should be under 4KB (4096 bytes)
    assert content_size < 4096, f"File too large: {content_size} bytes"
    assert content_size > 100, f"File too small: {content_size} bytes"


def test_ics_format_compatibility():
    """Test ICS format is compatible with Google & Outlook"""
    generator = ICSGenerator()
    test_time = datetime(2025, 6, 7, 10, 0, 0)
    
    event = generator.create_soak_test_event(start_time=test_time)
    generator.add_event(event)
    
    ics_content = generator.generate_ics()
    
    # Check basic ICS structure
    assert ics_content.startswith("BEGIN:VCALENDAR")
    assert ics_content.strip().endswith("END:VCALENDAR")
    assert "BEGIN:VEVENT" in ics_content
    assert "END:VEVENT" in ics_content
    
    # Check alarm structure
    assert "BEGIN:VALARM" in ics_content
    assert "END:VALARM" in ics_content
    assert "TRIGGER:-PT10M" in ics_content  # 10-minute trigger
    

def test_soak_test_event_properties():
    """Test soak test event has correct properties"""
    generator = ICSGenerator()
    test_time = datetime(2025, 6, 7, 10, 0, 0)
    
    event = generator.create_soak_test_event(
        start_time=test_time,
        duration_hours=24,
        test_name="Test Soak"
    )
    
    # Check event properties
    assert "🧪 Test Soak" == event.name
    assert event.location == "Production Infrastructure"
    assert event.duration == timedelta(hours=24)
    
    # Check description contains key elements
    description = event.description
    assert "Test Soak" in description
    assert "24 hours" in description
    assert "gates-watch" in description


def test_deployment_event_properties():
    """Test deployment event has correct properties"""
    generator = ICSGenerator()
    test_time = datetime(2025, 6, 7, 14, 0, 0)
    
    event = generator.create_deployment_event(
        deployment_time=test_time,
        version="v2.1.0",
        environment="production",
        duration_minutes=30
    )
    
    # Check event properties
    assert event.name == "🚀 Deploy v2.1.0 to production"
    assert event.location == "Production Infrastructure"
    assert event.duration == timedelta(minutes=30)
    
    # Check alarm
    assert len(event.alarms) == 1
    alarm = list(event.alarms)[0]
    assert alarm.trigger == timedelta(minutes=-10)


def test_calendar_statistics():
    """Test calendar statistics are accurate"""
    generator = ICSGenerator()
    test_time = datetime(2025, 6, 7, 10, 0, 0)
    
    # Add two events
    soak_event = generator.create_soak_test_event(start_time=test_time)
    deploy_event = generator.create_deployment_event(
        deployment_time=test_time + timedelta(hours=1),
        version="v1.0.0"
    )
    
    generator.add_event(soak_event)
    generator.add_event(deploy_event)
    
    stats = generator.get_calendar_stats()
    
    assert stats["total_events"] == 2
    assert stats["timezone"] == "America/New_York"
    assert stats["total_alarms"] == 2


def test_file_generation():
    """Test file generation works correctly"""
    generator = ICSGenerator()
    test_time = datetime(2025, 6, 7, 10, 0, 0)
    
    event = generator.create_soak_test_event(start_time=test_time)
    generator.add_event(event)
    
    # Generate to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ics', delete=False) as f:
        filename = f.name
    
    try:
        generator.generate_ics(filename)
        
        # Verify file exists and has content
        assert os.path.exists(filename)
        file_size = os.path.getsize(filename)
        assert file_size > 100  # Has meaningful content
        assert file_size < 4096  # Under 4KB limit
        
        # Verify file content
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "BEGIN:VCALENDAR" in content
        assert "🧪 Swarm Soak Test" in content
        assert "TRIGGER:-PT10M" in content
        
    finally:
        if os.path.exists(filename):
            os.unlink(filename)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 