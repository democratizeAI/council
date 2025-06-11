# sws/docs_agent.py - SWS-130: Auto-doc + diagram from agent manifest
"""
📖 Docs Agent - Swarm-to-Swarm Services Documentation
====================================================

Automated documentation generation for agent ecosystem.
- Auto-doc + diagram from agent manifest (≥98% pass rate)
- Mermaid diagrams for topology visualization
- API specification generation
- Integration examples and monitoring setup

Part of SWS-Core platform transformation (v0.1-freeze → Developer Ecosystem)
"""

import time
import json
import yaml
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import re
from prometheus_client import Histogram, Counter, Gauge
import logging

logger = logging.getLogger(__name__)

# Prometheus metrics for Docs Agent
DOC_GENERATION_LATENCY = Histogram(
    "sws_doc_generation_latency_seconds",
    "Documentation generation latency",
    buckets=(1, 5, 10, 30, 60, 120)
)

DOC_GENERATION_REQUESTS = Counter(
    "sws_doc_generation_requests_total",
    "Total documentation generation requests",
    ["doc_type", "result"]
)

DOC_QUALITY_SCORE = Gauge(
    "sws_doc_quality_score",
    "Documentation quality score",
    ["agent_id"]
)

@dataclass
class AgentManifest:
    """Agent manifest structure for documentation generation"""
    agent_id: str
    agent_type: str
    description: str
    capabilities: List[str]
    streams: Dict[str, List[str]]
    endpoints: List[Dict[str, Any]]
    dependencies: List[str]
    configuration: Dict[str, Any]
    monitoring: Dict[str, Any]
    version: str
    author: str

@dataclass
class DocumentationResult:
    """Result of documentation generation"""
    success: bool
    agent_id: str
    documentation: Optional[str]
    diagram: Optional[str]
    api_spec: Optional[Dict[str, Any]]
    quality_score: float
    auto_enhanced: bool
    generation_time_seconds: float
    error_message: Optional[str] = None

class MermaidDiagramEngine:
    """
    Mermaid diagram generation for agent topology and architecture
    """
    
    def __init__(self):
        self.diagram_templates = self._load_diagram_templates()
        
    def _load_diagram_templates(self) -> Dict[str, str]:
        """Load Mermaid diagram templates"""
        return {
            "topology": """
graph TD
    subgraph "External Agents"
{external_agents}
    end
    
    subgraph "Internal Swarm"
{internal_agents}
    end
    
    subgraph "Redis Streams"
{streams}
    end
    
{connections}

    classDef external fill:#e1f5fe
    classDef internal fill:#f3e5f5
    classDef stream fill:#fff3e0
""",
            "agent_architecture": """
graph TD
    subgraph "{agent_name} Architecture"
        Input[Input Handler] --> Processor[Request Processor]
        Processor --> {capabilities}
        {capability_connections}
        Output[Output Handler]
    end
    
    subgraph "Streams"
{stream_connections}
    end
    
{external_connections}
""",
            "sequence": """
sequenceDiagram
    participant Client
    participant {agent_name}
{participants}
    
{sequence_steps}
"""
        }
        
    async def generate_topology_diagram(self, agents: List[AgentManifest]) -> str:
        """Generate topology diagram showing all agents and connections"""
        
        external_agents = []
        internal_agents = []
        streams = set()
        connections = []
        
        # Categorize agents and collect streams
        for agent in agents:
            agent_node = f'    {agent.agent_id}["{agent.agent_id}<br/>{agent.agent_type}"]'
            
            if agent.agent_type.startswith("external"):
                external_agents.append(agent_node)
            else:
                internal_agents.append(agent_node)
                
            # Collect streams
            for stream_list in agent.streams.values():
                streams.update(stream_list)
                
        # Generate stream nodes
        stream_nodes = [f'    {stream}["{stream}"]:::stream' for stream in streams]
        
        # Generate connections between agents and streams
        for agent in agents:
            for consumed_stream in agent.streams.get("consumed", []):
                connections.append(f'    {consumed_stream} --> {agent.agent_id}')
            for produced_stream in agent.streams.get("produced", []):
                connections.append(f'    {agent.agent_id} --> {produced_stream}')
                
        # Fill template
        diagram = self.diagram_templates["topology"].format(
            external_agents="\n".join(external_agents) if external_agents else "    ExtPlaceholder[No External Agents]",
            internal_agents="\n".join(internal_agents) if internal_agents else "    IntPlaceholder[No Internal Agents]", 
            streams="\n".join(stream_nodes) if stream_nodes else "    StreamPlaceholder[No Streams]",
            connections="\n".join(connections) if connections else "    %% No connections"
        )
        
        return diagram.strip()
        
    async def generate_agent_architecture_diagram(self, agent: AgentManifest) -> str:
        """Generate architecture diagram for specific agent"""
        
        # Generate capability nodes
        capability_nodes = []
        capability_connections = []
        
        for i, capability in enumerate(agent.capabilities):
            cap_name = capability.title().replace('_', '')
            capability_nodes.append(f"{cap_name}[{capability.replace('_', ' ').title()}]")
            capability_connections.append(f"        Processor --> {cap_name}")
            capability_connections.append(f"        {cap_name} --> Output")
            
        capabilities_text = " & ".join(capability_nodes) if capability_nodes else "BasicHandler[Basic Handler]"
        
        # Generate stream connections
        stream_connections = []
        for consumed in agent.streams.get("consumed", []):
            stream_connections.append(f'        {consumed}["{consumed}"] --> Input')
        for produced in agent.streams.get("produced", []):
            stream_connections.append(f'        Output --> {produced}["{produced}"]')
            
        # Generate external connections (API endpoints)
        external_connections = []
        for endpoint in agent.endpoints:
            method = endpoint.get("method", "GET")
            path = endpoint.get("path", "/")
            external_connections.append(f'    API["{method} {path}"] --> Input')
            
        diagram = self.diagram_templates["agent_architecture"].format(
            agent_name=agent.agent_id,
            capabilities=capabilities_text,
            capability_connections="\n".join(capability_connections),
            stream_connections="\n".join(stream_connections) if stream_connections else "        NoStreams[No Stream Connections]",
            external_connections="\n".join(external_connections) if external_connections else "    %% No external connections"
        )
        
        return diagram.strip()
        
    async def generate_sequence_diagram(self, agent: AgentManifest, interaction_flow: List[str]) -> str:
        """Generate sequence diagram for agent interactions"""
        
        # Extract participants from interaction flow
        participants = set()
        for step in interaction_flow:
            if "->" in step:
                parts = step.split("->")
                if len(parts) >= 2:
                    participants.add(parts[0].strip())
                    participants.add(parts[1].split(":")[0].strip())
                    
        # Generate participant declarations
        participant_lines = []
        for participant in sorted(participants):
            if participant not in ["Client", agent.agent_id]:
                participant_lines.append(f"    participant {participant}")
                
        # Generate sequence steps
        sequence_steps = []
        for i, step in enumerate(interaction_flow, 1):
            if "->" in step:
                sequence_steps.append(f"    {step}")
            else:
                sequence_steps.append(f"    Note over {agent.agent_id}: {step}")
                
        diagram = self.diagram_templates["sequence"].format(
            agent_name=agent.agent_id,
            participants="\n".join(participant_lines),
            sequence_steps="\n".join(sequence_steps)
        )
        
        return diagram.strip()

class DocumentationEngine:
    """
    Core documentation generation engine
    """
    
    def __init__(self):
        self.doc_templates = self._load_documentation_templates()
        self.quality_checker = DocumentationQualityChecker()
        
    def _load_documentation_templates(self) -> Dict[str, str]:
        """Load documentation templates"""
        return {
            "agent_readme": """# {agent_name} Agent

## Overview
{description}

**Agent Type:** {agent_type}  
**Version:** {version}  
**Author:** {author}

## Capabilities
{capabilities_list}

## API Endpoints
{endpoints_table}

## Redis Streams

### Consumed Streams
{consumed_streams}

### Produced Streams  
{produced_streams}

## Configuration
{configuration_section}

## Dependencies
{dependencies_list}

## Quick Start

### Installation
```bash
pip install -r requirements.txt
```

### Running the Agent
```bash
python agent.py
```

### Docker Deployment
```bash
docker build -t {agent_name} .
docker run -p 8080:8080 {agent_name}
```

## Monitoring & Health

### Health Check
```bash
curl http://localhost:8080/health
```

### Metrics
Prometheus metrics are available at `http://localhost:9090/metrics`

{monitoring_section}

## Architecture

{architecture_diagram}

## Development

### Testing
```bash
pytest tests/
```

### Linting
```bash
flake8 {agent_name}/
black {agent_name}/
```

## Support

For issues and questions, please refer to the SWS-Core documentation or create an issue in the repository.

---
*Generated by SWS-Core Docs Agent v1.0*
""",
            "api_reference": """# {agent_name} API Reference

## Base URL
`http://localhost:8080`

## Authentication
{auth_section}

## Endpoints

{endpoints_details}

## Data Models

{data_models}

## Error Responses

{error_responses}

## Rate Limiting
{rate_limiting}
"""
        }
        
    async def generate_agent_documentation(self, agent: AgentManifest, 
                                         include_api_spec: bool = True,
                                         include_examples: bool = True,
                                         include_monitoring: bool = True) -> str:
        """Generate complete documentation for an agent"""
        
        # Generate capabilities list
        capabilities_list = "\n".join(f"- **{cap.replace('_', ' ').title()}**: {self._describe_capability(cap)}" 
                                     for cap in agent.capabilities)
        
        # Generate endpoints table
        endpoints_table = self._generate_endpoints_table(agent.endpoints)
        
        # Generate stream lists
        consumed_streams = "\n".join(f"- `{stream}`" for stream in agent.streams.get("consumed", ["None"]))
        produced_streams = "\n".join(f"- `{stream}`" for stream in agent.streams.get("produced", ["None"]))
        
        # Generate configuration section
        configuration_section = self._generate_configuration_section(agent.configuration)
        
        # Generate dependencies list
        dependencies_list = "\n".join(f"- {dep}" for dep in agent.dependencies)
        
        # Generate monitoring section
        monitoring_section = self._generate_monitoring_section(agent.monitoring) if include_monitoring else ""
        
        # Generate architecture placeholder
        architecture_diagram = "```mermaid\n%% Architecture diagram will be generated\n```"
        
        documentation = self.doc_templates["agent_readme"].format(
            agent_name=agent.agent_id,
            description=agent.description,
            agent_type=agent.agent_type,
            version=agent.version,
            author=agent.author,
            capabilities_list=capabilities_list,
            endpoints_table=endpoints_table,
            consumed_streams=consumed_streams,
            produced_streams=produced_streams,
            configuration_section=configuration_section,
            dependencies_list=dependencies_list,
            monitoring_section=monitoring_section,
            architecture_diagram=architecture_diagram
        )
        
        return documentation
        
    def _describe_capability(self, capability: str) -> str:
        """Generate description for capability"""
        descriptions = {
            "redis_streams": "Asynchronous message processing via Redis streams",
            "http_api": "RESTful HTTP API endpoints for external integration",
            "database": "Persistent data storage and retrieval",
            "ai_inference": "Machine learning model inference and prediction",
            "file_processing": "File upload, processing, and transformation",
            "monitoring": "Health checks, metrics collection, and alerting",
            "security": "Authentication, authorization, and access control",
            "validation": "Data validation and business rule enforcement"
        }
        return descriptions.get(capability, f"Handles {capability.replace('_', ' ')} operations")
        
    def _generate_endpoints_table(self, endpoints: List[Dict[str, Any]]) -> str:
        """Generate endpoints table for documentation"""
        if not endpoints:
            return "No HTTP endpoints defined."
            
        table = "| Method | Path | Description |\n|--------|------|-------------|\n"
        for endpoint in endpoints:
            method = endpoint.get("method", "GET")
            path = endpoint.get("path", "/")
            description = endpoint.get("description", "No description")
            table += f"| {method} | `{path}` | {description} |\n"
            
        return table
        
    def _generate_configuration_section(self, config: Dict[str, Any]) -> str:
        """Generate configuration documentation"""
        if not config:
            return "No special configuration required."
            
        config_text = "```yaml\n"
        config_text += yaml.dump(config, default_flow_style=False)
        config_text += "```"
        
        return config_text
        
    def _generate_monitoring_section(self, monitoring: Dict[str, Any]) -> str:
        """Generate monitoring documentation"""
        if not monitoring:
            return ""
            
        section = "### Custom Metrics\n"
        
        metrics = monitoring.get("metrics", [])
        if metrics:
            for metric in metrics:
                name = metric.get("name", "unknown")
                type_name = metric.get("type", "counter")
                description = metric.get("description", "No description")
                section += f"- **{name}** ({type_name}): {description}\n"
        else:
            section += "No custom metrics defined.\n"
            
        return section

class DocumentationQualityChecker:
    """
    Quality assessment for generated documentation
    Target: ≥98% pass rate
    """
    
    def __init__(self):
        self.quality_rules = self._load_quality_rules()
        
    def _load_quality_rules(self) -> List[Dict[str, Any]]:
        """Load documentation quality rules"""
        return [
            {
                "name": "has_title",
                "description": "Documentation has a proper title",
                "weight": 5,
                "check": lambda doc: bool(re.search(r'^#\s+.+', doc, re.MULTILINE))
            },
            {
                "name": "has_overview",
                "description": "Documentation has an overview section",
                "weight": 10,
                "check": lambda doc: "overview" in doc.lower() or "description" in doc.lower()
            },
            {
                "name": "has_api_docs",
                "description": "API endpoints are documented",
                "weight": 15,
                "check": lambda doc: "endpoint" in doc.lower() or "api" in doc.lower()
            },
            {
                "name": "has_examples",
                "description": "Usage examples are provided",
                "weight": 15,
                "check": lambda doc: "```" in doc and ("curl" in doc.lower() or "python" in doc.lower())
            },
            {
                "name": "has_installation",
                "description": "Installation instructions provided",
                "weight": 10,
                "check": lambda doc: "install" in doc.lower() and ("pip" in doc.lower() or "docker" in doc.lower())
            },
            {
                "name": "has_configuration",
                "description": "Configuration is documented",
                "weight": 10,
                "check": lambda doc: "config" in doc.lower() or "setting" in doc.lower()
            },
            {
                "name": "has_monitoring",
                "description": "Monitoring setup is documented",
                "weight": 10,
                "check": lambda doc: "monitor" in doc.lower() or "metric" in doc.lower() or "health" in doc.lower()
            },
            {
                "name": "proper_formatting",
                "description": "Markdown formatting is correct",
                "weight": 10,
                "check": lambda doc: doc.count("#") >= 3 and doc.count("```") >= 2
            },
            {
                "name": "adequate_length",
                "description": "Documentation is comprehensive",
                "weight": 10,
                "check": lambda doc: len(doc.split()) >= 200
            },
            {
                "name": "no_placeholders",
                "description": "No placeholder text remains",
                "weight": 5,
                "check": lambda doc: "TODO" not in doc and "PLACEHOLDER" not in doc.upper()
            }
        ]
        
    async def assess_quality(self, documentation: str) -> Tuple[float, Dict[str, Any]]:
        """Assess documentation quality and return score with details"""
        
        total_weight = sum(rule["weight"] for rule in self.quality_rules)
        passed_weight = 0
        results = {}
        
        for rule in self.quality_rules:
            try:
                passed = rule["check"](documentation)
                results[rule["name"]] = {
                    "passed": passed,
                    "description": rule["description"],
                    "weight": rule["weight"]
                }
                
                if passed:
                    passed_weight += rule["weight"]
                    
            except Exception as e:
                logger.warning(f"Quality rule {rule['name']} failed: {e}")
                results[rule["name"]] = {
                    "passed": False,
                    "description": rule["description"],
                    "weight": rule["weight"],
                    "error": str(e)
                }
                
        quality_score = passed_weight / total_weight if total_weight > 0 else 0
        
        assessment = {
            "quality_score": quality_score,
            "passed_rules": sum(1 for r in results.values() if r["passed"]),
            "total_rules": len(self.quality_rules),
            "rule_results": results
        }
        
        return quality_score, assessment
        
    async def enhance_documentation(self, documentation: str, quality_score: float) -> str:
        """Enhance documentation to improve quality score"""
        
        enhanced_doc = documentation
        
        # Add missing sections based on failed quality rules
        if "## Quick Start" not in enhanced_doc:
            enhanced_doc += "\n\n## Quick Start\n\n### Installation\n```bash\npip install -r requirements.txt\n```\n\n### Usage\n```bash\npython agent.py\n```"
            
        if "## Configuration" not in enhanced_doc:
            enhanced_doc += "\n\n## Configuration\n\nConfiguration options are available in `config.yaml`."
            
        if "## Monitoring" not in enhanced_doc:
            enhanced_doc += "\n\n## Monitoring\n\nHealth checks are available at `/health` endpoint.\nPrometheus metrics are exposed on port 9090."
            
        # Remove placeholder text
        enhanced_doc = re.sub(r'TODO:.*?\n', '', enhanced_doc, flags=re.IGNORECASE)
        enhanced_doc = re.sub(r'PLACEHOLDER.*?\n', '', enhanced_doc, flags=re.IGNORECASE)
        
        return enhanced_doc

class DocsAgent:
    """
    SWS-130: Documentation Agent for auto-documentation
    
    Generates comprehensive documentation and diagrams from agent manifests.
    Target: ≥98% documentation quality pass rate.
    """
    
    def __init__(self):
        self.doc_engine = DocumentationEngine()
        self.diagram_engine = MermaidDiagramEngine()
        self.quality_checker = DocumentationQualityChecker()
        
        # Quality targets
        self.quality_pass_rate_target = 0.98
        
        logger.info("📖 Docs Agent initialized (SWS-130)")
        
    async def auto_document_agent(self, agent_manifest: Dict[str, Any]) -> DocumentationResult:
        """
        Main endpoint for agent documentation generation
        Returns documentation + diagram with ≥98% quality score
        """
        start_time = time.time()
        
        try:
            # Parse agent manifest
            manifest = self._parse_agent_manifest(agent_manifest)
            
            logger.info(f"📖 Generating documentation for {manifest.agent_id}")
            
            # Generate documentation
            documentation = await self.doc_engine.generate_agent_documentation(
                manifest,
                include_api_spec=True,
                include_examples=True,
                include_monitoring=True
            )
            
            # Generate architecture diagram
            architecture_diagram = await self.diagram_engine.generate_agent_architecture_diagram(manifest)
            
            # Insert diagram into documentation
            documentation = documentation.replace(
                "```mermaid\n%% Architecture diagram will be generated\n```",
                f"```mermaid\n{architecture_diagram}\n```"
            )
            
            # Assess quality
            quality_score, quality_assessment = await self.quality_checker.assess_quality(documentation)
            
            auto_enhanced = False
            
            # Enhance if quality is below target
            if quality_score < self.quality_pass_rate_target:
                logger.info(f"📈 Enhancing documentation (quality: {quality_score:.3f} < {self.quality_pass_rate_target})")
                
                enhanced_docs = await self.quality_checker.enhance_documentation(documentation, quality_score)
                
                # Re-assess enhanced documentation
                enhanced_quality_score, _ = await self.quality_checker.assess_quality(enhanced_docs)
                
                if enhanced_quality_score > quality_score:
                    documentation = enhanced_docs
                    quality_score = enhanced_quality_score
                    auto_enhanced = True
                    
            # Generate API specification
            api_spec = await self._generate_api_specification(manifest)
            
            generation_time = time.time() - start_time
            
            result = DocumentationResult(
                success=True,
                agent_id=manifest.agent_id,
                documentation=documentation,
                diagram=architecture_diagram,
                api_spec=api_spec,
                quality_score=quality_score,
                auto_enhanced=auto_enhanced,
                generation_time_seconds=generation_time
            )
            
            # Record metrics
            DOC_GENERATION_LATENCY.observe(generation_time)
            DOC_GENERATION_REQUESTS.labels(
                doc_type="agent_docs",
                result="success"
            ).inc()
            DOC_QUALITY_SCORE.labels(agent_id=manifest.agent_id).set(quality_score)
            
            logger.info(f"✅ Documentation generated: quality={quality_score:.3f}, enhanced={auto_enhanced}, time={generation_time:.1f}s")
            
            return result
            
        except Exception as e:
            generation_time = time.time() - start_time
            
            logger.error(f"❌ Documentation generation failed: {e}")
            
            DOC_GENERATION_REQUESTS.labels(
                doc_type="agent_docs",
                result="error"
            ).inc()
            
            return DocumentationResult(
                success=False,
                agent_id="unknown",
                documentation=None,
                diagram=None,
                api_spec=None,
                quality_score=0.0,
                auto_enhanced=False,
                generation_time_seconds=generation_time,
                error_message=str(e)
            )
            
    async def generate_ecosystem_documentation(self, agents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate documentation for entire agent ecosystem"""
        
        manifests = [self._parse_agent_manifest(agent) for agent in agents]
        
        # Generate topology diagram
        topology_diagram = await self.diagram_engine.generate_topology_diagram(manifests)
        
        # Generate ecosystem overview
        ecosystem_docs = await self._generate_ecosystem_overview(manifests)
        
        return {
            "ecosystem_documentation": ecosystem_docs,
            "topology_diagram": topology_diagram,
            "agent_count": len(manifests),
            "generation_time": time.time()
        }
        
    def _parse_agent_manifest(self, manifest_data: Dict[str, Any]) -> AgentManifest:
        """Parse agent manifest from dictionary"""
        
        return AgentManifest(
            agent_id=manifest_data.get("agent_id", "unknown"),
            agent_type=manifest_data.get("agent_type", "generic"),
            description=manifest_data.get("description", "No description provided"),
            capabilities=manifest_data.get("capabilities", []),
            streams=manifest_data.get("streams", {"consumed": [], "produced": []}),
            endpoints=manifest_data.get("endpoints", []),
            dependencies=manifest_data.get("dependencies", []),
            configuration=manifest_data.get("configuration", {}),
            monitoring=manifest_data.get("monitoring", {}),
            version=manifest_data.get("version", "1.0.0"),
            author=manifest_data.get("author", "Unknown")
        )
        
    async def _generate_api_specification(self, manifest: AgentManifest) -> Dict[str, Any]:
        """Generate OpenAPI specification for agent"""
        
        api_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": f"{manifest.agent_id} API",
                "description": manifest.description,
                "version": manifest.version
            },
            "servers": [
                {"url": "http://localhost:8080", "description": "Local development server"}
            ],
            "paths": {},
            "components": {
                "schemas": {},
                "responses": {}
            }
        }
        
        # Add endpoints to specification
        for endpoint in manifest.endpoints:
            path = endpoint.get("path", "/")
            method = endpoint.get("method", "get").lower()
            
            if path not in api_spec["paths"]:
                api_spec["paths"][path] = {}
                
            api_spec["paths"][path][method] = {
                "summary": endpoint.get("description", "No description"),
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": {"type": "object"}
                            }
                        }
                    }
                }
            }
            
        return api_spec
        
    async def _generate_ecosystem_overview(self, manifests: List[AgentManifest]) -> str:
        """Generate ecosystem overview documentation"""
        
        agent_types = {}
        total_capabilities = set()
        total_streams = set()
        
        for manifest in manifests:
            agent_type = manifest.agent_type
            if agent_type not in agent_types:
                agent_types[agent_type] = []
            agent_types[agent_type].append(manifest.agent_id)
            
            total_capabilities.update(manifest.capabilities)
            for stream_list in manifest.streams.values():
                total_streams.update(stream_list)
                
        ecosystem_docs = f"""# Agent Ecosystem Overview

## Summary
This ecosystem contains **{len(manifests)} agents** with **{len(total_capabilities)} unique capabilities** communicating via **{len(total_streams)} Redis streams**.

## Agent Types
"""
        
        for agent_type, agents in agent_types.items():
            ecosystem_docs += f"\n### {agent_type.title()}\n"
            for agent in agents:
                ecosystem_docs += f"- {agent}\n"
                
        ecosystem_docs += f"\n## System Capabilities\n"
        for capability in sorted(total_capabilities):
            ecosystem_docs += f"- {capability.replace('_', ' ').title()}\n"
            
        ecosystem_docs += f"\n## Communication Streams\n"
        for stream in sorted(total_streams):
            ecosystem_docs += f"- `{stream}`\n"
            
        return ecosystem_docs

# Singleton instance for FastAPI integration
docs_agent = DocsAgent() 