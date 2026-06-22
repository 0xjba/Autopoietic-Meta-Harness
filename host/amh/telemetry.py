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
