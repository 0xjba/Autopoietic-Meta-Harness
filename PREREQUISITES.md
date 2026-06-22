# Prerequisites and reproducibility

The repository has been built and tested on a single reference platform. The setup scripts
assume macOS with Homebrew. Linux and Windows are not covered.

## Reference platform

| Component | Version |
| --- | --- |
| Operating system | macOS 26.0.1 (arm64) |
| Homebrew | 5.1.8 |
| uv | 0.11.23 |
| Python (uv-managed) | 3.13.14 |
| arduino-cli | 1.5.1 |
| Seeeduino nRF52 core | 1.1.13 |
| Seeed Arduino LSM6DS3 | 2.0.5 |
| Ollama | 0.30.10 |
| Model | `llama3.1` (8B instruct, `latest` build, digest `46e0c10c039e`) |

Python dependencies are pinned in `host/pyproject.toml`: `bleak==3.0.2`, `ollama==0.6.2`,
`jinja2==3.1.6`, `pyyaml==6.0.3`, `pytest==9.1.1`. The board core and library versions are
pinned in `scripts/setup_embedded.sh`.

## Environment requirements handled by the setup

Three platform-specific points are handled automatically; they are recorded here because
they are not obvious:

1. **Python interpreter.** The host uses a uv-managed CPython 3.13, not a Homebrew
   `python@3.13`. The Homebrew bottle links `pyexpat` against an incompatible system
   `libexpat`, which breaks `pip` and any XML or plist path. uv's standalone interpreter
   avoids that linkage.
2. **`python` on PATH.** The Seeed core's UF2/DFU build step invokes a bare `python`, which
   macOS does not provide. `scripts/setup_embedded.sh` creates a symlink to `python3` if
   none exists.
3. **UTF-8 locale.** The core's DFU packaging tool aborts under an ASCII locale. The host
   deployer (`amh.adapters.nrf52.arduino_deployer`) sets `LC_ALL`/`LANG` itself, so the
   control loop is locale-independent; a manual `arduino-cli` invocation needs the locale
   exported.

4. **Bluetooth permission (macOS).** The host reads telemetry over BLE, which requires the
   running application to hold Bluetooth permission. Launched from an interactive terminal
   (Terminal, iTerm), macOS shows a one-time authorization prompt on the first scan; grant
   it and the loop runs. Launched from a non-interactive parent that cannot display the
   prompt, CoreBluetooth aborts the process instead, so run the host from a terminal you
   can authorize, or grant Bluetooth access to the parent application in System Settings →
   Privacy & Security → Bluetooth. Linux has no equivalent gate.

## One-command setup

```sh
./scripts/bootstrap.sh
```

This runs the embedded, model, and host setup in order and verifies the result by running
the host test suite and compiling the firmware.

## Portability boundary

The scripts depend on Homebrew and Homebrew paths (`/opt/homebrew`). Porting to Linux would
require equivalent provisioning of `arduino-cli`, `ollama`, and a Python 3.13 interpreter,
and would not need the `python` shim or the explicit locale on most distributions. The
host package itself (`amh.core`, `amh.adapters`, `amh.usecases`) is platform-independent
Python; only the provisioning scripts are macOS-specific.
