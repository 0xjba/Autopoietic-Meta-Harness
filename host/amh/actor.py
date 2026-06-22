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
