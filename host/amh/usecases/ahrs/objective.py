import json
from pathlib import Path

from amh.usecases.ahrs.parameters import PARAMETERS
from amh.usecases.ahrs.schema import SERVICE_UUID, TELEMETRY_CHAR_UUID, Sample, parse

_TEMPLATE = str(Path(__file__).resolve().parent / "config.h.j2")

_ACTOR_SYSTEM = (
    "You tune firmware for a battery-constrained IMU air mouse. The device reports "
    "orientation drift and battery voltage; your parameters trade battery life against "
    "cursor responsiveness. When the battery is below its threshold, reduce power draw, "
    "but respect the physics rules so the cursor does not lag or drift. Respond only with "
    "the requested JSON."
)

_CRITIC_SYSTEM = (
    "You review a proposed firmware tuning change for a battery-constrained IMU air mouse. "
    "Accept only if the change plausibly reduces power draw under a low battery while "
    "respecting the stated physics rules (a slower poll rate requires a lower filter alpha, "
    "or the cursor drifts). Reject changes that would cause cursor lag or drift. Respond "
    "only with the requested JSON."
)


def _bounds_table() -> str:
    rows = []
    for p in PARAMETERS:
        domain = f"one of {list(p.allowed)}" if p.allowed else f"[{p.minimum}, {p.maximum}]"
        rows.append(f"- {p.name} ({p.ctype}): {domain}; {p.description}")
    return "\n".join(rows)


def _heuristics() -> str:
    return "\n".join(f"- {p.name}: {p.heuristic_rule}" for p in PARAMETERS if p.heuristic_rule)


class AhrsUseCase:
    parameters = PARAMETERS
    template_path = _TEMPLATE
    service_uuid = SERVICE_UUID
    char_uuid = TELEMETRY_CHAR_UUID

    def __init__(self, battery_threshold: float):
        self.battery_threshold = battery_threshold

    def parse(self, frame: bytes) -> Sample:
        return parse(frame)

    def observation(self, sample: Sample) -> dict:
        return {"drift_variance": sample.drift_variance, "battery": sample.battery}

    def is_violation(self, sample: Sample) -> bool:
        return sample.battery < self.battery_threshold

    def actor_system(self) -> str:
        return _ACTOR_SYSTEM

    def actor_user(self, window: list, current: dict) -> str:
        return (
            f"Battery threshold: {self.battery_threshold} V.\n"
            f"Current parameters: {json.dumps(current)}.\n"
            f"Tunable parameters and domains:\n{_bounds_table()}\n\n"
            f"Physics rules for this device:\n{_heuristics()}\n\n"
            f"Recent telemetry (oldest first): {json.dumps(window)}.\n"
            "Propose new parameter values and a rationale per changed parameter. Scale the "
            "change to how far the battery is below the threshold, and obey the physics "
            "rules."
        )

    def critic_system(self) -> str:
        return _CRITIC_SYSTEM

    def critic_user(self, current: dict, proposed: dict, rationale: list) -> str:
        return (
            f"Battery threshold: {self.battery_threshold} V.\n"
            f"Current parameters: {json.dumps(current)}.\n"
            f"Proposed parameters: {json.dumps(proposed)}.\n"
            f"Physics rules for this device:\n{_heuristics()}\n"
            f"Actor rationale: {json.dumps(rationale)}.\n"
            "Accept or reject this change."
        )
