from dataclasses import dataclass


@dataclass
class FlashDecision:
    flash: bool
    needs_confirmation: bool = False


def decide_flash(mode: str, critic_accept: bool, validator_ok: bool) -> FlashDecision:
    if not validator_ok:
        return FlashDecision(flash=False)
    if mode == "unattended":
        return FlashDecision(flash=True)
    if mode == "approval":
        return FlashDecision(flash=False, needs_confirmation=True)
    return FlashDecision(flash=critic_accept)
