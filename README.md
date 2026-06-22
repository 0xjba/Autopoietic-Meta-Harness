# Autopoietic Meta-Harnessing for Cyber-Physical Edge Nodes

A proof-of-work implementation of a closed control loop in which a local generative model
observes telemetry from a constrained edge node, reasons about a power–accuracy trade-off,
rewrites the node's tuning parameters, and redeploys firmware over tethered serial DFU
within a safety envelope.

The physical application is a continuous Attitude and Heading Reference System: a 6-axis
IMU on a Seeed XIAO nRF52840 Sense, fused through a complementary filter. The design is
specified in [docs/design.md](docs/design.md); the build sequence in
[docs/implementation-plan.md](docs/implementation-plan.md).

## Architecture

```
Layer A  Firmware (XIAO nRF52840 Sense, C++)
         LSM6DS3 -> complementary filter -> orientation
         drift_variance + battery -> BLE GATT notify @ 1 Hz
Layer B  Host telemetry mesh (Python, Bleak)
         BLE client + logger -> constraint monitor -> control loop + mode policy
Layer C  Meta-harness (Ollama, local)
         Actor -> Critic -> Validator -> Flasher
```

On a battery-constraint violation, the host packages the recent telemetry window and the
current parameters and invokes a local model under Ollama structured outputs. The Actor
proposes new parameter values and a rationale; the Critic independently accepts or rejects;
the Validator bounds-checks the values, renders `config.h` from a fixed template, and runs
`arduino-cli compile` as a memory-safety gate; the Flasher reflashes the node over serial
DFU. The model emits only validated numeric parameters, never C++, so rendered firmware
configuration is always compilable and within declared bounds.

## Layout

```
firmware/amh_node/   firmware sketch and tunable config.h
host/amh/            telemetry, monitor, actor, critic, render, flash, policy, loop
host/templates/      config.h template rendered from the parameter source of truth
docs/                design and implementation plan
scripts/             toolchain, model, and host setup
```

## Setup

Tested on macOS arm64 with Homebrew; requires `arduino-cli`, `ollama`, and `uv`. Exact
versions and platform notes are in [PREREQUISITES.md](PREREQUISITES.md).

```sh
./scripts/bootstrap.sh        # all of the below, then verify (tests + compile)
```

Or run the steps individually:

```sh
./scripts/setup_embedded.sh   # Seeed nRF52 core, LSM6DS3 library, python shim
./scripts/setup_model.sh      # pull the local model (default: qwen2.5-coder)
./scripts/setup_host.sh       # Python 3.13 virtual environment and dependencies
```

Build and flash the firmware:

```sh
arduino-cli compile --fqbn Seeeduino:nrf52:xiaonRF52840Sense firmware/amh_node
arduino-cli upload  --fqbn Seeeduino:nrf52:xiaonRF52840Sense -p <PORT> firmware/amh_node
```

## Running the loop

```sh
cd host
.venv/bin/python -m amh --dry-run    # full cycle without flashing
.venv/bin/python -m amh              # closed loop; set port in amh/config.yaml
```

Execution mode is set in `host/amh/config.yaml`:

- `guarded` — flash only if the Critic accepts and the Validator passes (default).
- `unattended` — skip the Critic; flash on Validator pass.
- `approval` — require human confirmation before flashing.

A `--dry-run` switch performs every step except the flash. Creating the kill-switch file
(`touch .amh_kill`) halts further interventions.

## Tests

```sh
cd host && .venv/bin/python -m pytest
```
