import json
from pathlib import Path

_CONFIG = None
_CONFIG_PATH = None


def load_config(path: Path):
    global _CONFIG
    global _CONFIG_PATH
    _CONFIG_PATH = path
    _CONFIG = json.loads(path.read_text(encoding="utf-8-sig"))
    return _CONFIG


def get_config():
    if _CONFIG is None:
        raise RuntimeError("Config not loaded")
    return _CONFIG


def save_config():
    if _CONFIG is None or _CONFIG_PATH is None:
        raise RuntimeError("Config not loaded")
    _CONFIG_PATH.write_text(json.dumps(_CONFIG, indent=4, ensure_ascii=False), encoding="utf-8")

