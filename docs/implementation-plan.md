# Implementation Plan

This plan implements the design in `docs/design.md` as a sequence of small, individually
verifiable tasks. Steps use checkbox syntax for tracking. Pure host logic is developed
test-first; firmware and hardware-bound steps are verified by compilation and on-device
observation, since they cannot be unit-tested off the device.

**Goal:** A closed control loop in which a local model observes BLE telemetry from a
XIAO nRF52840 Sense, proposes new tuning parameters under a power–accuracy objective, and
redeploys firmware over serial DFU within a safety envelope.

**Architecture:** Firmware (Layer A) streams `drift_variance` and `battery` over BLE. A
Python host (Layer B) logs the stream and detects constraint violations. A meta-harness
(Layer C) runs an Actor and Critic over Ollama, validates and renders `config.h`, and
flashes the node through `arduino-cli`.

**Tech stack:** Arduino C++ (Seeeduino nRF52 core, Bluefruit, Seeed LSM6DS3); Python 3.13
(Bleak, Ollama client, Jinja2, PyYAML, pytest); `arduino-cli`; Ollama (`qwen2.5-coder`).

**Conventions:** Commit messages are imperative and plain (no tooling prefixes). Each task
ends in a commit. Run host tests from `host/`.

---

## Phase 0: Toolchain and scaffolding

### Task 0.1: Repository skeleton

**Files:**
- Create: `firmware/amh_node/.gitkeep`, `host/amh/__init__.py`, `host/tests/__init__.py`,
  `scripts/.gitkeep`

- [ ] **Step 1: Create directories and placeholders**

```bash
mkdir -p firmware/amh_node host/amh host/templates host/tests scripts
touch firmware/amh_node/.gitkeep host/amh/__init__.py host/tests/__init__.py scripts/.gitkeep
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "Add source tree skeleton"
```

### Task 0.2: Host Python environment

**Files:**
- Create: `host/pyproject.toml`, `scripts/setup_host.sh`

`bleak` requires Python >=3.10 and is unverified on the system's 3.14, so the host is
pinned to 3.13. The Homebrew `python@3.13` bottle on this platform links `pyexpat` against
an incompatible system `libexpat`, which breaks `pip`; a managed CPython 3.13 via `uv`
avoids that linkage and still yields a standard pinned venv.

- [ ] **Step 1: Provision the interpreter and venv with uv**

Run:
```bash
brew install uv
uv venv host/.venv --python 3.13
host/.venv/bin/python --version
```
Expected: `Python 3.13.x`

- [ ] **Step 2: Write `host/pyproject.toml`**

```toml
[project]
name = "amh-host"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "bleak==3.0.2",
    "ollama>=0.4",
    "jinja2>=3.1",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: Install dependencies**

Run:
```bash
uv pip install --python host/.venv/bin/python -e 'host[dev]'
host/.venv/bin/python -c "import bleak, ollama, jinja2, yaml; print('ok')"
```
Expected: `ok`. `scripts/setup_host.sh` captures Steps 1 and 3 for reproducibility.

- [ ] **Step 4: Commit**

```bash
git add host/pyproject.toml scripts/setup_host.sh
git commit -m "Add host Python project and dependencies"
```

### Task 0.3: Embedded toolchain

**Files:**
- Create: `scripts/setup_embedded.sh`

- [ ] **Step 1: Write `scripts/setup_embedded.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

INDEX="https://files.seeedstudio.com/arduino/package_seeeduino_boards_index.json"

arduino-cli config init --overwrite
arduino-cli config add board_manager.additional_urls "$INDEX"
arduino-cli core update-index
arduino-cli core install Seeeduino:nrf52
arduino-cli lib install "Seeed Arduino LSM6DS3"
arduino-cli board listall | grep -i xiao
```

- [ ] **Step 2: Install arduino-cli and run the script**

Run:
```bash
brew install arduino-cli
chmod +x scripts/setup_embedded.sh
./scripts/setup_embedded.sh
```
Expected: the listing includes `Seeed XIAO nRF52840 Sense` with FQBN
`Seeeduino:nrf52:xiaonRF52840Sense`.

- [ ] **Step 3: Commit**

```bash
git add scripts/setup_embedded.sh && git commit -m "Add embedded toolchain setup script"
```

### Task 0.4: Local model

**Files:**
- Create: `scripts/setup_model.sh`

- [ ] **Step 1: Write `scripts/setup_model.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

MODEL="${AMH_MODEL:-qwen2.5-coder}"
ollama pull "$MODEL"
ollama list | grep -i "$MODEL"
```

- [ ] **Step 2: Install Ollama, start it, pull the model**

Run:
```bash
brew install ollama
brew services start ollama
chmod +x scripts/setup_model.sh
./scripts/setup_model.sh
```
Expected: `qwen2.5-coder` appears in `ollama list`.

- [ ] **Step 3: Commit**

```bash
git add scripts/setup_model.sh && git commit -m "Add local model setup script"
```

---

## Phase 1: Firmware

The firmware streams telemetry over BLE. It cannot be unit-tested; each task is verified by
a successful `arduino-cli compile` and, at the end, on-device observation.

### Task 1.1: Default configuration header

**Files:**
- Create: `firmware/amh_node/config.h`

- [ ] **Step 1: Write `firmware/amh_node/config.h`**

```c
#ifndef AMH_CONFIG_H
#define AMH_CONFIG_H

// Generated by the AMH meta-harness from host/amh/parameters.py.
// This checked-in copy holds the default values.
#define IMU_POLL_RATE_MS 20
#define FILTER_ALPHA     0.9600f
#define BLE_TX_POWER     0

#endif // AMH_CONFIG_H
```

- [ ] **Step 2: Commit**

```bash
git add firmware/amh_node/config.h && git commit -m "Add firmware configuration header with defaults"
```

### Task 1.2: IMU and complementary filter

**Files:**
- Create: `firmware/amh_node/imu.h`, `firmware/amh_node/imu.cpp`

- [ ] **Step 1: Write `firmware/amh_node/imu.h`**

```c
#ifndef AMH_IMU_H
#define AMH_IMU_H

struct Orientation {
  float pitch;
  float roll;
};

// Powers and configures the onboard LSM6DS3TR-C. Returns true on success.
bool imu_init();

// Reads one sample and advances both the complementary filter and the
// gyro-only reference integration. dt_s is the elapsed time in seconds.
void imu_update(float dt_s);

Orientation imu_orientation();

// Variance of the (gyro-only minus accelerometer) pitch residual accumulated
// since the previous call. Resets the accumulator.
float imu_drift_variance_reset();

#endif // AMH_IMU_H
```

- [ ] **Step 2: Write `firmware/amh_node/imu.cpp`**

The Sense does not power the IMU in the core's `initVariant()`; `PIN_LSM6DS3TR_C_POWER`
must be driven HIGH before `begin()`. Drift is tracked with Welford's online variance over
the residual between the gyro-only integrated pitch and the accelerometer-derived pitch.

```c
#include <Arduino.h>
#include <Wire.h>
#include <math.h>
#include "LSM6DS3.h"
#include "imu.h"
#include "config.h"

static LSM6DS3 imu(I2C_MODE, 0x6A);

static float pitch = 0.0f, roll = 0.0f;   // complementary filter output
static float gyroPitch = 0.0f;            // gyro-only reference

static unsigned long resCount = 0;        // Welford state over the residual
static float resMean = 0.0f, resM2 = 0.0f;

static const float RAD2DEG = 57.29578f;

bool imu_init() {
  pinMode(PIN_LSM6DS3TR_C_POWER, OUTPUT);
  digitalWrite(PIN_LSM6DS3TR_C_POWER, HIGH);
  delay(20);
  return imu.begin() == 0;
}

void imu_update(float dt_s) {
  float ax = imu.readFloatAccelX();
  float ay = imu.readFloatAccelY();
  float az = imu.readFloatAccelZ();
  float gx = imu.readFloatGyroX();   // deg/s
  float gy = imu.readFloatGyroY();

  float accelPitch = atan2f(-ax, sqrtf(ay * ay + az * az)) * RAD2DEG;
  float accelRoll  = atan2f(ay, az) * RAD2DEG;

  pitch = FILTER_ALPHA * (pitch + gx * dt_s) + (1.0f - FILTER_ALPHA) * accelPitch;
  roll  = FILTER_ALPHA * (roll  + gy * dt_s) + (1.0f - FILTER_ALPHA) * accelRoll;

  gyroPitch += gx * dt_s;
  float residual = gyroPitch - accelPitch;

  resCount += 1;
  float delta = residual - resMean;
  resMean += delta / (float)resCount;
  resM2 += delta * (residual - resMean);
}

Orientation imu_orientation() {
  Orientation o;
  o.pitch = pitch;
  o.roll = roll;
  return o;
}

float imu_drift_variance_reset() {
  float variance = (resCount > 1) ? (resM2 / (float)(resCount - 1)) : 0.0f;
  resCount = 0;
  resMean = 0.0f;
  resM2 = 0.0f;
  gyroPitch = pitch;   // re-anchor the reference to bound unbounded growth
  return variance;
}
```

- [ ] **Step 3: Commit**

```bash
git add firmware/amh_node/imu.h firmware/amh_node/imu.cpp
git commit -m "Add IMU driver, complementary filter, and drift variance"
```

### Task 1.3: Battery model

**Files:**
- Create: `firmware/amh_node/battery.h`, `firmware/amh_node/battery.cpp`

- [ ] **Step 1: Write `firmware/amh_node/battery.h`**

```c
#ifndef AMH_BATTERY_H
#define AMH_BATTERY_H

void battery_init();

// Accounts for one active wake cycle. Under the virtual model this advances
// depletion; on real hardware it is a no-op.
void battery_on_active_cycle();

float battery_voltage();

#endif // AMH_BATTERY_H
```

- [ ] **Step 2: Write `firmware/amh_node/battery.cpp`**

The virtual model depletes per active cycle, so a longer polling interval (fewer cycles
per second) measurably slows depletion. The constant is chosen so the default poll rate
reaches the 3.5 V threshold in a few minutes. The real path is retained for the Section 9
hardware validation; its divider constant is calibrated empirically in that step.

```c
#include <Arduino.h>
#include "battery.h"

#ifndef AMH_VIRTUAL_BATTERY
#define AMH_VIRTUAL_BATTERY 1
#endif

#if AMH_VIRTUAL_BATTERY

static const float V_FULL = 4.20f;
static const float V_FLOOR = 3.00f;
static const float ACTIVE_COST_V = 0.00008f;   // volts lost per wake cycle

static float v = V_FULL;

void battery_init() { v = V_FULL; }

void battery_on_active_cycle() {
  v -= ACTIVE_COST_V;
  if (v < V_FLOOR) v = V_FLOOR;
}

float battery_voltage() { return v; }

#else

void battery_init() {
  pinMode(VBAT_ENABLE, OUTPUT);
  digitalWrite(VBAT_ENABLE, HIGH);   // reading disabled by default
}

void battery_on_active_cycle() {}

float battery_voltage() {
  digitalWrite(VBAT_ENABLE, LOW);    // enable the divider
  delay(1);
  int raw = analogRead(PIN_VBAT);
  digitalWrite(VBAT_ENABLE, HIGH);
  float v_adc = raw * (3.6f / 1023.0f);
  return v_adc * 2.961f;             // divider ratio; calibrate in Section 9
}

#endif
```

- [ ] **Step 3: Commit**

```bash
git add firmware/amh_node/battery.h firmware/amh_node/battery.cpp
git commit -m "Add virtual battery model with real VBAT fallback"
```

### Task 1.4: BLE telemetry service

**Files:**
- Create: `firmware/amh_node/ble.h`, `firmware/amh_node/ble.cpp`

- [ ] **Step 1: Write `firmware/amh_node/ble.h`**

```c
#ifndef AMH_BLE_H
#define AMH_BLE_H

void ble_init(int tx_power);

// Notifies an 8-byte payload: float32 drift_variance, float32 battery (LE).
void ble_notify(float drift_variance, float battery);

bool ble_connected();

#endif // AMH_BLE_H
```

- [ ] **Step 2: Write `firmware/amh_node/ble.cpp`**

UUIDs are fixed so the host can subscribe by name. Bluefruit expects 128-bit UUIDs in
least-significant-byte-first order.

Service `f0000001-1111-2222-3333-444455556666`, characteristic
`f0000002-1111-2222-3333-444455556666`.

```c
#include <bluefruit.h>
#include "ble.h"

static uint8_t SERVICE_UUID[16] = {
  0x66,0x66,0x55,0x55,0x44,0x44,0x33,0x33,
  0x22,0x22,0x11,0x11,0x01,0x00,0x00,0xf0
};
static uint8_t CHAR_UUID[16] = {
  0x66,0x66,0x55,0x55,0x44,0x44,0x33,0x33,
  0x22,0x22,0x11,0x11,0x02,0x00,0x00,0xf0
};

static BLEService amhService(SERVICE_UUID);
static BLECharacteristic amhTelemetry(CHAR_UUID);

void ble_init(int tx_power) {
  Bluefruit.begin();
  Bluefruit.setTxPower(tx_power);
  Bluefruit.setName("AMH-Node");

  amhService.begin();
  amhTelemetry.setProperties(CHR_PROPS_NOTIFY);
  amhTelemetry.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
  amhTelemetry.setFixedLen(8);
  amhTelemetry.begin();

  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addTxPower();
  Bluefruit.Advertising.addService(amhService);
  Bluefruit.Advertising.addName();
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.setInterval(32, 244);
  Bluefruit.Advertising.setFastTimeout(30);
  Bluefruit.Advertising.start(0);
}

void ble_notify(float drift_variance, float battery) {
  if (!Bluefruit.connected()) return;
  float payload[2] = { drift_variance, battery };
  amhTelemetry.notify((uint8_t *)payload, sizeof(payload));
}

bool ble_connected() { return Bluefruit.connected(); }
```

- [ ] **Step 3: Commit**

```bash
git add firmware/amh_node/ble.h firmware/amh_node/ble.cpp
git commit -m "Add BLE telemetry service"
```

### Task 1.5: Main sketch

**Files:**
- Create: `firmware/amh_node/amh_node.ino`

- [ ] **Step 1: Write `firmware/amh_node/amh_node.ino`**

`delay()` on this core yields to the FreeRTOS idle task, which sleeps the CPU. A longer
`IMU_POLL_RATE_MS` therefore reduces active duty cycle, which the virtual battery records.

```c
#include <Arduino.h>
#include "config.h"
#include "imu.h"
#include "battery.h"
#include "ble.h"

static unsigned long lastNotifyMs = 0;

void setup() {
  imu_init();
  battery_init();
  ble_init(BLE_TX_POWER);
}

void loop() {
  const float dt = IMU_POLL_RATE_MS / 1000.0f;

  imu_update(dt);
  battery_on_active_cycle();

  unsigned long now = millis();
  if (now - lastNotifyMs >= 1000) {
    lastNotifyMs = now;
    ble_notify(imu_drift_variance_reset(), battery_voltage());
  }

  delay(IMU_POLL_RATE_MS);
}
```

- [ ] **Step 2: Compile**

Run:
```bash
arduino-cli compile --fqbn Seeeduino:nrf52:xiaonRF52840Sense firmware/amh_node
```
Expected: `Sketch uses ... bytes` with no errors.

- [ ] **Step 3: Flash and observe**

Connect the board, find the port (`arduino-cli board list`), then:
```bash
arduino-cli upload --fqbn Seeeduino:nrf52:xiaonRF52840Sense -p <PORT> firmware/amh_node
```
Using a BLE scanner app, confirm an advertiser named `AMH-Node` exposing service
`f0000001-...`, with the characteristic notifying 8 bytes per second.

- [ ] **Step 4: Commit**

```bash
git add firmware/amh_node/amh_node.ino && git commit -m "Add main firmware sketch"
```

---

## Phase 2: Host telemetry mesh

### Task 2.1: Telemetry sample parsing

**Files:**
- Create: `host/amh/telemetry.py`
- Test: `host/tests/test_telemetry.py`

- [ ] **Step 1: Write the failing test**

```python
import struct
import pytest
from amh.telemetry import Sample, parse_sample


def test_parse_sample_decodes_two_floats():
    raw = struct.pack("<ff", 0.0123, 3.62)
    s = parse_sample(raw)
    assert isinstance(s, Sample)
    assert s.drift_variance == pytest.approx(0.0123, rel=1e-5)
    assert s.battery == pytest.approx(3.62, rel=1e-5)


def test_parse_sample_rejects_wrong_length():
    with pytest.raises(ValueError):
        parse_sample(b"\x00\x00\x00")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `host/.venv/bin/pytest tests/test_telemetry.py -v` (from `host/`)
Expected: FAIL with `ModuleNotFoundError: No module named 'amh.telemetry'`

- [ ] **Step 3: Write `host/amh/telemetry.py`**

```python
import struct
from dataclasses import dataclass

PAYLOAD_FORMAT = "<ff"
PAYLOAD_SIZE = struct.calcsize(PAYLOAD_FORMAT)
TELEMETRY_CHAR_UUID = "f0000002-1111-2222-3333-444455556666"


@dataclass
class Sample:
    drift_variance: float
    battery: float


def parse_sample(raw: bytes) -> Sample:
    if len(raw) != PAYLOAD_SIZE:
        raise ValueError(f"expected {PAYLOAD_SIZE} bytes, got {len(raw)}")
    drift, battery = struct.unpack(PAYLOAD_FORMAT, raw)
    return Sample(drift_variance=drift, battery=battery)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `host/.venv/bin/pytest tests/test_telemetry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add host/amh/telemetry.py host/tests/test_telemetry.py
git commit -m "Add telemetry payload parsing"
```

### Task 2.2: Constraint monitor decision

**Files:**
- Create: `host/amh/monitor.py`
- Test: `host/tests/test_monitor.py`

- [ ] **Step 1: Write the failing test**

```python
from amh.monitor import should_intervene


def test_triggers_below_threshold_after_cooldown():
    assert should_intervene(3.40, 3.50, seconds_since_last=120, cooldown_s=60) is True


def test_no_trigger_above_threshold():
    assert should_intervene(3.80, 3.50, seconds_since_last=120, cooldown_s=60) is False


def test_no_trigger_within_cooldown():
    assert should_intervene(3.40, 3.50, seconds_since_last=10, cooldown_s=60) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `host/.venv/bin/pytest tests/test_monitor.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `host/amh/monitor.py`**

```python
def should_intervene(
    battery: float,
    threshold: float,
    seconds_since_last: float,
    cooldown_s: float,
) -> bool:
    return battery < threshold and seconds_since_last >= cooldown_s
```

- [ ] **Step 4: Run test to verify it passes**

Run: `host/.venv/bin/pytest tests/test_monitor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add host/amh/monitor.py host/tests/test_monitor.py
git commit -m "Add constraint monitor decision"
```

### Task 2.3: BLE client and logger

**Files:**
- Create: `host/amh/telemetry_client.py`

This task uses live BLE; verification is on-device, not unit tests.

- [ ] **Step 1: Write `host/amh/telemetry_client.py`**

```python
import asyncio
from typing import Awaitable, Callable

from bleak import BleakClient, BleakScanner

from amh.telemetry import TELEMETRY_CHAR_UUID, Sample, parse_sample

DEVICE_NAME = "AMH-Node"


async def find_device(name: str = DEVICE_NAME, timeout: float = 15.0):
    return await BleakScanner.find_device_by_name(name, timeout=timeout)


async def stream(on_sample: Callable[[Sample], Awaitable[None]], name: str = DEVICE_NAME):
    device = await find_device(name)
    if device is None:
        raise RuntimeError(f"device {name!r} not found")

    async with BleakClient(device) as client:
        async def handler(_char, data: bytearray):
            await on_sample(parse_sample(bytes(data)))

        await client.start_notify(TELEMETRY_CHAR_UUID, handler)
        while client.is_connected:
            await asyncio.sleep(1.0)
```

- [ ] **Step 2: Verify against the device**

With the firmware running, add a temporary entry point and confirm samples print once per
second:
```bash
host/.venv/bin/python -c "
import asyncio
from amh.telemetry_client import stream
async def show(s): print(s)
asyncio.run(stream(show))
"
```
Expected: one `Sample(...)` line per second with a plausible `battery` near 4.2 decreasing.

- [ ] **Step 3: Commit**

```bash
git add host/amh/telemetry_client.py
git commit -m "Add BLE telemetry client"
```

---

## Phase 3: Meta-harness

### Task 3.1: Parameter single source of truth

**Files:**
- Create: `host/amh/parameters.py`
- Test: `host/tests/test_parameters.py`

- [ ] **Step 1: Write the failing test**

```python
from amh.parameters import PARAMETERS, defaults, validate, json_schema


def test_defaults_are_within_bounds():
    assert validate(defaults()) == []


def test_validate_rejects_out_of_range():
    bad = defaults()
    bad["IMU_POLL_RATE_MS"] = 5
    errors = validate(bad)
    assert any("IMU_POLL_RATE_MS" in e for e in errors)


def test_validate_rejects_unknown_key():
    bad = defaults()
    bad["GAIN"] = 1
    errors = validate(bad)
    assert any("GAIN" in e for e in errors)


def test_validate_rejects_disallowed_discrete_value():
    bad = defaults()
    bad["BLE_TX_POWER"] = 1   # not an allowed Bluefruit level
    assert any("BLE_TX_POWER" in e for e in validate(bad))


def test_schema_lists_all_parameters():
    schema = json_schema()
    props = schema["properties"]["parameters"]["properties"]
    assert set(props) == {p.name for p in PARAMETERS}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `host/.venv/bin/pytest tests/test_parameters.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `host/amh/parameters.py`**

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Parameter:
    name: str
    ctype: str          # "int" or "float"
    minimum: float
    maximum: float
    default: float
    description: str
    allowed: tuple = field(default_factory=tuple)   # discrete set, if constrained


PARAMETERS = [
    Parameter("IMU_POLL_RATE_MS", "int", 10, 200, 20,
              "IMU sampling interval in milliseconds; higher reduces active duty"),
    Parameter("FILTER_ALPHA", "float", 0.80, 0.99, 0.96,
              "Complementary filter gyroscope weight"),
    Parameter("BLE_TX_POWER", "int", -40, 8, 0,
              "BLE transmit power in dBm",
              allowed=(-40, -20, -16, -12, -8, -4, 0, 2, 3, 4, 5, 6, 7, 8)),
]

PARAMETERS_BY_NAME = {p.name: p for p in PARAMETERS}


def defaults() -> dict:
    return {p.name: p.default for p in PARAMETERS}


def validate(values: dict) -> list[str]:
    errors: list[str] = []
    for key in values:
        if key not in PARAMETERS_BY_NAME:
            errors.append(f"unknown parameter {key}")
    for p in PARAMETERS:
        if p.name not in values:
            errors.append(f"{p.name} missing")
            continue
        v = values[p.name]
        if not isinstance(v, (int, float)):
            errors.append(f"{p.name} not numeric")
            continue
        if p.ctype == "int" and float(v) != int(v):
            errors.append(f"{p.name} must be integral")
            continue
        if p.allowed:
            if v not in p.allowed:
                errors.append(f"{p.name} {v} not in allowed set")
        elif not (p.minimum <= v <= p.maximum):
            errors.append(f"{p.name} {v} out of range [{p.minimum}, {p.maximum}]")
    return errors


def json_schema() -> dict:
    props = {}
    for p in PARAMETERS:
        node: dict = {"type": "integer" if p.ctype == "int" else "number"}
        if p.allowed:
            node["enum"] = list(p.allowed)
        else:
            node["minimum"] = p.minimum
            node["maximum"] = p.maximum
        props[p.name] = node
    return {
        "type": "object",
        "properties": {
            "parameters": {
                "type": "object",
                "properties": props,
                "required": [p.name for p in PARAMETERS],
                "additionalProperties": False,
            },
            "rationale": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "parameter": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["parameter", "reason"],
                },
            },
        },
        "required": ["parameters", "rationale"],
        "additionalProperties": False,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `host/.venv/bin/pytest tests/test_parameters.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add host/amh/parameters.py host/tests/test_parameters.py
git commit -m "Add parameter single source of truth"
```

### Task 3.2: Configuration rendering

**Files:**
- Create: `host/amh/render.py`, `host/templates/config.h.j2`
- Test: `host/tests/test_render.py`

- [ ] **Step 1: Write the failing test**

```python
from amh.render import render_config


def test_render_formats_by_type():
    out = render_config({"IMU_POLL_RATE_MS": 40, "FILTER_ALPHA": 0.96, "BLE_TX_POWER": 0})
    assert "#define IMU_POLL_RATE_MS 40" in out
    assert "#define FILTER_ALPHA     0.9600f" in out
    assert "#define BLE_TX_POWER     0" in out
    assert out.startswith("#ifndef AMH_CONFIG_H") or "AMH_CONFIG_H" in out


def test_render_is_deterministic():
    v = {"IMU_POLL_RATE_MS": 40, "FILTER_ALPHA": 0.96, "BLE_TX_POWER": 0}
    assert render_config(v) == render_config(v)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `host/.venv/bin/pytest tests/test_render.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `host/templates/config.h.j2`**

```jinja
#ifndef AMH_CONFIG_H
#define AMH_CONFIG_H

// Generated by the AMH meta-harness from host/amh/parameters.py.
// This checked-in copy holds the default values.
{{ body }}

#endif // AMH_CONFIG_H
```

- [ ] **Step 4: Write `host/amh/render.py`**

```python
from pathlib import Path

from jinja2 import Template

from amh.parameters import PARAMETERS

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "config.h.j2"


def _format_value(ctype: str, value) -> str:
    if ctype == "int":
        return str(int(value))
    return f"{float(value):.4f}f"


def render_config(values: dict) -> str:
    width = max(len(p.name) for p in PARAMETERS)
    lines = [
        f"#define {p.name.ljust(width)} {_format_value(p.ctype, values[p.name])}"
        for p in PARAMETERS
    ]
    template = Template(TEMPLATE_PATH.read_text())
    return template.render(body="\n".join(lines))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `host/.venv/bin/pytest tests/test_render.py -v`
Expected: PASS. If the alignment in the assertion differs, adjust the expected spacing to
match `name.ljust(width)` for the defined parameter set.

- [ ] **Step 6: Commit**

```bash
git add host/amh/render.py host/templates/config.h.j2 host/tests/test_render.py
git commit -m "Add configuration rendering from parameter source"
```

### Task 3.3: Actor and Critic response parsing

**Files:**
- Create: `host/amh/actor.py`, `host/amh/critic.py`
- Test: `host/tests/test_actor.py`, `host/tests/test_critic.py`

- [ ] **Step 1: Write the failing tests**

`host/tests/test_actor.py`:
```python
import pytest
from amh.actor import Proposal, parse_actor_response


def test_parse_actor_response_extracts_parameters_and_rationale():
    data = {
        "parameters": {"IMU_POLL_RATE_MS": 60, "FILTER_ALPHA": 0.9, "BLE_TX_POWER": -4},
        "rationale": [{"parameter": "IMU_POLL_RATE_MS", "reason": "extend deep sleep"}],
    }
    p = parse_actor_response(data)
    assert isinstance(p, Proposal)
    assert p.parameters["IMU_POLL_RATE_MS"] == 60
    assert p.rationale[0]["parameter"] == "IMU_POLL_RATE_MS"


def test_parse_actor_response_rejects_missing_parameters():
    with pytest.raises(ValueError):
        parse_actor_response({"rationale": []})
```

`host/tests/test_critic.py`:
```python
import pytest
from amh.critic import Verdict, parse_critic_response


def test_parse_critic_response_accept():
    v = parse_critic_response({"accept": True, "reason": "within envelope"})
    assert isinstance(v, Verdict)
    assert v.accept is True
    assert v.reason == "within envelope"


def test_parse_critic_response_rejects_malformed():
    with pytest.raises(ValueError):
        parse_critic_response({"reason": "no verdict"})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `host/.venv/bin/pytest tests/test_actor.py tests/test_critic.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `host/amh/actor.py`**

```python
import json
from dataclasses import dataclass

import ollama

from amh.parameters import PARAMETERS, json_schema

SYSTEM_PROMPT = (
    "You tune firmware for a battery-constrained inertial sensor node. "
    "Raising IMU_POLL_RATE_MS lengthens deep-sleep intervals and lowers power "
    "draw at the cost of orientation accuracy. When the battery is below its "
    "threshold, reduce power draw while keeping accuracy as high as the budget "
    "allows. Respond only with the requested JSON."
)


@dataclass
class Proposal:
    parameters: dict
    rationale: list


def parse_actor_response(data: dict) -> Proposal:
    if "parameters" not in data:
        raise ValueError("actor response missing 'parameters'")
    return Proposal(parameters=data["parameters"], rationale=data.get("rationale", []))


def _bounds_table() -> str:
    rows = []
    for p in PARAMETERS:
        domain = f"one of {list(p.allowed)}" if p.allowed else f"[{p.minimum}, {p.maximum}]"
        rows.append(f"- {p.name} ({p.ctype}): {domain}; {p.description}")
    return "\n".join(rows)


def build_user_prompt(window: list, current: dict, threshold: float) -> str:
    return (
        f"Battery threshold: {threshold} V.\n"
        f"Current parameters: {json.dumps(current)}.\n"
        f"Tunable parameters and domains:\n{_bounds_table()}\n"
        f"Recent telemetry (oldest first): {json.dumps(window)}.\n"
        "Propose new parameter values and a rationale per changed parameter."
    )


def propose(client: ollama.Client, model: str, window: list, current: dict,
            threshold: float) -> Proposal:
    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(window, current, threshold)},
        ],
        format=json_schema(),
        options={"temperature": 0},
    )
    return parse_actor_response(json.loads(response["message"]["content"]))
```

- [ ] **Step 4: Write `host/amh/critic.py`**

```python
import json
from dataclasses import dataclass

import ollama

CRITIC_SCHEMA = {
    "type": "object",
    "properties": {
        "accept": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["accept", "reason"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = (
    "You review a proposed firmware tuning change for a battery-constrained "
    "inertial node. Accept only if the change plausibly reduces power draw under "
    "a low battery while not needlessly destroying orientation accuracy. "
    "Respond only with the requested JSON."
)


@dataclass
class Verdict:
    accept: bool
    reason: str


def parse_critic_response(data: dict) -> Verdict:
    if "accept" not in data or "reason" not in data:
        raise ValueError("critic response missing 'accept' or 'reason'")
    return Verdict(accept=bool(data["accept"]), reason=str(data["reason"]))


def build_user_prompt(current: dict, proposed: dict, rationale: list,
                      threshold: float) -> str:
    return (
        f"Battery threshold: {threshold} V.\n"
        f"Current parameters: {json.dumps(current)}.\n"
        f"Proposed parameters: {json.dumps(proposed)}.\n"
        f"Actor rationale: {json.dumps(rationale)}.\n"
        "Accept or reject this change."
    )


def review(client: ollama.Client, model: str, current: dict, proposed: dict,
           rationale: list, threshold: float) -> Verdict:
    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",
             "content": build_user_prompt(current, proposed, rationale, threshold)},
        ],
        format=CRITIC_SCHEMA,
        options={"temperature": 0},
    )
    return parse_critic_response(json.loads(response["message"]["content"]))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `host/.venv/bin/pytest tests/test_actor.py tests/test_critic.py -v`
Expected: PASS

- [ ] **Step 6: Integration check against Ollama**

```bash
host/.venv/bin/python -c "
import ollama
from amh.actor import propose
from amh.parameters import defaults
p = propose(ollama.Client(), 'qwen2.5-coder',
            window=[{'drift_variance':0.5,'battery':3.4}],
            current=defaults(), threshold=3.5)
print(p.parameters, p.rationale)
"
```
Expected: a dict of in-domain parameters and a non-empty rationale.

- [ ] **Step 7: Commit**

```bash
git add host/amh/actor.py host/amh/critic.py host/tests/test_actor.py host/tests/test_critic.py
git commit -m "Add Actor and Critic over Ollama"
```

---

## Phase 4: Pipeline and closed loop

### Task 4.1: Compile size parsing

**Files:**
- Create: `host/amh/flash.py`
- Test: `host/tests/test_flash.py`

- [ ] **Step 1: Write the failing test**

```python
from amh.flash import parse_compile_output


SAMPLE = (
    "Sketch uses 123456 bytes (15%) of program storage space. Maximum is 811008 bytes.\n"
    "Global variables use 45678 bytes (18%) of dynamic memory, leaving 200000 bytes.\n"
)


def test_parse_compile_output_extracts_usage():
    r = parse_compile_output(SAMPLE)
    assert r.flash_bytes == 123456
    assert r.ram_bytes == 45678
    assert r.flash_pct == 15
```

- [ ] **Step 2: Run test to verify it fails**

Run: `host/.venv/bin/pytest tests/test_flash.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `host/amh/flash.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `host/.venv/bin/pytest tests/test_flash.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add host/amh/flash.py host/tests/test_flash.py
git commit -m "Add compile and flash wrappers"
```

### Task 4.2: Settings

**Files:**
- Create: `host/amh/settings.py`, `host/amh/config.yaml`
- Test: `host/tests/test_settings.py`

- [ ] **Step 1: Write the failing test**

```python
from amh.settings import Settings, load_settings


def test_load_settings_applies_defaults(tmp_path):
    f = tmp_path / "c.yaml"
    f.write_text("mode: unattended\nbattery_threshold: 3.4\n")
    s = load_settings(str(f))
    assert isinstance(s, Settings)
    assert s.mode == "unattended"
    assert s.battery_threshold == 3.4
    assert s.cooldown_s == 30          # default preserved


def test_load_settings_rejects_unknown_mode(tmp_path):
    f = tmp_path / "c.yaml"
    f.write_text("mode: chaos\n")
    try:
        load_settings(str(f))
        assert False
    except ValueError:
        pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `host/.venv/bin/pytest tests/test_settings.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `host/amh/settings.py`**

```python
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
```

- [ ] **Step 4: Write `host/amh/config.yaml`**

```yaml
mode: guarded
battery_threshold: 3.5
cooldown_s: 30
max_interventions: 10
model: qwen2.5-coder
port: ""
dry_run: false
```

- [ ] **Step 5: Run test to verify it passes**

Run: `host/.venv/bin/pytest tests/test_settings.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add host/amh/settings.py host/amh/config.yaml host/tests/test_settings.py
git commit -m "Add host settings"
```

### Task 4.3: Intervention policy

**Files:**
- Create: `host/amh/policy.py`
- Test: `host/tests/test_policy.py`

The policy decides, given a mode and the Critic verdict and validator result, whether to
flash. It is pure and fully testable.

- [ ] **Step 1: Write the failing test**

```python
from amh.policy import FlashDecision, decide_flash


def test_guarded_requires_critic_and_validator():
    assert decide_flash("guarded", critic_accept=True, validator_ok=True).flash is True
    assert decide_flash("guarded", critic_accept=False, validator_ok=True).flash is False
    assert decide_flash("guarded", critic_accept=True, validator_ok=False).flash is False


def test_unattended_ignores_critic():
    assert decide_flash("unattended", critic_accept=False, validator_ok=True).flash is True
    assert decide_flash("unattended", critic_accept=True, validator_ok=False).flash is False


def test_approval_defers_to_human():
    d = decide_flash("approval", critic_accept=True, validator_ok=True)
    assert d.flash is False
    assert d.needs_confirmation is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `host/.venv/bin/pytest tests/test_policy.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `host/amh/policy.py`**

```python
from dataclasses import dataclass


@dataclass
class FlashDecision:
    flash: bool
    needs_confirmation: bool = False


def decide_flash(mode: str, critic_accept: bool, validator_ok: bool) -> FlashDecision:
    if not validator_ok:
        return FlashDecision(flash=False)
    if mode == "unattended":
        return FlashDecision(flash=True)
    if mode == "approval":
        return FlashDecision(flash=False, needs_confirmation=True)
    # guarded
    return FlashDecision(flash=critic_accept)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `host/.venv/bin/pytest tests/test_policy.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add host/amh/policy.py host/tests/test_policy.py
git commit -m "Add intervention flash policy"
```

### Task 4.4: Loop orchestrator

**Files:**
- Create: `host/amh/loop.py`, `host/amh/__main__.py`

Wires the pieces. Logic is delegated to already-tested units; verification is end-to-end on
hardware.

- [ ] **Step 1: Write `host/amh/loop.py`**

```python
import asyncio
import time
from pathlib import Path

import ollama

from amh import actor, critic
from amh.flash import compile_firmware, flash_firmware
from amh.monitor import should_intervene
from amh.parameters import defaults, validate
from amh.policy import decide_flash
from amh.render import render_config
from amh.settings import Settings
from amh.telemetry import Sample
from amh.telemetry_client import stream


class Controller:
    def __init__(self, settings: Settings):
        self.s = settings
        self.client = ollama.Client()
        self.window: list[dict] = []
        self.current = defaults()
        self.last_intervention = 0.0
        self.count = 0

    def _killed(self) -> bool:
        return Path(self.s.kill_switch).exists()

    async def on_sample(self, sample: Sample):
        self.window.append({"drift_variance": sample.drift_variance,
                             "battery": sample.battery})
        self.window = self.window[-30:]

        if self._killed() or self.count >= self.s.max_interventions:
            return

        since = time.monotonic() - self.last_intervention
        if not should_intervene(sample.battery, self.s.battery_threshold,
                                since, self.s.cooldown_s):
            return

        self.last_intervention = time.monotonic()
        await asyncio.to_thread(self._intervene)

    def _intervene(self):
        proposal = actor.propose(self.client, self.s.model, self.window,
                                 self.current, self.s.battery_threshold)
        errors = validate(proposal.parameters)
        if errors:
            print(f"rejected (bounds): {errors}")
            return

        verdict_accept = True
        if self.s.mode == "guarded":
            verdict = critic.review(self.client, self.s.model, self.current,
                                    proposal.parameters, proposal.rationale,
                                    self.s.battery_threshold)
            verdict_accept = verdict.accept
            print(f"critic: {verdict.accept} ({verdict.reason})")

        rendered = render_config(proposal.parameters)
        Path(self.s.config_h_path).write_text(rendered)
        result = compile_firmware(self.s.sketch_dir, self.s.fqbn)
        print(f"compile ok={result.ok} flash={result.flash_pct}%")

        decision = decide_flash(self.s.mode, verdict_accept, result.ok)
        if decision.needs_confirmation:
            answer = input("flash this change? [y/N] ").strip().lower()
            decision = decision.__class__(flash=(answer == "y"))

        if self.s.dry_run:
            print("dry-run: not flashing")
            return
        if not decision.flash:
            print("not flashed")
            return
        if not self.s.port:
            print("no port configured; skipping flash")
            return

        if flash_firmware(self.s.sketch_dir, self.s.fqbn, self.s.port):
            self.current = proposal.parameters
            self.count += 1
            print(f"flashed; intervention {self.count}/{self.s.max_interventions}")


async def run(settings: Settings):
    controller = Controller(settings)
    await stream(controller.on_sample)
```

- [ ] **Step 2: Write `host/amh/__main__.py`**

```python
import argparse
import asyncio

from amh.loop import run
from amh.settings import load_settings


def main():
    parser = argparse.ArgumentParser(prog="amh")
    parser.add_argument("--config", default="amh/config.yaml")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = load_settings(args.config)
    if args.dry_run:
        settings.dry_run = True
    asyncio.run(run(settings))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Dry-run end-to-end**

With firmware flashed and advertising, and `dry_run` honored:
```bash
cd host && .venv/bin/python -m amh --dry-run
```
Expected: telemetry accumulates; once `battery` crosses the threshold, the Actor proposes,
the Critic reviews, `config.h` is rendered, compilation runs, and the run reports it would
flash without flashing.

- [ ] **Step 4: Full closed loop**

Set `port` in `config.yaml` to the board's port, then:
```bash
cd host && .venv/bin/python -m amh
```
Expected: on a threshold breach the node is reflashed; after the new `IMU_POLL_RATE_MS`
takes effect, the observed depletion rate slows. The kill switch (`touch .amh_kill`) halts
further interventions.

- [ ] **Step 5: Commit**

```bash
git add host/amh/loop.py host/amh/__main__.py
git commit -m "Add closed-loop orchestrator"
```

---

## Phase 5: Hardware battery validation (lowest priority, time permitting)

### Task 5.1: Real-battery run

Only after Phases 1–4 are complete and demonstrated.

- [ ] **Step 1: Build with the real battery path**

```bash
arduino-cli compile --fqbn Seeeduino:nrf52:xiaonRF52840Sense \
  --build-property "compiler.cpp.extra_flags=-DAMH_VIRTUAL_BATTERY=0" \
  firmware/amh_node
```

- [ ] **Step 2: Calibrate the divider constant**

Power the board from a small LiPo. Compare `analogRead`-derived voltage against a multimeter
reading across the cell and adjust the `2.961f` constant in `battery.cpp` until they agree
within 0.05 V. Record the procedure and the final constant in `docs/design.md`.

- [ ] **Step 3: Record the run**

Run the closed loop on battery and log whether the polling-interval-to-depletion
relationship observed under the model reproduces on hardware. Add the result to
`docs/design.md`.

- [ ] **Step 4: Commit**

```bash
git add firmware/amh_node/battery.cpp docs/design.md
git commit -m "Add real-battery validation result"
```

---

## README

### Task 6.1: Repository README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`** covering the problem, the three layers, setup
  (`scripts/setup_embedded.sh`, `scripts/setup_model.sh`, the host venv), how to run the
  loop and its modes, and a pointer to `docs/design.md`. Keep it factual and terse.

- [ ] **Step 2: Commit**

```bash
git add README.md && git commit -m "Add project README"
```
