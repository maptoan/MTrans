
from pathlib import Path

import yaml

config_path = Path(__file__).resolve().parent / "config" / "config.yaml"
with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

perf = config.get("performance", {})
print(f"DEBUG: Performance key exists: {'performance' in config}")
print(f"DEBUG: max_parallel_workers: {perf.get('max_parallel_workers')}")
print(f"DEBUG: max_requests_per_minute: {perf.get('max_requests_per_minute')}")
print(f"DEBUG: min_delay_between_requests: {perf.get('min_delay_between_requests')}")
