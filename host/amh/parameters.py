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
