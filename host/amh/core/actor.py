import json
from dataclasses import dataclass

import ollama


@dataclass
class Proposal:
    parameters: dict
    rationale: list


def parse_actor_response(data: dict) -> Proposal:
    if "parameters" not in data:
        raise ValueError("actor response missing 'parameters'")
    return Proposal(parameters=data["parameters"], rationale=data.get("rationale", []))


def propose(client: ollama.Client, model: str, schema: dict, system: str,
            user: str) -> Proposal:
    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        format=schema,
        options={"temperature": 0},
    )
    return parse_actor_response(json.loads(response["message"]["content"]))
