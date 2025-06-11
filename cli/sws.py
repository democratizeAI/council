#!/usr/bin/env python3
# cli/sws.py - SWS-Core CLI Tool
"""
🛠️ SWS-Core CLI - Command Line Interface
========================================

CLI tool for Swarm-to-Swarm Services platform.

Commands:
- agent create --intent="X"  # SWS-120 scaffolding
- topology map               # SWS-100 visualization
- permissions list           # SWS-110 management
- docs generate             # SWS-130 documentation

Usage:
    sws agent create --intent="Monitor system health and send alerts"
    sws topology map --format=json
    sws permissions register agent_id developer
    sws docs generate manifest.yaml
"""

import click
import asyncio
import aiohttp
import json
import yaml
import time
import os
from typing import Dict, Any, Optional
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING)  # Quiet by default
logger = logging.getLogger(__name__)

# Default SWS-Core API endpoint
DEFAULT_API_URL = os.environ.get("SWS_API_URL", "http://localhost:8080")

class SWSClient:
    """Client for SWS-Core API"""
    
    def __init__(self, api_url: str = DEFAULT_API_URL):
        self.api_url = api_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def health_check(self) -> Dict[str, Any]:
        """Check SWS-Core platform health"""
        async with self.session.get(f"{self.api_url}/health") as response:
            if response.status == 200:
                return await response.json()
            else:
                raise click.ClickException(f"Health check failed: {response.status}")
                
    async def create_agent(self, intent: str, developer_id: str = "cli") -> Dict[str, Any]:
        """Create agent via SWS-120 Build Agent"""
        payload = {
            "intent": intent,
            "developer_id": developer_id
        }
        
        async with self.session.post(f"{self.api_url}/agent/create", json=payload) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise click.ClickException(f"Agent creation failed: {error_text}")
                
    async def get_topology(self) -> Dict[str, Any]:
        """Get topology map via SWS-100 Graph Agent"""
        async with self.session.get(f"{self.api_url}/a2a/map") as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise click.ClickException(f"Topology fetch failed: {error_text}")
                
    async def authorize_access(self, agent_id: str, target_stream: str, operation: str) -> Dict[str, Any]:
        """Test authorization via SWS-110 Perms Agent"""
        payload = {
            "agent_id": agent_id,
            "target_stream": target_stream,
            "operation": operation,
            "context": {"source": "cli_test"}
        }
        
        async with self.session.post(f"{self.api_url}/a2a/auth", json=payload) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise click.ClickException(f"Authorization test failed: {error_text}")
                
    async def register_agent_permissions(self, agent_id: str, role: str) -> Dict[str, Any]:
        """Register agent with permissions"""
        payload = {
            "agent_id": agent_id,
            "role": role,
            "created_by": "cli"
        }
        
        async with self.session.post(f"{self.api_url}/a2a/register", json=payload) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise click.ClickException(f"Agent registration failed: {error_text}")
                
    async def generate_documentation(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Generate documentation via SWS-130 Docs Agent"""
        payload = {
            "agent_manifest": manifest
        }
        
        async with self.session.post(f"{self.api_url}/docs/generate", json=payload) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise click.ClickException(f"Documentation generation failed: {error_text}")

# CLI Commands
@click.group()
@click.option('--api-url', default=DEFAULT_API_URL, help='SWS-Core API URL')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def cli(ctx, api_url, verbose):
    """SWS-Core CLI - Swarm-to-Swarm Services Platform"""
    ctx.ensure_object(dict)
    ctx.obj['api_url'] = api_url
    ctx.obj['verbose'] = verbose
    
    if verbose:
        logging.getLogger().setLevel(logging.INFO)

@cli.command()
@click.pass_context
def health(ctx):
    """Check SWS-Core platform health"""
    
    async def check_health():
        async with SWSClient(ctx.obj['api_url']) as client:
            health_data = await client.health_check()
            
            status = health_data.get('status', 'unknown')
            components = health_data.get('components', {})
            
            click.echo(f"🏥 SWS-Core Platform Health: {status.upper()}")
            click.echo(f"📊 Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            click.echo(f"🔗 API URL: {ctx.obj['api_url']}")
            click.echo()
            
            click.echo("Components:")
            for component, comp_status in components.items():
                status_icon = "✅" if comp_status == "healthy" or comp_status == "ready" else "❌"
                click.echo(f"  {status_icon} {component}: {comp_status}")
                
    asyncio.run(check_health())

# Agent commands group
@cli.group()
def agent():
    """Agent management commands (SWS-120)"""
    pass

@agent.command()
@click.option('--intent', '-i', required=True, help='What the agent should do')
@click.option('--developer-id', '-d', default='cli', help='Developer ID')
@click.option('--wait', '-w', is_flag=True, help='Wait for completion')
@click.pass_context
def create(ctx, intent, developer_id, wait):
    """
    Create new agent from intent (SWS-120)
    
    Example:
        sws agent create --intent="Monitor system health and send alerts"
    """
    
    async def create_agent():
        click.echo(f"🛠️ Creating agent with intent: {intent}")
        click.echo(f"👤 Developer: {developer_id}")
        
        if ctx.obj['verbose']:
            click.echo(f"🔗 API URL: {ctx.obj['api_url']}")
        
        start_time = time.time()
        
        async with SWSClient(ctx.obj['api_url']) as client:
            try:
                result = await client.create_agent(intent, developer_id)
                
                creation_time = time.time() - start_time
                
                if result.get('success'):
                    click.echo(f"✅ Agent created successfully!")
                    click.echo(f"🤖 Agent Name: {result.get('agent_name')}")
                    click.echo(f"📋 Spec ID: {result.get('spec_id')}")
                    click.echo(f"⏱️  Creation Time: {creation_time:.1f}s")
                    
                    if result.get('pr_url'):
                        click.echo(f"🔗 Pull Request: {result.get('pr_url')}")
                        
                    if result.get('files_created'):
                        click.echo(f"📁 Files Created: {len(result.get('files_created'))}")
                        
                        if ctx.obj['verbose']:
                            for file_path in result.get('files_created'):
                                click.echo(f"   - {file_path}")
                                
                    ci_status = "✅ Passed" if result.get('ci_gates_passed') else "⏳ Pending"
                    click.echo(f"🚦 CI Gates: {ci_status}")
                    
                else:
                    click.echo(f"❌ Agent creation failed!")
                    if result.get('error_message'):
                        click.echo(f"Error: {result.get('error_message')}")
                        
            except Exception as e:
                click.echo(f"❌ Agent creation failed: {str(e)}")
                
    asyncio.run(create_agent())

@agent.command()
@click.pass_context
def templates(ctx):
    """List available agent templates"""
    
    async def list_templates():
        async with SWSClient(ctx.obj['api_url']) as client:
            async with client.session.get(f"{client.api_url}/agent/templates") as response:
                if response.status == 200:
                    data = await response.json()
                    templates = data.get('templates', [])
                    
                    click.echo(f"📋 Available Agent Templates ({len(templates)}):")
                    click.echo()
                    
                    for template in templates:
                        click.echo(f"🔧 {template['name']}")
                        click.echo(f"   Description: {template['description']}")
                        click.echo(f"   Capabilities: {', '.join(template['capabilities'])}")
                        click.echo(f"   Files: {', '.join(template['files'])}")
                        click.echo()
                        
                else:
                    click.echo("❌ Failed to fetch templates")
                    
    asyncio.run(list_templates())

# Topology commands group  
@cli.group()
def topology():
    """Topology introspection commands (SWS-100)"""
    pass

@topology.command()
@click.option('--format', '-f', type=click.Choice(['json', 'table', 'graph']), default='table', help='Output format')
@click.option('--output', '-o', type=click.Path(), help='Output file')
@click.pass_context
def map(ctx, format, output):
    """
    Get agent topology map (SWS-100)
    
    Example:
        sws topology map --format=json --output=topology.json
    """
    
    async def get_topology():
        click.echo("🧬 Fetching agent topology...")
        
        async with SWSClient(ctx.obj['api_url']) as client:
            topology_data = await client.get_topology()
            
            topology = topology_data.get('topology', {})
            metrics = topology_data.get('metrics', {})
            meta = topology_data.get('meta', {})
            
            if format == 'json':
                output_data = topology_data
                if output:
                    with open(output, 'w') as f:
                        json.dump(output_data, f, indent=2)
                    click.echo(f"💾 Topology saved to {output}")
                else:
                    click.echo(json.dumps(output_data, indent=2))
                    
            elif format == 'table':
                nodes = topology.get('nodes', [])
                edges = topology.get('edges', [])
                
                click.echo(f"🤖 Agents ({len(nodes)}):")
                click.echo("┌─────────────────────┬─────────────┬────────────┬─────────────────┐")
                click.echo("│ Agent ID            │ Type        │ Status     │ Capabilities    │")
                click.echo("├─────────────────────┼─────────────┼────────────┼─────────────────┤")
                
                for node in nodes:
                    agent_id = node.get('id', 'unknown')[:19]
                    agent_type = node.get('type', 'unknown')[:11]
                    status = node.get('status', 'unknown')[:10]
                    capabilities = ', '.join(node.get('capabilities', []))[:15]
                    
                    click.echo(f"│ {agent_id:<19} │ {agent_type:<11} │ {status:<10} │ {capabilities:<15} │")
                    
                click.echo("└─────────────────────┴─────────────┴────────────┴─────────────────┘")
                
                click.echo(f"\n🔗 Connections ({len(edges)}):")
                for edge in edges[:5]:  # Show first 5 connections
                    source = edge.get('source_agent', 'unknown')
                    target = edge.get('target_agent', 'unknown')
                    stream = edge.get('stream_name', 'unknown')
                    click.echo(f"   {source} → {target} (via {stream})")
                    
                if len(edges) > 5:
                    click.echo(f"   ... and {len(edges) - 5} more connections")
                    
            elif format == 'graph':
                click.echo("📊 Topology Graph (Mermaid format):")
                click.echo("```mermaid")
                click.echo("graph TD")
                
                nodes = topology.get('nodes', [])
                edges = topology.get('edges', [])
                
                for node in nodes:
                    node_id = node.get('id', 'unknown').replace('-', '_')
                    node_type = node.get('type', 'unknown')
                    click.echo(f"    {node_id}[\"{node.get('id')}<br/>{node_type}\"]")
                    
                for edge in edges:
                    source = edge.get('source_agent', 'unknown').replace('-', '_')
                    target = edge.get('target_agent', 'unknown').replace('-', '_')
                    click.echo(f"    {source} --> {target}")
                    
                click.echo("```")
                
            # Show metrics
            generation_time = meta.get('generation_time_ms', 0)
            click.echo(f"\n📊 Metrics:")
            click.echo(f"   Generation Time: {generation_time:.1f}ms")
            click.echo(f"   Agent Count: {topology.get('agent_count', 0)}")
            click.echo(f"   Connection Count: {topology.get('connection_count', 0)}")
            
    asyncio.run(get_topology())

# Permissions commands group
@cli.group() 
def permissions():
    """Permission management commands (SWS-110)"""
    pass

@permissions.command()
@click.argument('agent_id')
@click.argument('role', type=click.Choice(['internal_core', 'internal_service', 'external_developer', 'external_premium', 'system_admin']))
@click.pass_context
def register(ctx, agent_id, role):
    """
    Register agent with role-based permissions
    
    Example:
        sws permissions register my_agent external_developer
    """
    
    async def register_agent():
        click.echo(f"🔐 Registering agent: {agent_id}")
        click.echo(f"👤 Role: {role}")
        
        async with SWSClient(ctx.obj['api_url']) as client:
            result = await client.register_agent_permissions(agent_id, role)
            
            if result.get('success'):
                click.echo(f"✅ Agent registered successfully!")
                click.echo(f"Message: {result.get('message')}")
            else:
                click.echo(f"❌ Registration failed!")
                
    asyncio.run(register_agent())

@permissions.command()
@click.argument('agent_id')
@click.argument('target_stream')
@click.argument('operation', type=click.Choice(['read', 'write', 'admin', 'create', 'delete']))
@click.pass_context
def test(ctx, agent_id, target_stream, operation):
    """
    Test agent permissions
    
    Example:
        sws permissions test my_agent dev:test_stream read
    """
    
    async def test_permissions():
        click.echo(f"🔐 Testing permissions...")
        click.echo(f"Agent: {agent_id}")
        click.echo(f"Stream: {target_stream}")
        click.echo(f"Operation: {operation}")
        
        async with SWSClient(ctx.obj['api_url']) as client:
            result = await client.authorize_access(agent_id, target_stream, operation)
            
            allowed = result.get('allowed', False)
            reason = result.get('reason', 'No reason provided')
            latency_ms = result.get('latency_ms', 0)
            
            status_icon = "✅" if allowed else "❌"
            click.echo(f"\n{status_icon} Authorization: {'ALLOWED' if allowed else 'DENIED'}")
            click.echo(f"Reason: {reason}")
            click.echo(f"Latency: {latency_ms:.1f}ms")
            
            if result.get('cached'):
                click.echo("💾 Result was cached")
                
    asyncio.run(test_permissions())

# Documentation commands group
@cli.group()
def docs():
    """Documentation generation commands (SWS-130)"""
    pass

@docs.command()
@click.argument('manifest_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output documentation file')
@click.option('--include-diagram', '-d', is_flag=True, help='Include architecture diagram')
@click.pass_context
def generate(ctx, manifest_file, output, include_diagram):
    """
    Generate documentation from agent manifest
    
    Example:
        sws docs generate agent_manifest.yaml --output=README.md
    """
    
    async def generate_docs():
        click.echo(f"📖 Generating documentation from: {manifest_file}")
        
        # Load manifest
        manifest_path = Path(manifest_file)
        if manifest_path.suffix in ['.yaml', '.yml']:
            with open(manifest_path, 'r') as f:
                manifest = yaml.safe_load(f)
        elif manifest_path.suffix == '.json':
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
        else:
            raise click.ClickException("Manifest file must be .yaml, .yml, or .json")
            
        async with SWSClient(ctx.obj['api_url']) as client:
            result = await client.generate_documentation(manifest)
            
            if result.get('success'):
                agent_id = result.get('agent_id', 'unknown')
                quality_score = result.get('quality_score', 0)
                auto_enhanced = result.get('auto_enhanced', False)
                generation_time = result.get('generation_time_seconds', 0)
                
                click.echo(f"✅ Documentation generated for: {agent_id}")
                click.echo(f"📊 Quality Score: {quality_score:.1%}")
                click.echo(f"⏱️  Generation Time: {generation_time:.1f}s")
                
                if auto_enhanced:
                    click.echo("✨ Documentation was auto-enhanced")
                    
                documentation = result.get('documentation')
                if documentation:
                    if output:
                        with open(output, 'w') as f:
                            f.write(documentation)
                        click.echo(f"💾 Documentation saved to: {output}")
                    else:
                        click.echo("\n" + "="*60)
                        click.echo(documentation)
                        
                diagram = result.get('diagram')
                if diagram and include_diagram:
                    diagram_file = f"{agent_id}_architecture.mmd"
                    with open(diagram_file, 'w') as f:
                        f.write(diagram)
                    click.echo(f"📊 Diagram saved to: {diagram_file}")
                    
            else:
                click.echo(f"❌ Documentation generation failed!")
                if result.get('error_message'):
                    click.echo(f"Error: {result.get('error_message')}")
                    
    asyncio.run(generate_docs())

@docs.command()
@click.pass_context  
def standards(ctx):
    """Show documentation quality standards"""
    
    async def show_standards():
        async with SWSClient(ctx.obj['api_url']) as client:
            async with client.session.get(f"{client.api_url}/docs/quality/standards") as response:
                if response.status == 200:
                    data = await response.json()
                    target = data.get('quality_target', 0.98)
                    rules = data.get('quality_rules', [])
                    
                    click.echo(f"📋 Documentation Quality Standards")
                    click.echo(f"🎯 Target Quality Score: {target:.1%}")
                    click.echo()
                    
                    click.echo("📏 Quality Rules:")
                    for rule in rules:
                        name = rule.get('name', 'unknown')
                        description = rule.get('description', 'No description')
                        weight = rule.get('weight', 0)
                        click.echo(f"   • {name} (weight: {weight})")
                        click.echo(f"     {description}")
                        click.echo()
                        
                else:
                    click.echo("❌ Failed to fetch quality standards")
                    
    asyncio.run(show_standards())

# Platform status command
@cli.command()
@click.pass_context
def status(ctx):
    """Show platform status and metrics"""
    
    async def show_status():
        async with SWSClient(ctx.obj['api_url']) as client:
            # Get platform status
            async with client.session.get(f"{client.api_url}/platform/status") as response:
                if response.status == 200:
                    status_data = await response.json()
                    
                    platform = status_data.get('platform', 'Unknown')
                    version = status_data.get('version', 'Unknown')
                    status = status_data.get('status', 'Unknown')
                    components = status_data.get('components', {})
                    capabilities = status_data.get('capabilities', [])
                    
                    click.echo(f"🌐 {platform} v{version}")
                    click.echo(f"📊 Status: {status.upper()}")
                    click.echo()
                    
                    click.echo("🔧 Components:")
                    for comp_name, comp_info in components.items():
                        comp_status = comp_info.get('status', 'unknown')
                        comp_desc = comp_info.get('description', 'No description')
                        status_icon = "✅" if comp_status == "healthy" else "❌"
                        click.echo(f"   {status_icon} {comp_name}: {comp_desc}")
                        
                    click.echo(f"\n🚀 Capabilities ({len(capabilities)}):")
                    for capability in capabilities:
                        click.echo(f"   • {capability.replace('_', ' ').title()}")
                        
                else:
                    click.echo("❌ Failed to fetch platform status")
                    
    asyncio.run(show_status())

if __name__ == '__main__':
    cli() 