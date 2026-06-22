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


# The Actor is allowed a small temperature so it explores the parameter space rather than
# collapsing to a single fixed response. This makes proposals non-deterministic by design.
def propose(client: ollama.Client, model: str, schema: dict, system: str,
            user: str, temperature: float = 0.2) -> Proposal:
    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        format=schema,
        options={"temperature": temperature},
    )
    return parse_actor_response(json.loads(response["message"]["content"]))
