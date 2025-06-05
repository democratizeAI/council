#!/usr/bin/env python3
"""
Unit tests for ICS Generator (Ticket #225)
Tests timezone support, alarm creation, and ICS formatting
"""

import pytest
import os
import sys
import tempfile
from datetime import datetime, timedelta
import pytz
from ics import Calendar

# Add parent directory to path to import scripts
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scripts.ics_generator import ICSGenerator


class TestICSGenerator:
    """Test ICS calendar generator functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.generator = ICSGenerator(timezone="America/New_York")
        self.test_time = datetime(2025, 6, 7, 10, 0, 0)  # 10 AM
        
    def test_timezone_initialization(self):
        """Test timezone is properly initialized"""
        assert self.generator.timezone.zone == "America/New_York"
        
        # Test with different timezone
        pacific_gen = ICSGenerator(timezone="America/Los_Angeles")
        assert pacific_gen.timezone.zone == "America/Los_Angeles"
        
    def test_soak_test_event_creation(self):
        """Test soak test event creation with proper timezone and alarms"""
        event = self.generator.create_soak_test_event(
            start_time=self.test_time,
            duration_hours=24,
            test_name="Test Soak Event"
        )
        
        # Check basic event properties
        assert event.name == "🧪 Test Soak Event"
        assert event.location == "Production Infrastructure"
        assert event.duration == timedelta(hours=24)
        
        # Verify timezone localization
        assert event.begin.tzinfo is not None
        assert str(event.begin.tzinfo) in ["America/New_York", "EST", "EDT"]
        
        # Check alarm configuration
        assert len(event.alarms) == 1
        alarm = list(event.alarms)[0]
        assert alarm.trigger == timedelta(minutes=-10)  # 10 minutes before
        
        # Verify description contains key elements
        description = event.description
        assert "Test Soak Event" in description
        assert "24 hours" in description
        assert "just gates-watch" in description
        assert "P95 latency < 500ms" in description
        
    def test_deployment_event_creation(self):
        """Test deployment event creation"""
        event = self.generator.create_deployment_event(
            deployment_time=self.test_time,
            version="v2.1.0",
            environment="staging",
            duration_minutes=45
        )
        
        # Check event properties
        assert event.name == "🚀 Deploy v2.1.0 to staging"
        assert event.location == "Staging Infrastructure"
        assert event.duration == timedelta(minutes=45)
        
        # Verify timezone
        assert event.begin.tzinfo.zone == "America/New_York"
        
        # Check alarm
        assert len(event.alarms) == 1
        alarm = list(event.alarms)[0]
        assert alarm.trigger == timedelta(minutes=-10)
        
        # Verify description
        description = event.description
        assert "v2.1.0" in description
        assert "staging" in description
        assert "45 minutes" in description
        assert "docker-compose" in description
        
    def test_timezone_localization(self):
        """Test timezone localization for different input formats"""
        # Test naive datetime (should be localized)
        naive_time = datetime(2025, 6, 7, 14, 30, 0)
        event = self.generator.create_soak_test_event(start_time=naive_time)
        assert event.begin.tzinfo.zone == "America/New_York"
        
        # Test timezone-aware datetime (should be converted)
        utc_time = pytz.UTC.localize(naive_time)
        event = self.generator.create_soak_test_event(start_time=utc_time)
        assert event.begin.tzinfo.zone == "America/New_York"
        
        # Verify time conversion is correct
        expected_eastern = utc_time.astimezone(pytz.timezone("America/New_York"))
        assert event.begin == expected_eastern
        
    def test_alarm_formatting(self):
        """Test alarm formatting for Google Calendar & Outlook compatibility"""
        event = self.generator.create_soak_test_event(
            start_time=self.test_time,
            test_name="Alarm Test"
        )
        
        # Should have exactly one alarm
        assert len(event.alarms) == 1
        
        alarm = list(event.alarms)[0]
        
        # Check alarm trigger is properly formatted
        assert alarm.trigger == timedelta(minutes=-10)
        
        # Verify alarm description is useful
        assert "Alarm Test" in alarm.description
        assert "10 minutes" in alarm.description
        
    def test_calendar_generation(self):
        """Test calendar file generation and statistics"""
        # Add multiple events
        soak_event = self.generator.create_soak_test_event(
            start_time=self.test_time,
            test_name="Soak Test 1"
        )
        
        deploy_event = self.generator.create_deployment_event(
            deployment_time=self.test_time + timedelta(days=1),
            version="v1.2.3"
        )
        
        self.generator.add_event(soak_event)
        self.generator.add_event(deploy_event)
        
        # Test statistics
        stats = self.generator.get_calendar_stats()
        assert stats["total_events"] == 2
        assert stats["timezone"] == "America/New_York"
        assert stats["total_alarms"] == 2
        
    def test_ics_file_generation(self):
        """Test ICS file generation and size"""
        event = self.generator.create_soak_test_event(
            start_time=self.test_time,
            test_name="File Test"
        )
        self.generator.add_event(event)
        
        # Generate to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ics', delete=False) as f:
            filename = f.name
        
        try:
            self.generator.generate_ics(filename)
            
            # Verify file exists and has reasonable size
            assert os.path.exists(filename)
            file_size = os.path.getsize(filename)
            assert 100 < file_size < 4096  # Between 100 bytes and 4KB
            
            # Verify ICS format
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                
            assert content.startswith("BEGIN:VCALENDAR")
            assert content.strip().endswith("END:VCALENDAR")
            assert "BEGIN:VEVENT" in content
            assert "END:VEVENT" in content
            assert "BEGIN:VALARM" in content  # Has alarm
            assert "TRIGGER:-PT10M" in content  # 10-minute trigger
            assert "America/New_York" in content or "EDT" in content or "EST" in content
            
        finally:
            if os.path.exists(filename):
                os.unlink(filename)
                
    def test_ics_content_parsing(self):
        """Test that generated ICS can be parsed back correctly"""
        original_event = self.generator.create_soak_test_event(
            start_time=self.test_time,
            test_name="Parse Test",
            duration_hours=48
        )
        self.generator.add_event(original_event)
        
        # Generate ICS content
        ics_content = self.generator.generate_ics()
        
        # Parse it back
        parsed_calendar = Calendar(ics_content)
        parsed_events = list(parsed_calendar.events)
        
        assert len(parsed_events) == 1
        parsed_event = parsed_events[0]
        
        # Verify key properties survived the round trip
        assert "Parse Test" in parsed_event.name
        assert parsed_event.duration == timedelta(hours=48)
        assert len(parsed_event.alarms) == 1
        
    def test_custom_descriptions(self):
        """Test custom event descriptions"""
        custom_desc = "Custom test description with special requirements"
        
        event = self.generator.create_soak_test_event(
            start_time=self.test_time,
            test_name="Custom Test",
            description=custom_desc
        )
        
        assert event.description == custom_desc
        
    def test_edge_cases(self):
        """Test edge cases and error conditions"""
        # Very short duration
        event = self.generator.create_deployment_event(
            deployment_time=self.test_time,
            version="v0.1.0",
            duration_minutes=1
        )
        assert event.duration == timedelta(minutes=1)
        
        # Very long duration
        event = self.generator.create_soak_test_event(
            start_time=self.test_time,
            duration_hours=168  # 1 week
        )
        assert event.duration == timedelta(hours=168)
        
        # Empty calendar statistics
        empty_gen = ICSGenerator()
        stats = empty_gen.get_calendar_stats()
        assert stats["total_events"] == 0
        assert stats["timezone"] == "America/New_York"
        
    def test_multiple_timezone_support(self):
        """Test generator works with different timezones"""
        timezones = [
            "America/New_York",
            "America/Los_Angeles", 
            "Europe/London",
            "Asia/Tokyo"
        ]
        
        for tz in timezones:
            gen = ICSGenerator(timezone=tz)
            event = gen.create_soak_test_event(
                start_time=self.test_time,
                test_name=f"Test {tz}"
            )
            
            assert event.begin.tzinfo.zone == tz
            assert len(event.alarms) == 1
            
    def test_alarm_compatibility(self):
        """Test alarm format compatibility with Google Calendar & Outlook"""
        event = self.generator.create_soak_test_event(
            start_time=self.test_time,
            test_name="Compatibility Test"
        )
        
        ics_content = self.generator.generate_ics()
        
        # Check for Google Calendar & Outlook compatible alarm format
        lines = ics_content.split('\n')
        alarm_lines = [line for line in lines if 'TRIGGER' in line or 'ACTION' in line]
        
        # Should have ACTION:DISPLAY for visual alerts
        assert any('ACTION:DISPLAY' in line for line in alarm_lines)
        
        # Should have TRIGGER:-PT10M for 10 minutes before
        assert any('TRIGGER:-PT10M' in line for line in alarm_lines)


def test_cli_integration():
    """Test CLI integration and argument parsing"""
    # This would test the main() function, but we'll keep it simple
    # to avoid complex CLI testing setup
    
    import sys
    from unittest.mock import patch
    
    # Import main function
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from scripts.ics_generator import main
    
    # Test help doesn't crash
    with patch.object(sys, 'argv', ['ics_generator.py', '--help']):
        with pytest.raises(SystemExit):  # argparse exits on --help
            main()


def test_file_size_compliance():
    """Test that generated files stay under 4KB as specified in feedback"""
    generator = ICSGenerator()
    
    # Create a typical soak test event
    event = generator.create_soak_test_event(
        start_time=datetime(2025, 6, 7, 10, 0, 0),
        duration_hours=24,
        test_name="Size Compliance Test"
    )
    generator.add_event(event)
    
    # Generate content and check size
    ics_content = generator.generate_ics()
    content_size = len(ics_content.encode('utf-8'))
    
    # Should be well under 4KB (4096 bytes)
    assert content_size < 4096, f"ICS file too large: {content_size} bytes"
    assert content_size > 100, f"ICS file too small: {content_size} bytes"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 