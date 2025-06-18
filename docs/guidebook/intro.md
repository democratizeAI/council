# Autonomous Builder Swarm Guide

## Introduction

This is the autonomous builder swarm system documentation. The system includes:

- **o3 Council**: Decision making and routing
- **Builder Swarm**: Code generation and deployment  
- **Guardian**: Monitoring and auto-restart
- **Gemini**: Audit and safety oversight

## Current Status

- Version: v10.3-ε-autonomous
- Mode: Fully Autonomous
- Safety Systems: Active
- Performance: 65ms p95 latency

## Key Components

### Router Cascade
- Fast routing with specialist voting
- Redis caching for cost optimization
- Template stub detection

### Cost Protection
- Daily budget caps ($0-$10)
- Zero cloud spending mode active
- Local processing prioritized

### Security
- SBOM scanning with syft
- CVE blocking on critical vulnerabilities
- Gemini audit authority maintained 