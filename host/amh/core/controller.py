import asyncio
import time
from pathlib import Path

from amh.core.actor import propose
from amh.core.critic import review
from amh.core.interfaces import Deployer, TelemetrySource, UseCase
from amh.core.monitor import should_intervene
from amh.core.parameters import defaults, json_schema, validate
from amh.core.policy import FlashDecision, decide_flash
from amh.core.render import render_config
from amh.core.settings import Settings


class Controller:
    def __init__(self, settings: Settings, source: TelemetrySource, deployer: Deployer,
                 usecase: UseCase, client):
        self.s = settings
        self.source = source
        self.deployer = deployer
        self.usecase = usecase
        self.client = client
        self.window: list[dict] = []
        self.current = defaults(usecase.parameters)
        self.last_intervention = 0.0
        self.count = 0

    def _killed(self) -> bool:
        return Path(self.s.kill_switch).exists()

    async def run(self):
        await self.source.stream(self.on_frame)

    async def on_frame(self, frame: bytes):
        sample = self.usecase.parse(frame)
        self.window.append(self.usecase.observation(sample))
        self.window = self.window[-30:]

        if self._killed() or self.count >= self.s.max_interventions:
            return

        since = time.monotonic() - self.last_intervention
        if not should_intervene(self.usecase.is_violation(sample), since, self.s.cooldown_s):
            return

        self.last_intervention = time.monotonic()
        await asyncio.to_thread(self._intervene)

    def _intervene(self):
        schema = json_schema(self.usecase.parameters)
        proposal = propose(self.client, self.s.model, schema,
                           self.usecase.actor_system(),
                           self.usecase.actor_user(self.window, self.current))
        errors = validate(self.usecase.parameters, proposal.parameters)
        if errors:
            print(f"rejected (bounds): {errors}")
            return

        accept = True
        if self.s.mode == "guarded":
            verdict = review(self.client, self.s.model,
                             self.usecase.critic_system(),
                             self.usecase.critic_user(self.current, proposal.parameters,
                                                      proposal.rationale))
            accept = verdict.accept
            print(f"critic: {verdict.accept} ({verdict.reason})")

        config_text = render_config(self.usecase.parameters, proposal.parameters,
                                    self.usecase.template_path)
        outcome = self.deployer.build(config_text)
        print(f"build ok={outcome.ok} ({outcome.detail})")

        decision = decide_flash(self.s.mode, accept, outcome.ok)
        if decision.needs_confirmation:
            answer = input("flash this change? [y/N] ").strip().lower()
            decision = FlashDecision(flash=(answer == "y"))

        if self.s.dry_run:
            print("dry-run: not flashing")
            return
        if not decision.flash:
            print("not flashed")
            return

        if self.deployer.deploy():
            self.current = proposal.parameters
            self.count += 1
            print(f"flashed; intervention {self.count}/{self.s.max_interventions}")
