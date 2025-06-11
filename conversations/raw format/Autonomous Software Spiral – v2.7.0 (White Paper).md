# Autonomous Software Spiral – v2.7.0 (White Paper)

## 1 · Executive Summary

The **Autonomous Software Spiral** converts a single‐GPU workstation into a continuously self‑improving, cost‑guarded language‑model platform. Version 2.7.0 adds a nightly LoRA distillation loop, pattern‑mined micro‑specialists, and a full Day‑2 operations surface (alerts, canary, budget caps). The system now delivers \~100 ms p95 latency, < \$0.02 / 100 reqs cost, and learns autonomously every 24 hours while hard‑limiting cloud spend to \$0.10 day.

## 2 · High‑Level Architecture

```
                ┌──────────────────────────────┐
                │   Traefik  (95 % / 5 %)      │
                └────────────┬─┬───────────────┘
                             │ │ weight knob
             ┌───────────────┘ └───────────────┐
             │                                   │
┌────────────▼────────────┐     ┌───────────────▼────────────┐
│  API (Main)   gpu:6 GB  │     │  API (Canary)  gpu:3 GB    │
│  • RouterCascade        │     │  • same image             │
│  • 5 Specialist Heads   │     │  • health‑gated           │
│  • Pattern Miner cache  │     └───────────────┬────────────┘
└────────────┬────────────┘                     │Prom scrape
             │                                   │
┌────────────▼────────────┐  jobs  ┌────────────▼───────────┐
│  Redis (cache & queue)  │<──────►│  Trainer (GPU LoRA)    │
└────────────┬────────────┘        └────────────┬───────────┘
             │ metrics                        LoRA Δ
┌────────────▼────────────┐  push  ┌────────────▼───────────┐
│   Prometheus + PGW      │<──────►│ Alertmanager ➜ Slack/PD│
└────────────┬────────────┘        └────────────────────────┘
             │ dashboards
          ┌──▼──┐
          │Graf.│
          └─────┘
```

### Major components

| Component         | Purpose                                                            | Image                     | Memory / GPU |
| ----------------- | ------------------------------------------------------------------ | ------------------------- | ------------ |
| **API**           | FastAPI + router, exposes `/orchestrate`, `/vote`, `/admin/reload` | `swarm/api:v2.7.0-spiral` | 6 GB GPU     |
| **Pattern‑Miner** | Clusters new prompts → auto‑specialists                            | same image (side‑task)    | CPU‑only     |
| **Redis**         | SHA256 prompt cache + job queue                                    | `redis:7-alpine`          | 512 MiB      |
| **Trainer**       | Nightly QLoRA distillation                                         | `swarm/trainer:v2.7.0`    | 4 GB GPU     |
| **Scheduler**     | APScheduler cron (2 AM LoRA; 6 h pattern)                          | `swarm/cron:v2.7.0`       | 256 MiB      |
| **Observability** | Prom 2.53, Grafana 11, Alertmanager 0.27                           | off‑the‑shelf             | 2 GiB        |
| **Pushgateway**   | Chaos alert drills                                                 | optional                  | 256 MiB      |

## 3 · Model Pipeline

* **Base model**: TinyLlama‑1.1B Q4\_K\_M (GPU‑resident, ≈ 4 GB)
* **Micro‑specialists**: regex + pattern‑mined stubs; run in llama.cpp cpu sub‑graphs (< 20 ms)
* **Nightly LoRA**: QLoRA‑4bit, rank 64, α 32; 40 min budget; cost guard \$0.20
* Hot‑reload via `/admin/reload?lora=latest` (zero downtime)

## 4 · Routing Logic

1. **Cache hit?** instant reply (≤ 40 ms)
2. **Pattern head** if confidence ≥ 0.50  (5 ms)
3. **Full Council** vote (5 heads) – length‑penalty & diversity bonus
4. **CloudRetry**  ⇢ Mistral‑Medium → GPT‑4o‑mini (cap \$0.02) only if local fails

## 5 · Guard‑Rails & Budgets

| Guard             | Threshold   | Action                                |
| ----------------- | ----------- | ------------------------------------- |
| Per‑request cost  | \$0.02      | Raise `BudgetExceeded`, abort call    |
| Daily pool        | \$0.10      | Block cloud & trainer until UTC reset |
| VRAM              |  10.5 GB    | Loader exits if exceeded              |
| p95 latency       |  200 ms     | Alert Critical (> 500 ms Pager)       |
| Cloud retry ratio | 20 % / 10 m | Alert “local drift”                   |

## 6 · CI / CD “Full‑Pipes” Gate

GitHub Actions workflow runs on every PR:

1. build images – cached
2. `make ci-up` (quick\_test profile)
3. `pytest` (incl. cost‑guard tests)
4. 10‑stage gate: loader, micro Titanic, dummy trainer job, alert drill
5. artifacts: Titanic JSON + gate summary Time ≈ 12 min; fails merge if any target red.

## 7 · Performance & Cost Metrics (RTX 4070)

| Metric                  | Value        | Notes                                |
| ----------------------- | ------------ | ------------------------------------ |
| p95 first‑token         | **\~80 ms**  | SSE streaming on                     |
| p95 full                | **\~100 ms** | after pattern cache                  |
| Cost / 100 req          | **\$0.02**   | 92 % local hit‑rate                  |
| GPU util (soak 120 QPS) | 45 – 65 %    | no fragmentation                     |
| Mean nightly spend      | **\$0.04**   | 6 min GPU training + few cloud calls |

## 8 · Security Posture

* Containers run as non‑root; Firejail for exec tool.
* Network isolation (`--net=none`) for trainer; API egress only to cloud endpoints.
* Secrets via env files; no secrets baked into images.

## 9 · Operations Runbooks (links)

| Alert               | Runbook                          |
| ------------------- | -------------------------------- |
| VRAM High           | `docs/runbooks/alert_vram.md`    |
| Latency Pager       | `docs/runbooks/alert_latency.md` |
| Cost Exceeded       | `docs/runbooks/budget.md`        |
| LoRA nightly missed | `docs/runbooks/lora_missed.md`   |

## 10 · Roadmap (Q3 2025)

1. **MiniLM intent classifier** – retire regex cascade.
2. **UI Suite** – React SPA chat + live metrics panel.
3. **Windows sandbox** – gVisor/WSL for cross‑platform exec.
4. **Mixtral‑8×7B Q4\_K** – second GPU node via traffic‑shaper.

## 11 · Appendix – Key Commands

```bash
make up                   # full prod stack
make gate                 # 10‑stage release gate
make evolution-once       # enqueue dummy LoRA job
make set-canary-weight PERCENT=25
make test-alerts-e2e      # VRAM chaos drill
```
