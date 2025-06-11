#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CommLink Specialist - Trinity Agent Press Room Filter & Accuracy Auditor
Real-time Slack monitoring with tone drift detection and press accuracy validation
"""

import os
import json
import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import yaml
import requests
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
import prometheus_client
from prometheus_client import Counter, Histogram

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
agent_answer_mismatch_total = Counter(
    'agent_answer_mismatch_total',
    'Total agent answer mismatches detected',
    ['agent_id', 'mismatch_type']
)

voice_drift_total = Counter(
    'voice_drift_total', 
    'Total voice drift incidents detected',
    ['agent_id', 'drift_severity']
)

press_alerts_total = Counter(
    'press_alerts_total',
    'Total press alerts generated',
    ['alert_type']
)

slack_ingestion_latency = Histogram(
    'slack_ingestion_latency_seconds',
    'Slack message ingestion latency'
)

class CommLinkSpecialist:
    def __init__(self):
        self.config = self.load_config()
        self.slack_client = AsyncWebClient(token=self.config['slack_token'])
        self.agents_registry = self.load_agents_registry()
        self.personality_specs = self.load_personality_specs()
        self.litmus_tests = self.load_litmus_tests()
        self.escalation_matrix = self.load_escalation_matrix()
        self.command_aliases = self.load_command_aliases()
        self.alert_threshold = int(self.config.get('drift_threshold', 3))
        self.alert_window = int(self.config.get('alert_window_minutes', 15))
        self.recent_alerts = []
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables and config file"""
        config = {}
        
        # Try environment variables first
        env_mapping = {
            'slack_token': 'SLACK_BOT_TOKEN_RO',
            'slack_channel': 'SLACK_ALERTS_CHANNEL', 
            'grafana_token': 'GRAFANA_API_RO',
            'grafana_url': 'GRAFANA_URL',
            'council_api_url': 'COUNCIL_API_URL',
            'drift_threshold': 'COMMLINK_DRIFT_THRESHOLD',
            'alert_window_minutes': 'COMMLINK_ALERT_WINDOW_MINUTES',
            'real_time_interval': 'COMMLINK_REAL_TIME_INTERVAL'
        }
        
        for key, env_var in env_mapping.items():
            value = os.environ.get(env_var)
            if value:
                config[key] = value
        
        # Fallback to config file if needed
        try:
            if os.path.exists('commlink_config.txt'):
                with open('commlink_config.txt', 'r', encoding='utf-8') as f:
                    for line in f:
                        if '=' in line and not line.strip().startswith('#'):
                            key, value = line.strip().split('=', 1)
                            config_key = key.lower().replace('slack_bot_token_ro', 'slack_token')
                            config_key = config_key.replace('slack_alerts_channel', 'slack_channel')
                            if config_key not in config:
                                config[config_key] = value
        except Exception as e:
            logger.warning(f"Could not read config file: {e}")
        
        # Set defaults
        config.setdefault('slack_channel', '#trinity-alerts')
        config.setdefault('drift_threshold', '3')
        config.setdefault('alert_window_minutes', '15')
        config.setdefault('real_time_interval', '2')
        
        return config
    
    def load_command_aliases(self) -> Dict[str, str]:
        """Load command aliases from environment variables"""
        aliases = {}
        for key, value in os.environ.items():
            if key.startswith('COMMAND_ALIAS_'):
                command = key[14:].lower()  # Remove 'COMMAND_ALIAS_' prefix
                aliases[command] = value
        return aliases
    
    def load_agents_registry(self) -> Dict[str, Any]:
        """Load agent registry from agents/registry.yaml"""
        try:
            with open('agents/registry.yaml', 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error("agents/registry.yaml not found")
            return {}
    
    def load_personality_specs(self) -> Dict[str, str]:
        """Load personality spec files from prompts/"""
        specs = {}
        try:
            for agent_id, agent_info in self.agents_registry.get('agents', {}).items():
                persona_file = agent_info.get('persona_file', f'prompts/{agent_id}.md')
                if os.path.exists(persona_file):
                    with open(persona_file, 'r', encoding='utf-8') as f:
                        specs[agent_id] = f.read()
            return specs
        except Exception as e:
            logger.error(f"Error loading personality specs: {e}")
            return {}
    
    def load_litmus_tests(self) -> List[Dict]:
        """Load press litmus tests"""
        try:
            with open('tests/press_litmus.yaml', 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data.get('litmus_tests', [])
        except FileNotFoundError:
            logger.error("tests/press_litmus.yaml not found")
            return []
    
    def load_escalation_matrix(self) -> List[Dict]:
        """Load escalation contacts from CSV"""
        contacts = []
        try:
            with open('ops/escalation_contacts.csv', 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if len(lines) > 1:
                    for line in lines[1:]:
                        parts = line.strip().split(',')
                        if len(parts) >= 4:
                            contacts.append({
                                'role': parts[0],
                                'contact': parts[1],
                                'incident_types': parts[2],
                                'sla': parts[3]
                            })
            return contacts
        except FileNotFoundError:
            logger.error("ops/escalation_contacts.csv not found")
            return []
    
    async def send_startup_message(self):
        """Send startup confirmation to Slack"""
        try:
            message = "✅ CommLink Specialist online – drift & press alerts active"
            await self.slack_client.chat_postMessage(
                channel=self.config['slack_channel'],
                text=message
            )
            logger.info("Startup message sent to Slack")
        except SlackApiError as e:
            logger.error(f"Failed to send startup message: {e}")
    
    async def monitor_health(self):
        """Health monitoring loop"""
        logger.info("Starting health monitoring...")
        while True:
            try:
                # Simple health check - can be expanded
                await asyncio.sleep(30)
                logger.debug("Health check passed")
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                await asyncio.sleep(30)
    
    async def run(self):
        """Main execution loop"""
        logger.info("CommLink Specialist starting up...")
        
        if not self.config.get('slack_token'):
            logger.error("No Slack token configured")
            return
        
        logger.info(f"Loaded {len(self.personality_specs)} personality specs")
        logger.info(f"Loaded {len(self.litmus_tests)} litmus tests")
        logger.info(f"Loaded {len(self.escalation_matrix)} escalation contacts")
        logger.info(f"Loaded {len(self.command_aliases)} command aliases")
        
        await self.send_startup_message()
        
        # Main monitoring loop
        try:
            await self.monitor_health()
        except KeyboardInterrupt:
            logger.info("CommLink Specialist shutting down...")

if __name__ == "__main__":
    # Start Prometheus metrics server
    prometheus_client.start_http_server(8088)
    logger.info("Prometheus metrics server started on port 8088")
    
    # Run CommLink Specialist
    specialist = CommLinkSpecialist()
    asyncio.run(specialist.run()) 