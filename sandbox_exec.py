# sandbox_exec.py – secure Firejail wrapper for Agent‑Zero `exec_safe`
# -------------------------------------------------------------------
# Requires: firejail on host/container; prometheus_client for metrics
# Exposes exec_safe(code:str, lang:str="python") → {stdout, stderr, elapsed_ms}

import os, subprocess, tempfile, time, textwrap
from pathlib import Path
from prometheus_client import Counter, Summary

# ─── Prometheus metrics ─────────────────────────────────────────────
EXEC_LAT   = Summary("swarm_exec_latency_seconds", "Sandbox exec latency")
EXEC_FAILS = Counter("swarm_exec_fail_total", "Sandbox exec failures", ["reason"])

FIREJAIL = os.getenv("FIREJAIL_BIN", "/usr/bin/firejail")
TIMEOUT  = int(os.getenv("EXEC_TIMEOUT_SEC", "5"))  # wall‑clock seconds

# ─── Core helper ────────────────────────────────────────────────────
@EXEC_LAT.time()
def exec_safe(code: str, lang: str = "python") -> dict:
    """Run *code* inside Firejail. Raises RuntimeError on error/timeout."""
    if not Path(FIREJAIL).exists():
        EXEC_FAILS.labels("firejail_missing").inc()
        raise RuntimeError("Firejail not installed on host")

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"snippet.{lang}"
        src.write_text(textwrap.dedent(code))

        cmd = [
            FIREJAIL, "--quiet", "--private", "--net=none",
            "--rlimit-cpu=5", "--rlimit-fsize=20480000",  # 20 MB output cap
            "bash", "-c", f"timeout {TIMEOUT}s python {src}"
        ]
        start = time.perf_counter()
        proc = subprocess.run(cmd, capture_output=True, text=True)
        elapsed = int((time.perf_counter() - start) * 1000)

        if proc.returncode == 124:  # timeout from coreutils `timeout`
            EXEC_FAILS.labels("timeout").inc()
            raise RuntimeError("Sandbox execution timed out")
        if proc.returncode != 0:
            EXEC_FAILS.labels("runtime").inc()
            raise RuntimeError(proc.stderr.strip()[:400] or "non‑zero exit")

        return {"stdout": proc.stdout.strip(), "stderr": proc.stderr.strip(), "elapsed_ms": elapsed}

# ─── Quick manual test ──────────────────────────────────────────────
if __name__ == "__main__":
    print(exec_safe("print(sum(range(10)))")) 