from __future__ import annotations
from pathlib import Path
import yaml
from .defaults import default_run_config, merge_dicts
from .schema import RunConfig, run_config_from_dict
from haxs.io.hashes import hash_dict

def load_config(path: str | Path | None = None, overrides: dict | None = None) -> RunConfig:
    base = default_run_config()
    if path is not None:
        with Path(path).open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        base = merge_dicts(base, loaded)
    if overrides:
        base = merge_dicts(base, overrides)
    return run_config_from_dict(base)

def config_hash(config: RunConfig | dict) -> str:
    data = config.raw if isinstance(config, RunConfig) and config.raw else (config if isinstance(config, dict) else config.__dict__)
    return hash_dict(data)
