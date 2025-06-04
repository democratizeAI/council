Below is a checkpoint-playbook you can run any time you worry the “Tamagotchi + Council” stack might be stalling, leaking, or silently breaking.
Everything it calls already exists in the repo—you’re just orchestrating it.

1 Sanity-pulse (∼30 s)
Probe	Command	Pass rule
API ping	curl -sf http://localhost:9000/health	200 OK
GPU heartbeat	`nvidia-smi -q	grep "Gpu" -A1`
Memory query	python - <<'PY'\nfrom faiss_memory import FaissMemory as M;print(len(M().query('dummy')))\nPY	Runs in <50 ms

If any of these wobble, stop here and check the container logs.

2 Leak & smoke suite (35-45 min on RTX 4070)
Run the iron-clad suite described in chat gpt log.md:

bash
Copy
Edit
make -f Makefile.leak_tests init_env
make -f Makefile.leak_tests full_leak_suite | tee leak_run.log
You’ll automatically test for:

Over-fitting (hidden eval & diff tests)

Network leaks (tcp-dump / fake DNS)

Metric inflation (latency echo / Prom parity)

Red-team policy breaks and

Stress bursts 100 req/s chat gpt log

Green wall = no smoke, no mirrors. Tag the SHA in leak_run.log so future runs can diff.

3 Growth-loop health (5 min)
Check last night’s cron
Was harvest_failures.py → train_lora.sh → restart executed?

perl
Copy
Edit
docker logs council | grep "LoRA promotion"
Prom counters
Did they tick?

swarm_lora_train_total should +1

swarm_lora_loss_last should be lower than yesterday o3plan

Blind hold-out

go
Copy
Edit
make titanic BLIND=100
Pass rule – accuracy not < 3 pp below previous baseline.

If anything fails, run rollback_lora.sh (already in Phase 3 docs v2.6.0_full).

4 Docker bill-of-materials (quick diff)
Your production compose file should list exactly these stateful pieces:

Service	Purpose	Volume
llm	ExLlama + Mistral core	models/, loras/
council	FastAPI router + skills	memory/
prometheus	metrics DB	prom_data/
grafana	dashboards	graf_data/
trainer (oneshot)	QLoRA jobs	
cron	nightly harvest/train/restart	

If you see extra ad-hoc containers, you’re drifting.

5 Growth-velocity dashboard (Grafana)
Make one row with:

LoRA version – swarm_lora_version (monotonic)

Daily gain – swarm_titanic_accuracy{type="blind"} sparkline

Cost – swarm_cloud_cost_dollars_total

Latency p95 – swarm_vote_latency_seconds_p95

If version stops ticking for >48 h or gain stays flat three nights in a row, the Tamagotchi stalled—time to inspect the failure shard.

6 Quick regression checklist before any release
Gate	Script	Expected
Unit + e2e	pytest -q	100 %
Leak suite	see § 2	0 fail
Titanic 30-prompt	make micro_gauntlet	≥ 80 %
p95 latency	curlbench 200	< 1 s
Prom scrape	curl :9090/-/healthy	healthy
CI green	GitHub badge	✅

All green → cut the tag.

TL;DR
Pulse (30 s) – health & GPU.

Leak suite (45 min) – prove no cheats.

Growth checks (5 min) – LoRA promoted & blind test green.

Compose diff – ensure only the six canonical services run.

Grafana row – watch version, gain, cost, latency.

Release gate – micro-gauntlet + CI before push.

Stick to this cadence and you’ll catch leaks, stagnation, or broken builds long before users feel them—while your Tamagotchi keeps levelling up every night.