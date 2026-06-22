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


@dataclass
class Verdict:
    accept: bool
    reason: str


def parse_critic_response(data: dict) -> Verdict:
    if "accept" not in data or "reason" not in data:
        raise ValueError("critic response missing 'accept' or 'reason'")
    return Verdict(accept=bool(data["accept"]), reason=str(data["reason"]))


# The Critic stays fully deterministic: it is a ruthless, repeatable gate, not an explorer.
def review(client: ollama.Client, model: str, system: str, user: str,
           temperature: float = 0.0) -> Verdict:
    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        format=CRITIC_SCHEMA,
        options={"temperature": temperature},
    )
    return parse_critic_response(json.loads(response["message"]["content"]))
