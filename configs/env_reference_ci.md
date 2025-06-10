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