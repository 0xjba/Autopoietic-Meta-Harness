import pytest

from amh.core.actor import Proposal, parse_actor_response


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
