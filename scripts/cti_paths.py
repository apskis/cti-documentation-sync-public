"""Shared path resolution for CTI Documentation Sync.

Every script and every agent run reads folder locations from cti.config.json in
the repository root. Nothing hard codes a path.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "cti.config.json"


class ConfigError(RuntimeError):
    pass


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise ConfigError(
            f"{CONFIG_PATH} not found. Copy cti.config.example.json to "
            "cti.config.json and set the two folder paths."
        )
    with CONFIG_PATH.open(encoding="utf-8") as fh:
        cfg = json.load(fh)
    for key in ("deliverables", "documentation"):
        if not cfg.get(key):
            raise ConfigError(f"cti.config.json is missing '{key}'.")
    return cfg


def _expand(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value)))


def deliverables_dir(required: bool = True) -> Path:
    p = _expand(load_config()["deliverables"])
    if required and not p.is_dir():
        raise ConfigError(f"Deliverables folder not found: {p}")
    return p


def documentation_dir(required: bool = True) -> Path:
    p = _expand(load_config()["documentation"])
    if required and not p.is_dir():
        raise ConfigError(f"Documentation folder not found: {p}")
    return p


def strategy_dir() -> Path:
    return documentation_dir() / "Strategy_and_Plan"


def doc_sync_dir() -> Path:
    d = documentation_dir() / "_doc_sync"
    d.mkdir(parents=True, exist_ok=True)
    return d


def backups_dir() -> Path:
    d = doc_sync_dir() / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def runs_dir() -> Path:
    d = doc_sync_dir() / "runs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def state_record() -> Path:
    return doc_sync_dir() / "portfolio_state.md"


PROTECTED = ("CTI Strategy.pptx", "CTI Strategy-Reference for April.pptx")


def assert_writable(path: Path) -> None:
    """Refuse to touch the two off limits decks, whatever the caller intends."""
    if Path(path).name in PROTECTED:
        raise ConfigError(
            f"{Path(path).name} is off limits to automation. Read it for "
            "context only."
        )
