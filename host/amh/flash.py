import re
import subprocess
from dataclasses import dataclass

FLASH_RE = re.compile(r"Sketch uses (\d+) bytes \((\d+)%\)")
RAM_RE = re.compile(r"Global variables use (\d+) bytes \((\d+)%\)")


@dataclass
class CompileResult:
    ok: bool
    flash_bytes: int
    flash_pct: int
    ram_bytes: int
    output: str


def parse_compile_output(text: str) -> CompileResult:
    flash = FLASH_RE.search(text)
    ram = RAM_RE.search(text)
    return CompileResult(
        ok=flash is not None,
        flash_bytes=int(flash.group(1)) if flash else 0,
        flash_pct=int(flash.group(2)) if flash else 0,
        ram_bytes=int(ram.group(1)) if ram else 0,
        output=text,
    )


def compile_firmware(sketch_dir: str, fqbn: str) -> CompileResult:
    proc = subprocess.run(
        ["arduino-cli", "compile", "--fqbn", fqbn, sketch_dir],
        capture_output=True, text=True,
    )
    result = parse_compile_output(proc.stdout + proc.stderr)
    result.ok = result.ok and proc.returncode == 0
    return result


def flash_firmware(sketch_dir: str, fqbn: str, port: str) -> bool:
    proc = subprocess.run(
        ["arduino-cli", "upload", "--fqbn", fqbn, "-p", port, sketch_dir],
        capture_output=True, text=True,
    )
    return proc.returncode == 0
