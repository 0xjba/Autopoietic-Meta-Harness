# Autopoietic Meta-Harnessing for Cyber-Physical Edge Nodes — Design

Applicant: Jobin Babu Ayathil

## 1. Scope

This document specifies the proof-of-work implementation: a closed control loop in
which a local generative model observes BLE telemetry from a constrained edge node,
reasons about a power–accuracy trade-off, rewrites the node's tuning parameters, and
redeploys firmware over tethered serial DFU. The implementation target is a two-week
build with no objectives beyond the loop described here.

The physical application is a continuous Attitude and Heading Reference System (AHRS):
a 6-axis IMU tracked through a complementary filter on a Seeed XIAO nRF52840 Sense.

## 2. Architecture

Three asynchronous layers.

```
Layer A  Firmware (XIAO nRF52840 Sense, C++ / Arduino)
         LSM6DS3 -> complementary filter -> orientation
         drift_variance + battery -> BLE GATT notify @ 1 Hz
Layer B  Host telemetry mesh (Python 3.13, Bleak)
         BLE client + logger -> constraint monitor -> control loop + mode policy
Layer C  Meta-harness (Ollama, local)
         Actor -> Critic -> Validator -> Flasher
```

### 2.1 Layer A — firmware

- IMU: onboard LSM6DS3TR-C over I2C, read via the Seeed LSM6DS3 library.
- Orientation: complementary filter fusing gyroscope integration with the
  accelerometer gravity vector, producing pitch and roll.
- `drift_variance`: the running variance, over a fixed window, of the residual
  `gyro_integrated_angle - accel_derived_angle`. This residual is the quantity the
  complementary filter blends; its variance is an on-device proxy for orientation
  error requiring no external ground-truth reference.
- Battery: a compile-time selection.
  - `AMH_VIRTUAL_BATTERY` (default): charge is modelled as a function of MCU active
    duty cycle, so a longer polling interval measurably slows depletion. This makes
    the control loop's effect observable within minutes and reproducible across runs.
    The model is documented as such and is not presented as a hardware measurement.
  - When disabled: the real VBAT rail is sampled through the ADC (P0.31), with the
    read path enabled via P0.14. This path supports a final hardware validation
    (Section 9, step 5) on a small-capacity cell, confirming that the qualitative
    relationship between polling interval and depletion observed under the model also
    holds on real hardware. This validation is the lowest build priority; the IMU
    orientation and control-loop work take precedence.
- All tuning parameters are isolated in `config.h`, which is the sole mutable artifact
  the meta-harness rewrites.
- Telemetry transport: a custom GATT service with a single notify characteristic
  emitting `drift_variance` and `battery` once per second.

### 2.2 Layer B — host telemetry mesh

- BLE client (Bleak) subscribes to the notify characteristic and logs each sample.
- The constraint monitor compares `battery` against a configured threshold. A
  violation, subject to a cooldown, triggers one intervention cycle.
- The control loop sequences Layer C and enforces the active execution mode.

### 2.3 Layer C — meta-harness

- Actor: a local model served by Ollama. Input is the recent telemetry window, the
  current parameter values, the declared bounds, and the control objective. Output is
  constrained by an Ollama structured-output schema at temperature 0 to
  `{ parameters, rationale }`, where `parameters` are numeric and `rationale` is a
  short per-decision justification logged for analysis.
- Critic: a second, independent model pass that reviews the Actor's proposal against
  the objective and telemetry and returns accept or reject with a reason.
- Validator: bounds-checks every proposed value, renders `config.h` from a fixed
  template, then runs `arduino-cli compile` as a memory-safety gate, confirming
  success and that flash and RAM usage remain within device limits.
- Flasher: on acceptance, writes the firmware via `arduino-cli upload`, which drives
  the core's bundled `adafruit-nrfutil` to reset the node into the Adafruit bootloader
  and perform serial DFU.

## 3. Control objective

A single trade-off is optimised: power against orientation accuracy. Raising
`IMU_POLL_RATE_MS` lengthens deep-sleep intervals and reduces active time, lowering
power draw at the cost of increased drift. Under a battery constraint the Actor is
expected to raise the polling interval, trading accuracy for endurance. No further
objectives are in scope.

## 4. Parameter single source of truth

A single declaration (`host/amh/parameters.py`) defines each tunable parameter: name,
type, inclusive bounds, default, and its slot in the C++ template. This declaration
drives, without duplication:

- the Actor's structured-output JSON schema,
- the Critic's review context,
- the Validator's bounds check,
- the renderer that produces `config.h`.

A single source prevents the model from proposing unsupported keys or out-of-range
values. The initial parameter set is `IMU_POLL_RATE_MS`, `FILTER_ALPHA`, and
`BLE_TX_POWER`.

## 5. Configuration rendering

The model never emits C++. It emits validated numeric values; the host renders
`config.h` by substituting those values into a fixed, pre-tested template
(`host/templates/config.h.j2`). Rendered output is therefore always syntactically
valid and within bounds, and identical inputs always produce an identical file.

## 6. Execution modes and safety

Selected in host configuration:

- `guarded` (default): flash only if the Critic accepts and the Validator passes.
- `unattended`: skip the Critic; flash on Validator pass.
- `approval`: require human confirmation before flashing.

Independent of mode: a `--dry-run` switch performs the full cycle except the flash, and
a kill-switch file halts interventions. A cooldown and a per-session intervention cap
bound the loop's activity.

## 7. Toolchain

- Host: Python 3.13 virtual environment; Bleak 3.0.2. The host avoids the PyPI
  `adafruit-nrfutil` package (last released 2021); flashing uses the binary bundled
  with the board core.
- Embedded: `arduino-cli` with the non-mbed core `Seeeduino:nrf52` and FQBN
  `Seeeduino:nrf52:xiaonRF52840Sense` (board index
  `package_seeeduino_boards_index.json`). Libraries: Seeed LSM6DS3, Adafruit Bluefruit.
- Model: Ollama serving `qwen2.5-coder`, with the model name configurable.

## 8. Repository layout

```
firmware/amh_node/   amh_node.ino, config.h, imu.{h,cpp}, ble.{h,cpp}, battery.{h,cpp}
host/amh/            telemetry.py, monitor.py, actor.py, critic.py, render.py,
                     flash.py, parameters.py, settings
host/templates/      config.h.j2
docs/                design.md, architecture.md
scripts/             toolchain and model setup, run entry point
```

## 9. Build order

1. Firmware: complementary filter, `drift_variance`, virtual battery, BLE service;
   all tunables isolated in `config.h`.
2. Host mesh: Bleak client, 1 Hz logger, threshold monitor.
3. Meta-harness: Actor and Critic over Ollama with structured outputs, the parameter
   source of truth, and the renderer.
4. Pipeline: `arduino-cli` compile gate and serial-DFU flash, the mode policy, and the
   complete closed loop.
5. Hardware battery validation (lowest priority, time permitting): repeat the loop on a
   small-capacity cell with `AMH_VIRTUAL_BATTERY` disabled, and report whether the
   modelled polling-interval-to-depletion relationship reproduces on real hardware.
