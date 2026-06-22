from dataclasses import dataclass

import yaml

MODES = ("guarded", "unattended", "approval")


@dataclass
class Settings:
    mode: str = "guarded"
    battery_threshold: float = 3.5
    cooldown_s: float = 30.0
    max_interventions: int = 10
    model: str = "qwen2.5-coder"
    fqbn: str = "Seeeduino:nrf52:xiaonRF52840Sense"
    port: str = ""
    sketch_dir: str = "firmware/amh_node"
    config_h_path: str = "firmware/amh_node/config.h"
    kill_switch: str = ".amh_kill"
    dry_run: bool = False


def load_settings(path: str) -> Settings:
    with open(path) as fh:
        data = yaml.safe_load(fh) or {}
    settings = Settings(**data)
    if settings.mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    return settings
