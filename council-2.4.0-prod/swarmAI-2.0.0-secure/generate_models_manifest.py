# -*- coding: utf-8 -*-
import re
import pathlib
import yaml
import textwrap

root = pathlib.Path('.').resolve()
cfg = root / 'config'
cfg.mkdir(exist_ok=True)

orc = (root / 'cross_agent_consensus_orchestrator.py').read_text('utf-8')
models = sorted(set(re.findall(r'"model":\s*"([^"]+)"', orc)))
entries = []

for name in models:
    short = name.replace(':', '-')
    entries.append(dict(
        name=short,
        path=f"/models/{short}.gguf",
        dtype="q4_K",
        device="cuda:0"
    ))

yaml.safe_dump({'models': entries}, (cfg/'models.yaml').open('w'))
print("\n✨  Wrote", cfg/'models.yaml') 