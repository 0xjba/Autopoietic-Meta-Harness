from amh.core.parameters import defaults, json_schema, validate
from amh.usecases.ahrs.parameters import PARAMETERS


def test_defaults_are_within_bounds():
    assert validate(PARAMETERS, defaults(PARAMETERS)) == []


def test_validate_rejects_out_of_range():
    bad = defaults(PARAMETERS)
    bad["IMU_POLL_RATE_MS"] = 5
    assert any("IMU_POLL_RATE_MS" in e for e in validate(PARAMETERS, bad))


def test_validate_rejects_unknown_key():
    bad = defaults(PARAMETERS)
    bad["GAIN"] = 1
    assert any("GAIN" in e for e in validate(PARAMETERS, bad))


def test_validate_rejects_disallowed_discrete_value():
    bad = defaults(PARAMETERS)
    bad["BLE_TX_POWER"] = 1
    assert any("BLE_TX_POWER" in e for e in validate(PARAMETERS, bad))


def test_schema_lists_all_parameters():
    props = json_schema(PARAMETERS)["properties"]["parameters"]["properties"]
    assert set(props) == {p.name for p in PARAMETERS}
