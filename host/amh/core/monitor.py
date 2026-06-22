def should_intervene(violation: bool, seconds_since_last: float, cooldown_s: float) -> bool:
    return violation and seconds_since_last >= cooldown_s
