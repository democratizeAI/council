#!/usr/bin/env python3
import os
os.environ["SWARM_CLOUD_ENABLED"] = "false"

from loader.deterministic_loader import get_loaded_models

models = get_loaded_models()
print(f"Loaded models: {len(models)}")
for name, info in models.items():
    print(f"  {name}: {info.get('backend', 'unknown')}") 