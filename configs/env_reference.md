# Environment Variables Reference

## CI/CD Secrets Configuration
| Key                | CI scope | Used by                  |
|--------------------|---------|--------------------------|
| GRAFANA_API_TOKEN  | ✓       | dashboard-import step    |
| DOCKERHUB_PAT      | ✓       | docker-push in deploy.yml|
| SLACK_WEBHOOK_URL  | ✗       | alertmanager webhooks    |

## Core API Configuration
- `API_PORT` - Port for the main API service (default: 9000)
- `REDIS_URL` - Redis connection string for caching
- `DATABASE_URL` - Primary database connection string

## LLM Service Configuration  
- `TINY_SVC_URL` - Endpoint for tiny language model service
- `GEMINI_SVC_URL` - Endpoint for Gemini model service
- `LLM_SVC_URL` - General LLM service endpoint

## Monitoring & Observability
- `PROMETHEUS_URL` - Prometheus metrics endpoint
- `GRAFANA_ADMIN_PASSWORD` - Grafana admin interface password
- `ALERT_WEBHOOK_URL` - Webhook for critical alerts

## Security & Authentication
- `API_KEY_SECRET` - Secret for API key generation
- `JWT_SECRET` - Secret for JWT token signing
- `CORS_ORIGINS` - Allowed CORS origins (comma-separated)

## TITAN.EXE Mission Variables

### Slack Integration
- `SLACK_SIGNING_SECRET` - Secret for verifying Slack webhook signatures
- `SLACK_BOT_TOKEN` - Bot token for Slack API interactions
- `SLACK_APP_TOKEN` - App-level token for Socket Mode connections  
- `SLACK_WEBHOOK_ALERTS` - Webhook URL for alert notifications
- `SLACK_WEBHOOK_PATCHES` - Webhook URL for patch/deployment notifications

### Backend Configuration
- `MEMORY_BACKEND` - Backend for memory/context storage (redis|postgres|memory)
- `ROUTER_BACKEND` - Backend for request routing (nginx|traefik|direct)

### Cost & Budget Monitoring
- `DAILY_BUDGET_USD` - Maximum daily spend in USD (default: 3.33)
- `STRIPE_SECRET_KEY` - Stripe API secret key for billing
- `AWS_COST_EXPLORER_KEY` - AWS API key for cost tracking
- `GCP_BILLING_ACCOUNT` - Google Cloud billing account ID

### Public Endpoint
- `DOMAIN` - Primary domain for public endpoint (e.g., example.com)
- `SSL_EMAIL` - Email for SSL certificate registration
- `CLOUDFLARE_API_TOKEN` - Cloudflare API token for tunnel setup

### Guardian & Automation
- `MANDATE_ACTIVE` - Enable autonomous operations (true|false)
- `MAX_AUTO_MERGES_PER_DAY` - Limit for Guardian auto-merges (default: 3)
- `EMERGENCY_ROLLBACK_ON_FAIL` - Enable automatic rollback (true|false)
- `AUDIT_ENABLED` - Enable nightly self-audit (true|false)

### Development & Testing
- `MINI_SOAK_DURATION` - Duration for mini soak tests (default: 5m)
- `TEST_API_KEY` - API key for automated testing
- `CI_SKIP_EXPENSIVE_TESTS` - Skip resource-intensive tests in CI

## Environment-Specific Overrides

### Production
```bash
MANDATE_ACTIVE=true
EMERGENCY_ROLLBACK_ON_FAIL=true
AUDIT_ENABLED=true
DAILY_BUDGET_USD=3.33
```

### Staging
```bash
MANDATE_ACTIVE=false
EMERGENCY_ROLLBACK_ON_FAIL=false  
AUDIT_ENABLED=false
DAILY_BUDGET_USD=1.00
```

### Development
```bash
MANDATE_ACTIVE=false
MEMORY_BACKEND=memory
ROUTER_BACKEND=direct
MINI_SOAK_DURATION=1m
```

## Required vs Optional

### Required for Basic Operation
- `API_PORT`
- `REDIS_URL`
- `TINY_SVC_URL`
- `GEMINI_SVC_URL`

### Required for TITAN.EXE Mission
- `DOMAIN`
- `DAILY_BUDGET_USD`
- `SLACK_WEBHOOK_ALERTS`
- `MANDATE_ACTIVE`

### Optional (with Defaults)
- `MAX_AUTO_MERGES_PER_DAY` (default: 3)
- `MEMORY_BACKEND` (default: redis)
- `ROUTER_BACKEND` (default: nginx)
- `MINI_SOAK_DURATION` (default: 5m) 