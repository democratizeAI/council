#!/usr/bin/env python3
"""
📅 ICS Calendar Generator (Ticket #225)
Generates calendar events for soak tests, deployments, and monitoring activities
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import pytz
from ics import Calendar, Event
from ics.alarm import DisplayAlarm, AudioAlarm

class ICSGenerator:
    """Generator for ICS calendar files with timezone and alarm support"""
    
    def __init__(self, timezone: str = "America/New_York"):
        self.timezone = pytz.timezone(timezone)
        self.calendar = Calendar()
        
    def create_soak_test_event(
        self,
        start_time: datetime,
        duration_hours: int = 24,
        test_name: str = "Swarm Soak Test",
        description: str = None,
        location: str = "Production Infrastructure"
    ) -> Event:
        """Create a soak test calendar event"""
        
        # Localize to timezone
        if start_time.tzinfo is None:
            start_time = self.timezone.localize(start_time)
        else:
            start_time = start_time.astimezone(self.timezone)
        
        end_time = start_time + timedelta(hours=duration_hours)
        
        event = Event()
        event.name = f"🧪 {test_name}"
        event.begin = start_time
        event.end = end_time
        event.location = location
        
        # Rich description with soak test details
        if description is None:
            description = f"""
🚀 Soak Test: {test_name}
📅 Duration: {duration_hours} hours
📍 Location: {location}
🎯 Objective: Extended stability and performance validation

📊 Monitoring:
• just gates-watch (continuous gate monitoring)
• Grafana: http://localhost:3000
• Prometheus: http://localhost:9090
• Ops Dashboard: ops/ops_dashboard_v2.html

🚨 Critical Gates:
• P95 latency < 500ms
• Error rate < 1%
• GPU memory < 10GB

⚠️ Actions:
• Monitor continuously
• Check alerts every 2 hours
• Stop test if critical gates fail
• Document results in lineage
            """.strip()
        
        event.description = description
        
        # Add 10-minute alarm (compatible with Google & Outlook)
        alarm = DisplayAlarm()
        alarm.trigger = timedelta(minutes=-10)  # 10 minutes before
        alarm.description = f"⏰ Soak test '{test_name}' starts in 10 minutes"
        event.alarms.append(alarm)
        
        return event
    
    def create_deployment_event(
        self,
        deployment_time: datetime,
        version: str,
        environment: str = "production",
        duration_minutes: int = 30
    ) -> Event:
        """Create a deployment calendar event"""
        
        if deployment_time.tzinfo is None:
            deployment_time = self.timezone.localize(deployment_time)
        else:
            deployment_time = deployment_time.astimezone(self.timezone)
            
        end_time = deployment_time + timedelta(minutes=duration_minutes)
        
        event = Event()
        event.name = f"🚀 Deploy {version} to {environment}"
        event.begin = deployment_time
        event.end = end_time
        event.location = f"{environment.title()} Infrastructure"
        
        event.description = f"""
🚀 Deployment: {version}
🎯 Environment: {environment}
⏱️ Estimated Duration: {duration_minutes} minutes

📋 Pre-deployment Checklist:
• Boot sequence validation
• Gate checks passed  
• Monitoring ready
• Rollback plan prepared

🔧 Deployment Steps:
• docker-compose down
• git pull origin main
• docker-compose up -d
• Health checks
• Gate validation

📊 Post-deployment:
• python scripts/soak_gates.py
• just health
• Monitor for 2 hours
        """.strip()
        
        # 10-minute warning alarm
        alarm = DisplayAlarm()
        alarm.trigger = timedelta(minutes=-10)
        alarm.description = f"⏰ Deployment '{version}' to {environment} in 10 minutes"
        event.alarms.append(alarm)
        
        return event
    
    def add_event(self, event: Event) -> None:
        """Add an event to the calendar"""
        self.calendar.events.add(event)
    
    def generate_ics(self, filename: str = None) -> str:
        """Generate ICS content"""
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(str(self.calendar))
            return filename
        else:
            return str(self.calendar)
    
    def get_calendar_stats(self) -> Dict[str, Any]:
        """Get calendar statistics"""
        events = list(self.calendar.events)
        
        if not events:
            return {"total_events": 0, "timezone": self.timezone.zone}
        
        stats = {
            "total_events": len(events),
            "timezone": self.timezone.zone,
            "total_alarms": sum(len(event.alarms) for event in events)
        }
        
        return stats

def main():
    """CLI interface for ICS generator"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ICS calendar generator for soak tests and deployments")
    parser.add_argument("--type", choices=["soak", "deployment"], 
                       default="soak", help="Type of event to generate")
    parser.add_argument("--start", type=str, help="Start time (YYYY-MM-DD HH:MM)")
    parser.add_argument("--duration", type=int, help="Duration in hours")
    parser.add_argument("--name", type=str, help="Event name")
    parser.add_argument("--output", type=str, help="Output filename")
    parser.add_argument("--timezone", type=str, default="America/New_York", help="Timezone")
    
    args = parser.parse_args()
    
    generator = ICSGenerator(timezone=args.timezone)
    
    # Parse start time
    if args.start:
        start_time = datetime.strptime(args.start, "%Y-%m-%d %H:%M")
    else:
        # Default to tomorrow at 10 AM
        start_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    # Create specific event type
    if args.type == "soak":
        event = generator.create_soak_test_event(
            start_time=start_time,
            duration_hours=args.duration or 24,
            test_name=args.name or "Swarm Soak Test"
        )
    elif args.type == "deployment":
        event = generator.create_deployment_event(
            deployment_time=start_time,
            version=args.name or "v1.0.0",
            duration_minutes=(args.duration or 1) * 60  # Convert hours to minutes
        )
    
    generator.add_event(event)
    
    # Generate output
    output_file = args.output or f"swarm_calendar_{args.type}.ics"
    generator.generate_ics(output_file)
    
    # Show statistics
    stats = generator.get_calendar_stats()
    print(f"📅 Generated calendar: {output_file}")
    print(f"📊 Events: {stats['total_events']}")
    print(f"🕒 Timezone: {stats['timezone']}")
    print(f"⏰ Total alarms: {stats['total_alarms']}")
    print(f"📂 File size: {os.path.getsize(output_file)} bytes")
    print(f"✅ Ready to import into Google Calendar, Outlook, or any ICS-compatible client")

if __name__ == "__main__":
    main()
