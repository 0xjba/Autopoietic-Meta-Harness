def should_intervene(
    battery: float,
    threshold: float,
    seconds_since_last: float,
    cooldown_s: float,
) -> bool:
    return battery < threshold and seconds_since_last >= cooldown_s
