# Phase 3: Self-Improvement Loop 🧠🔄

AutoGen Council autonomous quality improvement system with Agent-0 failure harvesting, QLoRA fine-tuning, and automatic deployment with rollback protection.

## Overview

Phase 3 completes the evolution from basic routing to a fully autonomous self-improving system:

```
🔍 Harvest failures → 🧠 Agent-0 rewrites → 🚀 QLoRA training → 📊 Auto-deploy → 🔄 Monitor & rollback
```

**Key Components:**
- **Agent-0 Failure Harvester**: Finds failed responses and rewrites them with reasoning
- **QLoRA Training Pipeline**: Nightly fine-tuning on harvested improvements
- **Deployment System**: Automatic LoRA loading with quality regression detection
- **Rollback Protection**: Emergency reversion when quality degrades

## Architecture

### 1. Memory-Driven Failure Detection
```python
# Memory tracks all Q&A with success flags
memory.add(query, {
    "response": response_text,
    "success": confidence > 0.7,  # Quality threshold
    "model": model_used,
    "timestamp": now()
})
```

### 2. Agent-0 Intelligent Rewriting
```python
# Agent-0 prompt for failure improvement
agent0_prompt = f"""You are Agent-0, an expert response improver.

QUERY: {original_query}
BAD_RESPONSE: {failed_response}

Your task: Provide a much better response with clear reasoning.

Format:
REASONING: [Step-by-step thinking]
ANSWER: [Improved response]"""
```

### 3. QLoRA Fine-Tuning Pipeline
- **Training Data**: JSONL format with instruction/output pairs
- **LoRA Config**: Rank 16, Alpha 32, targeting attention layers
- **Quality Filtering**: Only high-quality rewrites (score ≥ 0.7)

### 4. Deployment with Monitoring
- **Pre-deployment Validation**: File checks, metrics snapshot
- **Gradual Rollout**: Health monitoring with regression detection
- **Automatic Rollback**: <85% success rate or >1000ms latency triggers reversion

## Components

### Core Scripts

#### 1. `harvest_failures.py` - Agent-0 Failure Harvester
```bash
python harvest_failures.py
```

**Features:**
- Scans memory for yesterday's failed responses
- Uses Agent-0 Council voting to generate improved responses
- Quality assessment with reasoning detection
- Outputs training data in JSONL format

**Output Example:**
```json
{
  "instruction": "What is machine learning?",
  "output": "Machine learning is a subset of AI that enables computers to learn from data without being explicitly programmed...",
  "reasoning": "This requires explaining a technical concept clearly with examples",
  "quality_score": 0.85
}
```

#### 2. `train_lora.sh` - QLoRA Training Pipeline
```bash
bash train_lora.sh
```

**Features:**
- Automatic training data detection
- LoRA configuration with optimized hyperparameters
- Training metrics tracking and validation
- Backup creation and failure recovery

**Configuration:**
```bash
BATCH_SIZE=4
GRADIENT_ACCUMULATION=8
LEARNING_RATE=5e-5
NUM_EPOCHS=3
LORA_RANK=16
LORA_ALPHA=32
```

#### 3. `deploy_lora.sh` - Deployment with Monitoring
```bash
bash deploy_lora.sh loras/latest
```

**Features:**
- Pre-deployment validation and metrics capture
- Symlink-based deployment for instant switching
- 60-second monitoring window with regression detection
- Automatic health checks and functional testing

**Thresholds:**
- Maximum latency: 1000ms
- Minimum success rate: 85%
- Monitoring duration: 60 seconds

#### 4. `rollback_lora.sh` - Emergency Rollback
```bash
bash rollback_lora.sh
```

**Features:**
- Automatic rollback target selection
- Failed deployment backup for analysis
- Health validation after rollback
- Alerting integration (webhook notifications)

### Automation

#### 5. `cron/nightly_improvement.sh` - Complete Pipeline
```bash
# Add to crontab for 2 AM daily execution
0 2 * * * /path/to/cron/nightly_improvement.sh
```

**Pipeline Flow:**
1. **Pre-flight checks**: Server health, disk space (2GB minimum)
2. **Failure harvesting**: Agent-0 rewriting with quality filtering
3. **QLoRA training**: Only if ≥5 high-quality examples
4. **Deployment**: With monitoring and rollback protection
5. **Validation**: Health checks and functional testing
6. **Cleanup**: Old files and backups removal

**Notifications:**
- Slack/Discord webhooks for success/failure alerts
- System journal logging for monitoring integration
- Detailed logs with timing and metrics

## Quality Metrics

### Training Quality Assessment
```python
def _assess_quality(query, bad_response, good_response):
    score = 0.5  # baseline
    
    # Length improvement (more detailed)
    if len(good_response) > len(bad_response) * 1.5:
        score += 0.2
    
    # Reasoning indicators
    reasoning_words = ["because", "therefore", "step", "first"]
    if any(word in good_response.lower() for word in reasoning_words):
        score += 0.15
    
    # Code/math improvements
    if "```" in good_response and "```" not in bad_response:
        score += 0.1
    
    return min(score, 1.0)
```

### Deployment Monitoring
```bash
# Regression detection thresholds
ROLLBACK_THRESHOLD_LATENCY=1000    # ms
ROLLBACK_THRESHOLD_SUCCESS=0.85    # 85%
MONITOR_DURATION=60                # seconds
```

## File Structure

```
├── harvest_failures.py           # Agent-0 failure harvester
├── train_lora.sh                 # QLoRA training pipeline
├── deploy_lora.sh                # Deployment with monitoring
├── rollback_lora.sh              # Emergency rollback
├── cron/
│   └── nightly_improvement.sh    # Complete automation
├── tests/phase3/
│   └── test_self_improvement.py  # Comprehensive test suite
├── training_data/                # Harvested training examples
│   └── harvest_YYYYMMDD.jsonl
├── loras/
│   ├── current → latest/         # Active LoRA symlink
│   ├── latest/                   # Newest trained LoRA
│   ├── backup_*/                 # Previous versions
│   └── rollback_*/               # Rollback targets
└── logs/
    ├── harvest_*.log             # Harvesting logs
    ├── training_*.log            # Training logs
    ├── deployment_*.log          # Deployment logs
    └── nightly_*.log             # Complete pipeline logs
```

## Usage Examples

### Manual Improvement Cycle
```bash
# 1. Harvest yesterday's failures
python harvest_failures.py

# 2. Train LoRA if enough data
bash train_lora.sh

# 3. Deploy with monitoring
bash deploy_lora.sh loras/latest

# 4. Monitor for regressions (automatic)
```

### Emergency Rollback
```bash
# Automatic rollback on quality regression
bash rollback_lora.sh

# Check rollback status
cat loras/current/rollback_summary.json
```

### Nightly Automation
```bash
# Set up cron job
echo "0 2 * * * cd /path/to/project && bash cron/nightly_improvement.sh" | crontab -

# Check last run
tail -f logs/nightly_*.log
```

## Testing

### Comprehensive Test Suite
```bash
python tests/phase3/test_self_improvement.py
```

**Test Coverage:**
- Failure harvester initialization and quality assessment
- Training data format validation
- LoRA file structure verification
- Deployment summary format checking
- Regression detection logic
- End-to-end simulation

### Expected Output
```
🧪 Phase 3 Self-Improvement Test Suite
✅ Harvester initialization test passed
✅ Quality assessment test passed (scores: 0.95, 0.95)
✅ Training data format test passed
✅ LoRA file validation test passed
✅ Deployment summary format test passed
✅ Regression detection test passed
🎉 All Phase 3 tests completed successfully!
```

## Monitoring and Alerts

### Prometheus Metrics
```
# Training completion
autogen_training_completed_total
autogen_training_duration_seconds
autogen_training_loss

# Deployment success
autogen_deployment_success_total
autogen_rollback_triggered_total

# Quality metrics
autogen_quality_improvement_ratio
autogen_agent0_rewrite_success_rate
```

### Webhook Notifications
```bash
# Set notification webhook
export NOTIFICATION_WEBHOOK="https://hooks.slack.com/services/..."

# Automatic notifications on:
# - Training completion
# - Deployment success/failure
# - Quality regression rollback
# - Pipeline errors
```

## Performance Expectations

### Timing Targets
- **Harvest**: 30 minutes (varies with failure count)
- **Training**: 30 minutes (2-3 epochs on local GPU)
- **Deployment**: 10 minutes (includes 60s monitoring)
- **Total Pipeline**: ~1.5 hours end-to-end

### Quality Improvements
- **Success Rate**: Target +5-10% improvement per cycle
- **Response Quality**: Reasoning, accuracy, completeness
- **Latency**: Maintain <1s p95 latency
- **Memory Efficiency**: LoRA adapters ~50MB vs full model fine-tuning

## Configuration

### Environment Variables
```bash
# Optional configuration
export NOTIFICATION_WEBHOOK="https://hooks.slack.com/..."
export MIN_FAILURES_TO_TRAIN=5
export LORA_RANK=16
export LORA_ALPHA=32
export ROLLBACK_THRESHOLD_LATENCY=1000
export ROLLBACK_THRESHOLD_SUCCESS=0.85
```

### Customization
- **Quality thresholds**: Adjust in `harvest_failures.py`
- **Training hyperparameters**: Modify in `train_lora.sh`
- **Monitoring duration**: Change in `deploy_lora.sh`
- **Notification format**: Update webhook payload in `nightly_improvement.sh`

## Troubleshooting

### Common Issues

#### No Training Data Generated
```bash
# Check memory has failed responses
python -c "from faiss_memory import FaissMemory; m=FaissMemory(); print(f'Memory size: {len(m.meta)}')"

# Check Agent-0 rewriting
python harvest_failures.py  # Should show rewrite attempts
```

#### Training Fails
```bash
# Check disk space (need 2GB+)
df -h .

# Check GPU memory
nvidia-smi

# Validate training data
head training_data/harvest_*.jsonl
```

#### Deployment Rollback
```bash
# Check rollback reason
cat loras/current/rollback_summary.json

# Review deployment logs
tail logs/deployment_*.log

# Manual health check
curl http://localhost:8000/health
```

#### Pipeline Stuck
```bash
# Check server health
curl http://localhost:8000/health

# Review nightly logs
tail -f logs/nightly_*.log

# Manual component testing
python harvest_failures.py
bash train_lora.sh
bash deploy_lora.sh loras/latest
```

## Next Steps

Phase 3 completes the core self-improvement loop. Future enhancements:

1. **Advanced Quality Metrics**: LLM-based quality scoring
2. **Multi-Modal Training**: Code, math, reasoning specialization  
3. **Federated Learning**: Multiple Council instances sharing improvements
4. **Real-Time Adaptation**: Online learning during conversations
5. **Benchmark Integration**: Automated evaluation on standard datasets

## Success Metrics

Phase 3 implementation is successful when:

- ✅ Nightly pipeline runs autonomously without intervention
- ✅ Quality regressions are detected and rolled back automatically
- ✅ System gradually improves over weeks of operation
- ✅ Failed responses decrease over time
- ✅ User satisfaction increases with more accurate responses

**The Council is now fully autonomous and self-improving!** 🎉 