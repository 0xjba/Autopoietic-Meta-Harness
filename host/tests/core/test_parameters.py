from amh.core.parameters import Parameter, defaults, json_schema, validate
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
    params = [Parameter("MODE", "int", 0, 3, 0, "discrete knob", allowed=(0, 2))]
    assert any("MODE" in e for e in validate(params, {"MODE": 1}))
    assert validate(params, {"MODE": 2}) == []


def test_schema_uses_enum_for_discrete_and_range_otherwise():
    params = [
        Parameter("R", "int", 0, 10, 1, "range"),
        Parameter("D", "int", 0, 9, 0, "discrete", allowed=(0, 5)),
    ]
    props = json_schema(params)["properties"]["parameters"]["properties"]
    assert "enum" not in props["R"] and props["R"]["minimum"] == 0
    assert props["D"]["enum"] == [0, 5]


def test_schema_lists_all_parameters():
    props = json_schema(PARAMETERS)["properties"]["parameters"]["properties"]
    assert set(props) == {p.name for p in PARAMETERS}
