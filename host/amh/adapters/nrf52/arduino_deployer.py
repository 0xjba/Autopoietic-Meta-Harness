import os
import re
import subprocess
from pathlib import Path

from amh.core.interfaces import BuildOutcome

FLASH_RE = re.compile(r"Sketch uses (\d+) bytes \((\d+)%\)")
RAM_RE = re.compile(r"Global variables use (\d+) bytes \((\d+)%\)")

# The Seeed core's DFU packaging step runs a Click-based tool that aborts under
# an ASCII locale, so arduino-cli is always invoked with a UTF-8 locale.
_BUILD_ENV = {**os.environ, "LC_ALL": "en_US.UTF-8", "LANG": "en_US.UTF-8"}


def parse_compile_output(text: str) -> dict:
    flash = FLASH_RE.search(text)
    ram = RAM_RE.search(text)
    return {
        "found": flash is not None,
        "flash_bytes": int(flash.group(1)) if flash else 0,
        "flash_pct": int(flash.group(2)) if flash else 0,
        "ram_bytes": int(ram.group(1)) if ram else 0,
    }


class Nrf52ArduinoDeployer:
    def __init__(self, fqbn: str, sketch_dir: str, config_h_path: str, port: str):
        self.fqbn = fqbn
        self.sketch_dir = sketch_dir
        self.config_h_path = config_h_path
        self.port = port

    def build(self, config_text: str) -> BuildOutcome:
        Path(self.config_h_path).write_text(config_text)
        proc = subprocess.run(
            ["arduino-cli", "compile", "--fqbn", self.fqbn, self.sketch_dir],
            capture_output=True, text=True, env=_BUILD_ENV,
        )
        sizes = parse_compile_output(proc.stdout + proc.stderr)
        ok = sizes["found"] and proc.returncode == 0
        detail = f"flash {sizes['flash_pct']}%, ram {sizes['ram_bytes']} bytes"
        return BuildOutcome(ok=ok, detail=detail)

    def deploy(self) -> bool:
        if not self.port:
            print("no port configured; skipping flash")
            return False
        proc = subprocess.run(
            ["arduino-cli", "upload", "--fqbn", self.fqbn, "-p", self.port, self.sketch_dir],
            capture_output=True, text=True, env=_BUILD_ENV,
        )
        return proc.returncode == 0
