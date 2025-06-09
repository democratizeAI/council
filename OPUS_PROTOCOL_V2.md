# 📜 OPUS PROTOCOL V2 — "Slack & o3 Command Sprint"

*(Drop this whole block into the Opus-Architect tab or /opus command.  
Opus will generate / update ledger rows, then the builder-swarm scaffolds the code.)*

## 0 · Context

We now want first-class Slack control:

- `/o3`, `/opus` chat commands
- `/titan save` / `load` config commands  
- Webhook security (Slack signing secret)
- Round-trip tests so Guardian & CI stay green.

## 1 · Tickets to ensure

| Code | Deliverable | KPI / Gate | Effort |
|------|-------------|------------|--------|
| S-01 | Slack command framework (/slack/* FastAPI routes) | slash command returns 200 OK w/in 2 s | 0.5 d |
| S-02 | /o3 command → direct o3 reply | response ≤ 10 s; logged in Live-Logs | 0.25 d |
| S-03 | /opus command → Council (Opus) reply | same KPI as S-02 | 0.25 d |
| S-04 | /titan save \<name\> & /titan load | file in configs/ created/applied | 0.5 d |
| S-05 | Guardian rate-limit (max 3 cmd/min) | alert if exceeded; unit test passes | 0.25 d |

## 2 · Ledger-row schema

```yaml
id: <auto>
wave: "UX / Slack Control"
owner: "Builder"
deliverable: "<as above>"
kpi: "<as above>"
effort: "<as above>"
status: "⬜ queued"
notes: ""
```

## 3 · Opus tasks

1. GET `/ledger/snapshot` and search for deliverables S-01 … S-05.
2. For any missing, POST `/ledger/new_row` (schema above).
3. Respond (YAML) listing each ticket with id, status (created / existing).
4. Emit builder_guidance block:

```yaml
builder_guidance:
  - code: "S-01"
    branch: "builder/S-01-slack-framework"
    env:
      - SLACK_SIGNING_SECRET
      - SLACK_BOT_TOKEN
    tests:
      - "POST /slack/test returns 200"
  - code: "S-02"
    branch: "builder/S-02-o3-slash"
    tests:
      - "`/o3 ping` returns 'pong'"
  - code: "S-03"
    branch: "builder/S-03-opus-slash"
    tests:
      - "`/opus ping` returns 'pong'"
  - code: "S-04"
    branch: "builder/S-04-titan-config"
    tests:
      - "`/titan save test.yaml` creates file"
      - "`/titan load test.yaml` applies config"
  - code: "S-05"
    branch: "builder/S-05-guardian-ratelimit"
    tests:
      - "Rate limit test: >3 commands/min triggers alert"
      - "Guardian metrics updated"
```

## 4 · Builder-swarm expectations

- Each branch scaffolds FastAPI route, unit test, SBOM clean.
- CI runs `sbom.yml` + 25 VU mini-soak.
- On green → auto-merge (label `autonomous`) → canary deploy.

## 5 · Security & secrets

- `SLACK_SIGNING_SECRET` and `SLACK_BOT_TOKEN` must be stored in repo secrets before PR merges.
- Builder tests include HMAC signature verification.

## 6 · Manual pipe-check (after merge)

```bash
# Hit Slack test route
curl -H 'X-Slack-Signature: v0=...' -H 'X-Slack-Request-Timestamp: ...' \
     -d 'command=/o3&text=ping' localhost:9000/slack/o3

# Confirm logs
docker compose logs council-api | tail
```

*Grafana tile "Slack cmd rate" should show events; Guardian alert fires if >3/min for 1 min.*

---

**Paste "OPUS PROTOCOL V2 — Slack & o3 Command Sprint"**  
*Opus will wire ledger rows, the builder swarm will ship the routes, and you'll have full Slack steering in the next green build.* 