# SciWave: Triple Agent Synergy for Science Planning & Literature Summarization

**🌊 Long-term science planning & literature summarization powered by autonomous multi-agent coordination**

## Overview

SciWave implements a production-grade triple agent synergy system that autonomously discovers, reviews, and validates scientific literature. Built on the AutoGen Council enterprise swarm architecture, it provides:

- **SCI-100**: 📥 Fetch Agent - ArXiv + PubMed daily scraper  
- **SCI-110**: 🧠 Review Agent - Extractive + abstractive paper summarization
- **SCI-120**: 👥 Peer Agent - Self-critique + cross-agent comparison

## Architecture

### Triple Agent Synergy Pattern

```
📥 FETCH (SCI-100)     🧠 REVIEW (SCI-110)     👥 PEER (SCI-120)
     ↓                        ↓                       ↓
ArXiv/PubMed Scraper → Paper Summarization → Quality Assessment
     ↓                        ↓                       ↓
Redis Stream Queue  → BLEU Score Tracking → Confidence Delta
     ↓                        ↓                       ↓
KPI: ≥3 successful   KPI: BLEU ≥ 0.85      KPI: δ confidence ≥ 2%
```

### Enterprise Infrastructure

- **Redis Streams**: Asynchronous agent coordination
- **Prometheus Metrics**: Real-time KPI tracking  
- **FastAPI Service**: Production health checks
- **Docker Swarm**: Containerized deployment
- **Grafana Dashboards**: Visual monitoring

## Quick Start

### Prerequisites

- Docker & Docker Compose
- 8GB+ RAM recommended
- Internet access for paper fetching

### 1. Deploy SciWave

```bash
# Make deployment script executable (Linux/Mac)
chmod +x scripts/deploy_sciwave.sh

# Deploy full stack
./scripts/deploy_sciwave.sh deploy
```

**Windows**: Use `bash scripts/deploy_sciwave.sh deploy` or execute commands manually from the script.

### 2. Verify Deployment

```bash
# Check service health
curl http://localhost:8080/health

# View real-time status
curl http://localhost:8080/status
```

### 3. Access Interfaces

- **SciWave API**: http://localhost:8080
- **Health Check**: http://localhost:8080/health  
- **Metrics**: http://localhost:8080/metrics
- **Prometheus**: http://localhost:9091
- **Grafana**: http://localhost:3001 (admin/sciwave123)

## Agent Details

### SCI-100: Fetch Agent 📥

**Purpose**: Autonomous research paper discovery and intake

**Sources**:
- ArXiv API (CS.AI, CS.CL, CS.LG, STAT.ML, CS.CV)
- PubMed API (AI/ML/NLP mesh terms)

**KPI Gate**: `arxiv_pull_success_total ≥ 3`

**Features**:
- Daily automated fetching
- 7-day sliding window
- Structured metadata extraction
- Redis stream publication

**Configuration**:
```python
fetch_config = {
    'arxiv_queries': [
        'cat:cs.AI OR cat:cs.CL OR cat:cs.LG',
        'cat:stat.ML', 
        'cat:cs.CV'
    ],
    'pubmed_queries': [
        'artificial intelligence[MeSH Terms]',
        'machine learning[Title/Abstract]'
    ],
    'max_results_per_query': 10
}
```

### SCI-110: Review Agent 🧠

**Purpose**: Intelligent paper analysis and summarization

**Capabilities**:
- Extractive summarization (TF-IDF sentence ranking)
- Abstractive summarization (paraphrasing + condensation)
- Methodology extraction
- Key findings identification
- Significance scoring

**KPI Gate**: `summary_bleu ≥ 0.85`

**Quality Metrics**:
- BLEU score vs original abstract
- Readability score (Flesch reading ease)
- Confidence scoring
- Technical density analysis

**Example Output**:
```json
{
  "paper_id": "arxiv:2024.01234",
  "extractive_summary": "Key sentences from original abstract...",
  "abstractive_summary": "Condensed, rephrased summary...",
  "key_findings": ["15% accuracy improvement", "30% faster inference"],
  "methodology": "Transformer-based approach with attention mechanisms",
  "bleu_score": 0.87,
  "confidence": 0.82
}
```

### SCI-120: Peer Agent 👥

**Purpose**: Quality assurance through peer review simulation

**Review Dimensions**:
- **Clarity**: Readability and structure assessment
- **Completeness**: Coverage of key elements
- **Accuracy**: Technical detail verification  
- **Conciseness**: Optimal length evaluation
- **Significance**: Impact communication

**KPI Gate**: `delta_confidence ≥ 2%`

**Cross-Agent Comparison**:
- TF-IDF similarity scoring
- Difference identification
- Consensus point extraction
- Improvement recommendations

**Confidence Adjustment Logic**:
```python
# Quality score influences confidence
confidence_adjustment = (quality_score - 0.5) * 0.3  # ±15% max
new_confidence = clamp(original_confidence + adjustment, 0.0, 1.0)
delta_confidence = new_confidence - original_confidence
```

## API Reference

### Core Endpoints

#### Health & Status
```bash
GET /health              # Service health check
GET /ready               # Kubernetes readiness probe  
GET /status              # Detailed system status
GET /metrics             # Prometheus metrics
```

#### Agent Operations
```bash
POST /cycle              # Trigger manual research cycle
GET /agents/{name}/metrics  # Individual agent metrics
```

#### Example Health Response
```json
{
  "status": "healthy",
  "redis": true,
  "agents": {
    "fetch": true,
    "review": true, 
    "peer": true
  },
  "uptime_seconds": 3600,
  "last_cycle": "2024-01-15T10:30:00Z"
}
```

## Configuration

### Environment Variables

```bash
# Core Configuration
REDIS_URL=redis://redis:6379
SCIWAVE_BACKGROUND_ENABLED=true
SCIWAVE_CYCLE_INTERVAL=3600  # 1 hour

# Agent-Specific
MIN_BLEU_SCORE=0.85
MIN_DELTA_CONFIDENCE=0.02
FETCH_INTERVAL=3600

# Service Configuration  
PORT=8080
LOG_LEVEL=INFO
```

### Docker Compose Override

Create `docker-compose.override.yml`:
```yaml
version: '3.8'
services:
  sciwave:
    environment:
      - SCIWAVE_CYCLE_INTERVAL=1800  # 30 minutes
      - MIN_BLEU_SCORE=0.80          # Lower threshold
```

## Monitoring & Metrics

### Prometheus Metrics

**Cycle Metrics**:
- `sciwave_cycles_total` - Total cycles executed
- `sciwave_cycle_duration_seconds` - Cycle execution time
- `sciwave_success_rate` - Overall success rate

**Agent Metrics**:
- `sciwave_papers_processed_total` - Papers processed
- `sciwave_kpi_gates_passed_total{agent}` - KPI gates passed
- `sciwave_agent_health{agent}` - Agent health status

**Example Queries**:
```promql
# Success rate over time
rate(sciwave_kpi_gates_passed_total[5m])

# Average cycle duration
avg(sciwave_cycle_duration_seconds)

# Agent health status
sciwave_agent_health
```

### Grafana Dashboards

Pre-configured dashboards include:

1. **SciWave Overview**: High-level metrics and health
2. **Agent Performance**: Individual agent KPIs
3. **Paper Pipeline**: Flow from fetch → review → peer
4. **Quality Metrics**: BLEU scores, confidence trends

## Operational Procedures

### Daily Operations

**Morning Check** (automated):
```bash
# Verify overnight cycles
./scripts/deploy_sciwave.sh health

# Check paper intake
curl -s http://localhost:8080/agents/fetch/metrics | jq '.papers_fetched_today'
```

**Manual Cycle Trigger**:
```bash
# Force immediate research cycle
./scripts/deploy_sciwave.sh cycle

# Monitor progress
curl -s http://localhost:8080/status | jq '.swarm.swarm_metrics'
```

### Troubleshooting

**Health Check Failures**:
```bash
# Check container status
docker-compose -f docker-compose.sciwave.yml ps

# View logs
./scripts/deploy_sciwave.sh logs sciwave

# Restart unhealthy services
./scripts/deploy_sciwave.sh restart
```

**KPI Gate Failures**:
```bash
# Check agent-specific metrics
curl http://localhost:8080/agents/review/metrics

# Analyze quality trends
curl http://localhost:8080/metrics | grep bleu_score
```

**Redis Connection Issues**:
```bash
# Test Redis connectivity
docker exec sciwave-redis redis-cli ping

# Check stream health
docker exec sciwave-redis redis-cli XINFO STREAMS
```

### Performance Tuning

**Fetch Agent Optimization**:
```python
# Increase query diversity
fetch_config['arxiv_queries'].append('cat:cs.RO')  # Robotics
fetch_config['max_results_per_query'] = 15         # More papers
```

**Review Agent Optimization**:
```python
# Adjust quality thresholds
review_config['min_bleu_score'] = 0.80  # More lenient
review_config['summary_max_length'] = 300  # Longer summaries
```

**Peer Agent Optimization**:
```python
# Modify confidence sensitivity
peer_config['min_delta_confidence'] = 0.015  # 1.5% threshold
peer_config['quality_weights'] = {            # Custom weights
    'clarity': 0.3,
    'completeness': 0.3, 
    'accuracy': 0.4
}
```

## Integration with AutoGen Council

SciWave integrates seamlessly with the main AutoGen Council ecosystem:

### Shared Infrastructure
- Redis coordination bus
- Prometheus monitoring stack
- Docker orchestration
- Enterprise governance (Spec-Out)

### Council Router Integration
```python
# Register SciWave as specialist
router.register_specialist('research', 
    endpoint='http://sciwave:8080/cycle',
    confidence_threshold=0.7
)

# Route research queries to SciWave
if 'research' in query.lower() or 'papers' in query.lower():
    response = await call_specialist('research', query)
```

### Shared Memory System
```python
# Store research results in Council memory
from common.scratchpad import write as sp_write

sp_write(
    session_id=session_id,
    agent="sciwave_research",
    content=research_summary,
    tags=["research", "papers", paper_id],
    entry_type="research_result"
)
```

## Development & Testing

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt
pip install nltk scikit-learn textstat redis aiohttp

# Download NLTK data  
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# Test individual agents
python agents/sciwave/fetch_agent.py
python agents/sciwave/review_agent.py  
python agents/sciwave/peer_agent.py
```

### Unit Testing

```bash
# Run agent tests
./scripts/deploy_sciwave.sh test

# Test specific agent
docker-compose exec sciwave python -m pytest agents/sciwave/test_fetch_agent.py
```

### Integration Testing

```bash
# Full cycle test
curl -X POST http://localhost:8080/cycle

# Verify results
curl http://localhost:8080/status | jq '.phases'
```

## Roadmap

### Phase 1: Core Triple Agent (✅ Complete)
- [x] SCI-100: Fetch Agent with ArXiv/PubMed
- [x] SCI-110: Review Agent with BLEU scoring
- [x] SCI-120: Peer Agent with confidence delta
- [x] Redis streams coordination
- [x] Production service wrapper

### Phase 2: Enhanced Quality (In Progress)
- [ ] Local LLM integration for abstractive summaries
- [ ] Advanced citation network analysis
- [ ] Multi-language paper support
- [ ] Custom research domain configurations

### Phase 3: Advanced Analytics (Future)
- [ ] Trend detection and prediction
- [ ] Research gap identification  
- [ ] Automated literature review generation
- [ ] Collaboration network mapping

### Phase 4: Enterprise Integration (Future)
- [ ] LDAP/SSO authentication
- [ ] API rate limiting and quotas
- [ ] Multi-tenant isolation
- [ ] Enterprise audit logging

## Contributing

SciWave follows the AutoGen Council development standards:

1. **Spec-Out Governance**: All features require SPEC-### documents
2. **KPI Gates**: Maintain measurement criteria
3. **Enterprise Testing**: 24h soak → Fast Gauntlet → Release
4. **Accuracy Guards**: Never compromise quality for speed

### Development Workflow

1. Create feature SPEC-### document
2. Implement with KPI tracking
3. Add Prometheus metrics
4. Update documentation
5. Submit for peer review
6. Pass enterprise certification

## Support

- **Documentation**: `/docs/sciwave/`
- **API Reference**: `http://localhost:8080/docs`
- **Metrics Dashboard**: `http://localhost:3001`
- **Health Monitoring**: `http://localhost:8080/health`

For enterprise support and custom deployments, contact the AutoGen Council team.

---

**SciWave**: Where autonomous agents meet rigorous science. 🌊🔬

*Built on the AutoGen Council v0.1-freeze enterprise multi-agent infrastructure.* 