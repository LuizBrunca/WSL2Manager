from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

_CONFIG_DIR = Path(os.environ["APPDATA"]) / "WSL2Manager"
_CONFIG_PATH = _CONFIG_DIR / "config.json"


@dataclass
class Config:
    maintained_distros: list[str] | None = None


def load() -> Config:
    if not _CONFIG_PATH.exists():
        return Config()
    data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    return Config(maintained_distros=data.get("maintained_distros"))


def save(config: Config) -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(
        json.dumps({"maintained_distros": config.maintained_distros}, indent=2),
        encoding="utf-8",
    )
