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
