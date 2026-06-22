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
    bad["BLE_TX_POWER"] = 1
    assert any("BLE_TX_POWER" in e for e in validate(bad))


def test_schema_lists_all_parameters():
    schema = json_schema()
    props = schema["properties"]["parameters"]["properties"]
    assert set(props) == {p.name for p in PARAMETERS}
