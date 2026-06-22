import json
from pathlib import Path

from amh.usecases.ahrs.parameters import PARAMETERS
from amh.usecases.ahrs.schema import SERVICE_UUID, TELEMETRY_CHAR_UUID, Sample, parse

_TEMPLATE = str(Path(__file__).resolve().parent / "config.h.j2")

_ACTOR_SYSTEM = (
    "You tune firmware for a battery-constrained inertial sensor node. "
    "Raising IMU_POLL_RATE_MS lengthens deep-sleep intervals and lowers power "
    "draw at the cost of orientation accuracy. When the battery is below its "
    "threshold, reduce power draw while keeping accuracy as high as the budget "
    "allows. Respond only with the requested JSON."
)

_CRITIC_SYSTEM = (
    "You review a proposed firmware tuning change for a battery-constrained "
    "inertial node. Accept only if the change plausibly reduces power draw under "
    "a low battery while not needlessly destroying orientation accuracy. "
    "Respond only with the requested JSON."
)


def _bounds_table() -> str:
    rows = []
    for p in PARAMETERS:
        domain = f"one of {list(p.allowed)}" if p.allowed else f"[{p.minimum}, {p.maximum}]"
        rows.append(f"- {p.name} ({p.ctype}): {domain}; {p.description}")
    return "\n".join(rows)


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
            f"Tunable parameters and domains:\n{_bounds_table()}\n"
            f"Recent telemetry (oldest first): {json.dumps(window)}.\n"
            "Propose new parameter values and a rationale per changed parameter."
        )

    def critic_system(self) -> str:
        return _CRITIC_SYSTEM

    def critic_user(self, current: dict, proposed: dict, rationale: list) -> str:
        return (
            f"Battery threshold: {self.battery_threshold} V.\n"
            f"Current parameters: {json.dumps(current)}.\n"
            f"Proposed parameters: {json.dumps(proposed)}.\n"
            f"Actor rationale: {json.dumps(rationale)}.\n"
            "Accept or reject this change."
        )
