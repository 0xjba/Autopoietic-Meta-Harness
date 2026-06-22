import struct
from dataclasses import dataclass

PAYLOAD_FORMAT = "<ff"
PAYLOAD_SIZE = struct.calcsize(PAYLOAD_FORMAT)
TELEMETRY_CHAR_UUID = "f0000002-1111-2222-3333-444455556666"
DEVICE_NAME = "AMH-Node"


@dataclass
class Sample:
    drift_variance: float
    battery: float


def parse(frame: bytes) -> Sample:
    if len(frame) != PAYLOAD_SIZE:
        raise ValueError(f"expected {PAYLOAD_SIZE} bytes, got {len(frame)}")
    drift, battery = struct.unpack(PAYLOAD_FORMAT, frame)
    return Sample(drift_variance=drift, battery=battery)
