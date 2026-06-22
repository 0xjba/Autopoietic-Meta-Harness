import asyncio
import time
from pathlib import Path

import ollama

from amh import actor, critic
from amh.flash import compile_firmware, flash_firmware
from amh.monitor import should_intervene
from amh.parameters import defaults, validate
from amh.policy import decide_flash
from amh.render import render_config
from amh.settings import Settings
from amh.telemetry import Sample
from amh.telemetry_client import stream


class Controller:
    def __init__(self, settings: Settings):
        self.s = settings
        self.client = ollama.Client()
        self.window: list[dict] = []
        self.current = defaults()
        self.last_intervention = 0.0
        self.count = 0

    def _killed(self) -> bool:
        return Path(self.s.kill_switch).exists()

    async def on_sample(self, sample: Sample):
        self.window.append({"drift_variance": sample.drift_variance,
                             "battery": sample.battery})
        self.window = self.window[-30:]

        if self._killed() or self.count >= self.s.max_interventions:
            return

        since = time.monotonic() - self.last_intervention
        if not should_intervene(sample.battery, self.s.battery_threshold,
                                since, self.s.cooldown_s):
            return

        self.last_intervention = time.monotonic()
        await asyncio.to_thread(self._intervene)

    def _intervene(self):
        proposal = actor.propose(self.client, self.s.model, self.window,
                                 self.current, self.s.battery_threshold)
        errors = validate(proposal.parameters)
        if errors:
            print(f"rejected (bounds): {errors}")
            return

        verdict_accept = True
        if self.s.mode == "guarded":
            verdict = critic.review(self.client, self.s.model, self.current,
                                    proposal.parameters, proposal.rationale,
                                    self.s.battery_threshold)
            verdict_accept = verdict.accept
            print(f"critic: {verdict.accept} ({verdict.reason})")

        rendered = render_config(proposal.parameters)
        Path(self.s.config_h_path).write_text(rendered)
        result = compile_firmware(self.s.sketch_dir, self.s.fqbn)
        print(f"compile ok={result.ok} flash={result.flash_pct}%")

        decision = decide_flash(self.s.mode, verdict_accept, result.ok)
        if decision.needs_confirmation:
            answer = input("flash this change? [y/N] ").strip().lower()
            decision = decision.__class__(flash=(answer == "y"))

        if self.s.dry_run:
            print("dry-run: not flashing")
            return
        if not decision.flash:
            print("not flashed")
            return
        if not self.s.port:
            print("no port configured; skipping flash")
            return

        if flash_firmware(self.s.sketch_dir, self.s.fqbn, self.s.port):
            self.current = proposal.parameters
            self.count += 1
            print(f"flashed; intervention {self.count}/{self.s.max_interventions}")


async def run(settings: Settings):
    controller = Controller(settings)
    await stream(controller.on_sample)
