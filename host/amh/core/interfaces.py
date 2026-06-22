from dataclasses import dataclass
from typing import Awaitable, Callable, Protocol, Sequence

from amh.core.parameters import Parameter


@dataclass
class BuildOutcome:
    ok: bool
    detail: str


class TelemetrySource(Protocol):
    async def stream(self, on_frame: Callable[[bytes], Awaitable[None]]) -> None: ...


class Deployer(Protocol):
    def build(self, config_text: str) -> BuildOutcome: ...

    def deploy(self) -> bool: ...


class UseCase(Protocol):
    parameters: Sequence[Parameter]
    template_path: str
    device_name: str
    char_uuid: str

    def parse(self, frame: bytes) -> object: ...

    def observation(self, sample: object) -> dict: ...

    def is_violation(self, sample: object) -> bool: ...

    def actor_system(self) -> str: ...

    def actor_user(self, window: list, current: dict) -> str: ...

    def critic_system(self) -> str: ...

    def critic_user(self, current: dict, proposed: dict, rationale: list) -> str: ...
