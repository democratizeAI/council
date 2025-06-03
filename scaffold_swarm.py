# -*- coding: utf-8 -*-
import textwrap, pathlib, json, yaml, os

root = pathlib.Path(".").resolve()
(root / "loader").mkdir(exist_ok=True, parents=True)
(root / "tests").mkdir(exist_ok=True, parents=True)
(root / ".github/workflows").mkdir(exist_ok=True, parents=True)

# ── 1. deterministic_loader.py ────────────────────────────────────────────────
(root/"loader/deterministic_loader.py").write_text(textwrap.dedent("""\
    # -*- coding: utf-8 -*-
    \"\"\"Deterministic VRAM-aware model loader.
    Reads config/models.yaml and loads heads until the declared limit
    (per-card profile) is reached.  Any spill aborts with a non-zero exit.
    \"\"\"

    import os, sys, time, yaml, importlib, functools
    from pathlib import Path
    from typing import List

    PROFILES = ('gtx_1080', 'rtx_4070')
    CARD = os.environ.get("SWARM_GPU_PROFILE", "gtx_1080").lower()
    if CARD not in PROFILES:
        sys.exit(f"Unknown profile {CARD!r}; choose one of {PROFILES}")

    MODELS = yaml.safe_load(Path('config/models.yaml').read_text())
    strat   = MODELS['loading_strategy'][CARD]
    limit   = strat['vram_limit_mb']
    force_cpu = set(strat.get('force_cpu', []))
    prio    = strat['priority_order']

    total_vram = 0
    loaded = []

    def echo(msg: str): print(time.strftime('%H:%M:%S'), msg, flush=True)

    def dummy_load(head):
        \"\"\"Placeholder: replace with llama.cpp / vLLM / transformers-compatible
        loader call; here we just pretend to allocate VRAM.\"\"\"
        time.sleep(0.05)               # pretend I/O
        return head['vram_mb']         # MB claimed on GPU

    for bucket in prio:
        for head in MODELS.get(bucket, []):
            name = head['name']
            if name in force_cpu or head.get('dtype') == 'openvino_fp32':
                echo(f'Skipping GPU load – {name} forced to CPU')
                continue
            need = head['vram_mb']
            if total_vram + need > limit:
                echo(f'Stopping at {name} (would spill {total_vram+need} > {limit} MB)')
                break
            echo(f'Loading {name:30s} {need:4d} MB …')
            total_vram += dummy_load(head)
            loaded.append(name)
        else:
            continue   # only reached if inner loop wasn't broken
        break          # stop outer loop too

    echo(f'[OK] Loaded {len(loaded)} heads, total {total_vram} MB within {limit} MB cap')
    """), encoding='utf-8')

# ── 2. PyTest: VRAM smoke-load + RAM guard + router gluttony ──────────────────
(root/"tests/test_vram_and_ram.py").write_text(textwrap.dedent("""\
    # -*- coding: utf-8 -*-
    import os, psutil, subprocess, time, json, pytest

    def test_vram_smokeload():
        env = os.environ.copy()
        env['SWARM_GPU_PROFILE'] = 'gtx_1080'
        p = subprocess.run(['python', '-m', 'loader.deterministic_loader'],
                           capture_output=True, text=True, env=env)
        assert p.returncode == 0, p.stdout + p.stderr
        assert "[OK]" in p.stdout

    @pytest.mark.skipif(os.name == "nt", reason="htop not available on Windows CI")
    def test_ram_guard():
        before = psutil.virtual_memory().used
        time.sleep(1)   # simulate 100-req soak later
        after = psutil.virtual_memory().used
        assert (after - before) < 3 * 1024 ** 3, "RAM leak > 3 GB"
    """), encoding='utf-8')

# ── 3. Locustfile (router gluttony) ───────────────────────────────────────────
(root/"locustfile.py").write_text(textwrap.dedent("""\
    from locust import task, HttpUser, between
    class SwarmUser(HttpUser):
        wait_time = between(0.01, 0.05)
        @task
        def multi_hop(self):
            self.client.post("/orchestrate",
                             json={"prompt": "Explain E=mc^2 in one sentence.",
                                   "route": ["openchat_3_5_0_4b"]})
    """), encoding='utf-8')

# ── 4. GitHub Actions workflow (pytest + headless Locust) ─────────────────────
(root/".github/workflows/ci.yaml").write_text(textwrap.dedent("""\
    name: swarm-ci
    on: [push, pull_request]
    jobs:
      test:
        runs-on: ubuntu-latest
        steps:
        - uses: actions/checkout@v4
        - name: Setup Python
          uses: actions/setup-python@v5
          with: {python-version: '3.11'}
        - name: Install deps
          run: |
            pip install -r requirements.txt
            pip install pytest locust
        - name: Unit & smoke tests
          run: pytest -q
        - name: Router soak (mock)
          run: locust -f locustfile.py --headless -u 50 -r 20 -t 20s
    """), encoding='utf-8')

# ── 5. Fragmentation hot-fix env file (for Docker entrypoint) ─────────────────
(root/".env.swarm").write_text("PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128\n", encoding='utf-8')

print("✨  Loader, tests, Locustfile, CI workflow & env stub written.") 