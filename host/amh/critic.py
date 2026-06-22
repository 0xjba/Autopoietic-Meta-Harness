import json
from dataclasses import dataclass

import ollama

CRITIC_SCHEMA = {
    "type": "object",
    "properties": {
        "accept": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["accept", "reason"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = (
    "You review a proposed firmware tuning change for a battery-constrained "
    "inertial node. Accept only if the change plausibly reduces power draw under "
    "a low battery while not needlessly destroying orientation accuracy. "
    "Respond only with the requested JSON."
)


@dataclass
class Verdict:
    accept: bool
    reason: str


def parse_critic_response(data: dict) -> Verdict:
    if "accept" not in data or "reason" not in data:
        raise ValueError("critic response missing 'accept' or 'reason'")
    return Verdict(accept=bool(data["accept"]), reason=str(data["reason"]))


def build_user_prompt(current: dict, proposed: dict, rationale: list,
                      threshold: float) -> str:
    return (
        f"Battery threshold: {threshold} V.\n"
        f"Current parameters: {json.dumps(current)}.\n"
        f"Proposed parameters: {json.dumps(proposed)}.\n"
        f"Actor rationale: {json.dumps(rationale)}.\n"
        "Accept or reject this change."
    )


def review(client: ollama.Client, model: str, current: dict, proposed: dict,
           rationale: list, threshold: float) -> Verdict:
    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",
             "content": build_user_prompt(current, proposed, rationale, threshold)},
        ],
        format=CRITIC_SCHEMA,
        options={"temperature": 0},
    )
    return parse_critic_response(json.loads(response["message"]["content"]))
