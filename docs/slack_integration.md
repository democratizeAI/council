# Slack ↔ Trinity Integration Documentation

## Overview

This document describes the Slack integration for the Trinity autonomous system, enabling command and control through Slack channels with full correlation tracking and error handling.

## Architecture

```
Slack Commands → FastAPI Router → Council/o3 → Builder → PatchCtl → Slack Notifications
       ↑                              ↓
   Correlation ID ←─────────────────────┘
```

## Features

- **5 Slash Commands**: `/o3`, `/opus`, `/ticket`, `/patches`, `/status`
- **Correlation Tracking**: Every request gets a unique 8-character tracking ID
- **HMAC Security**: All Slack requests verified with signing secret
- **Async Processing**: Commands queued for background processing
- **Error Handling**: Retry buttons and failure notifications
- **CI/CD Hooks**: Builder and PatchCtl post success/failure to Slack

## Slack App Configuration

### Required App Settings

| Setting | Value |
|---------|-------|
| App Name | `Trinity-Ops` |
| Scopes | `commands`, `chat:write`, `chat:write.public`, `chat:write.customize`, `incoming-webhook` |
| Events API | `app_mention`, `message.channels`, `reaction_added` |

### Environment Variables

```bash
SLACK_SIGNING_SECRET=your_signing_secret_here
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
```

### Slash Commands Setup

Configure these slash commands in your Slack app:

| Command | Request URL | Description |
|---------|-------------|-------------|
| `/o3` | `https://your-domain.com/slack/commands` | Direct o3 model queries |
| `/opus` | `https://your-domain.com/slack/commands` | Council deliberation |
| `/ticket` | `https://your-domain.com/slack/commands` | Ticket management |
| `/patches` | `https://your-domain.com/slack/commands` | Patch status |
| `/status` | `https://your-domain.com/slack/commands` | Pipeline status |

### Event Subscriptions

Configure these event subscriptions:

- **Request URL**: `https://your-domain.com/slack/events`
- **Events**: `app_mention`, `message.channels`, `reaction_added`

## API Endpoints

### POST /slack/commands

Main command handler for all slash commands.

**Request Format** (form-encoded):
```
command=/o3
text=ping
user_id=U123456
trigger_id=12345.67890
```

**Response Format**:
```json
{
  "response_type": "ephemeral",
  "text": "✅ Received • tracking id `a1b2c3d4`",
  "attachments": [
    {
      "color": "good",
      "text": "Command `/o3` queued for processing"
    }
  ]
}
```

### POST /slack/interactive

Handles interactive components (buttons, modals).

**Payload Examples**:
- Retry button click
- Modal form submission

### POST /slack/events

Handles Slack Events API.

**Supported Events**:
- `url_verification` - Slack app verification challenge
- `app_mention` - @Trinity-Ops mentions  
- `reaction_added` - Emoji reactions to messages

### GET /slack/health

Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "service": "slack-integration", 
  "queue_size": 3,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### POST /slack/webhook/success

Success notification webhook for CI/CD.

**Request Body**:
```json
{
  "correlation_id": "a1b2c3d4",
  "event_type": "builder_merge",
  "message": "PR #456 merged successfully"
}
```

### POST /slack/webhook/failure

Failure notification webhook with retry option.

**Request Body**:
```json
{
  "correlation_id": "a1b2c3d4", 
  "stage": "Builder",
  "error": "Unit test failed in test_integration.py"
}
```

## Command Reference

### /o3 Command

Direct interaction with o3 model.

**Usage**:
```
/o3 ping                    # Health check
/o3 What is 2+2?           # Direct query
/o3 analyze logs           # Analysis request
```

**Response Flow**:
1. Command queued (immediate response)
2. o3 model processes query
3. Result posted to thread

### /opus Command

Council (Opus) deliberation system.

**Usage**:
```
/opus ping                 # Health check
/opus vote on issue #123   # Trigger voting
/opus status              # Council status
```

**Response Flow**:
1. Command queued
2. Council members deliberate
3. Voting results posted

### /ticket Command

Ticket management system.

**Usage**:
```
/ticket add title="Fix bug" wave=B owner=Dev effort=2h
/ticket list wave=B
/ticket status ID-123
```

**Response Flow**:
1. Ticket creation queued
2. Ledger entry created
3. Builder opens scaffold PR
4. PatchCtl deploys

### /patches Command

Query recent patch status.

**Usage**:
```
/patches                   # Recent patches
/patches wave=B           # Specific wave
/patches failed           # Failed patches
```

### /status Command

Overall pipeline status.

**Usage**:
```
/status                   # Full status
/status council          # Council only
/status builder          # Builder only
```

**Response Format**:
```
Trinity Pipeline Status
┌─────────────┬─────────────┐
│ Council     │ ✅ Healthy  │
│ Builder     │ ✅ Active   │
│ Guardian    │ ✅ Monitor  │
│ Queue Depth │ 3 items     │
└─────────────┴─────────────┘
```

## Correlation ID System

Every Slack interaction gets a unique 8-character correlation ID for end-to-end tracking.

### Correlation Flow

```
Slack Request → a1b2c3d4 → Council API → Builder → PatchCtl
      ↓              ↓           ↓          ↓         ↓
  "✅ Received"  "🟢 Queued"  "📒 Ledger"  "🔧 PR"  "🚀 Deploy"
```

### Headers

All downstream services receive:
```
X-Corr-ID: a1b2c3d4
```

### Logging

All log entries include correlation ID:
```
2024-01-15 10:30:00 INFO Processing /o3 command | corr: a1b2c3d4
2024-01-15 10:30:01 INFO Council vote started | corr: a1b2c3d4
2024-01-15 10:30:05 INFO Builder PR opened #456 | corr: a1b2c3d4
```

## Security

### HMAC Verification

All Slack requests verified using signing secret:

```python
def verify_slack_signature(body: bytes, timestamp: str, signature: str, signing_secret: str) -> bool:
    basestring = f"v0:{timestamp}:{body.decode()}"
    expected = "v0=" + hmac.new(
        signing_secret.encode(),
        basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

### Rate Limiting

Built-in protection against abuse:
- 3 commands per minute per user
- Guardian escalation for unusual patterns
- Automatic retry backoff

## Error Handling

### Error Response Format

```json
{
  "response_type": "ephemeral",
  "text": "🔴 FAIL at Builder – unit test error (see CI)",
  "attachments": [
    {
      "color": "danger",
      "actions": [
        {
          "type": "button",
          "text": "🔄 Retry",
          "action_id": "retry_command"
        }
      ]
    }
  ]
}
```

### Timeout Handling

If no response within 30 seconds:
```
🔴 TIMEOUT at Council – no response from deliberation
🔄 Auto-retry in 60 seconds or click button to retry now
```

### Guardian Escalation

Critical failures trigger Guardian alerts:
```
🚨 CRITICAL: Builder system down for 5+ minutes
📧 Escalated to #trinity-alerts
🔧 Auto-restart attempted
```

## CI/CD Integration

### Builder Hooks

In `.github/workflows/builder.yml`:

```yaml
- name: Slack success notification
  if: success()
  run: |
    curl -XPOST "${{ secrets.SLACK_WEBHOOK_URL }}/slack/webhook/success" \
    -H 'Content-Type: application/json' \
    -d '{
      "correlation_id": "${{ secrets.CORR_ID }}",
      "event_type": "builder_merge", 
      "message": "🔧 Builder merged PR ${{ github.event.pull_request.number }}"
    }'

- name: Slack failure notification  
  if: failure()
  run: |
    curl -XPOST "${{ secrets.SLACK_WEBHOOK_URL }}/slack/webhook/failure" \
    -H 'Content-Type: application/json' \
    -d '{
      "correlation_id": "${{ secrets.CORR_ID }}",
      "stage": "Builder",
      "error": "Build failed - see ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
    }'
```

### PatchCtl Hooks

In `scripts/notify_slack.sh`:

```bash
#!/bin/bash
CORR_ID=${1:-unknown}
STATUS=${2:-success}

if [ "$STATUS" = "success" ]; then
  curl -XPOST "$SLACK_WEBHOOK_URL/slack/webhook/success" \
    -H 'Content-Type: application/json' \
    -d "{
      \"correlation_id\": \"$CORR_ID\",
      \"event_type\": \"patchctl_deploy\",
      \"message\": \"🚀 PatchCtl canary deployed successfully\"
    }"
else
  curl -XPOST "$SLACK_WEBHOOK_URL/slack/webhook/failure" \
    -H 'Content-Type: application/json' \
    -d "{
      \"correlation_id\": \"$CORR_ID\", 
      \"stage\": \"PatchCtl\",
      \"error\": \"Deployment failed - check logs\"
    }"
fi
```

## Testing

### Unit Tests

Run the test suite:

```bash
pytest tests/test_slack_integration.py -v
```

### Manual Testing

Test with curl:

```bash
# Test command endpoint
curl -X POST http://localhost:8000/slack/commands \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "command=/o3&text=ping&user_id=U123456"

# Test health endpoint  
curl http://localhost:8000/slack/health
```

### Integration Testing

Full end-to-end test:

```bash
# 1. Submit ticket via Slack
curl -X POST http://localhost:8000/slack/commands \
  -d "command=/ticket&text=add title='Test' wave=B owner=Dev effort=1h&user_id=U123456"

# 2. Check correlation ID in response headers
# 3. Verify ticket created in ledger
# 4. Monitor Builder PR creation
# 5. Check deployment success notification
```

## Monitoring

### Key Metrics

- Command response time (target: <3s)
- Queue depth (alert if >10)
- Error rate (alert if >5%)
- Correlation ID coverage (target: 100%)

### Dashboards

Available in Grafana:
- Slack Integration Overview
- Command Performance 
- Error Analysis
- Correlation Tracking

### Alerts

Configured in Prometheus:
- Slack endpoint down
- High error rate
- Queue backlog
- Missing correlation IDs

## Troubleshooting

### Common Issues

**Problem**: Commands timeout
**Solution**: Check Council API health, verify Redis connection

**Problem**: HMAC verification fails
**Solution**: Verify SLACK_SIGNING_SECRET matches Slack app settings

**Problem**: Missing correlation IDs
**Solution**: Ensure CorrelationIdMiddleware is properly configured

**Problem**: Notifications not posting
**Solution**: Check webhook URLs and SLACK_BOT_TOKEN permissions

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("router.slack").setLevel(logging.DEBUG)
logging.getLogger("middleware.corr_id").setLevel(logging.DEBUG)
```

### Health Checks

Verify all components:

```bash
# Slack integration
curl http://localhost:8000/slack/health

# Council API
curl http://localhost:8000/council/health

# Builder status
curl http://localhost:8000/builder/status  

# Guardian status
curl http://localhost:8000/guardian/health
```

## Future Enhancements

### Phase 2 Features

- Interactive ticket creation modals
- SSO mapping (Slack user → Ledger owner)
- Rich message formatting with blocks
- Threaded conversation tracking
- Direct message support

### Phase 3 Features

- Voice command integration
- AI-powered help suggestions
- Workflow automation triggers
- Advanced analytics dashboard 