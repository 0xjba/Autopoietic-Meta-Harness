from amh.monitor import should_intervene


def test_triggers_below_threshold_after_cooldown():
    assert should_intervene(3.40, 3.50, seconds_since_last=120, cooldown_s=60) is True


def test_no_trigger_above_threshold():
    assert should_intervene(3.80, 3.50, seconds_since_last=120, cooldown_s=60) is False


def test_no_trigger_within_cooldown():
    assert should_intervene(3.40, 3.50, seconds_since_last=10, cooldown_s=60) is False
