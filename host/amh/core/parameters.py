from dataclasses import dataclass, field


@dataclass(frozen=True)
class Parameter:
    name: str
    ctype: str          # "int" or "float"
    minimum: float
    maximum: float
    default: float
    description: str
    heuristic_rule: str = ""                         # physical effect, for the Actor prompt
    allowed: tuple = field(default_factory=tuple)    # discrete set, if constrained


def defaults(params) -> dict:
    return {p.name: p.default for p in params}


def validate(params, values: dict) -> list[str]:
    by_name = {p.name: p for p in params}
    errors: list[str] = []
    for key in values:
        if key not in by_name:
            errors.append(f"unknown parameter {key}")
    for p in params:
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


def json_schema(params) -> dict:
    props = {}
    for p in params:
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
                "required": [p.name for p in params],
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
