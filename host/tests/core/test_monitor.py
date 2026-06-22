from amh.core.monitor import should_intervene


def test_triggers_when_violation_and_cooldown_elapsed():
    assert should_intervene(True, 120, 60) is True


def test_no_trigger_without_violation():
    assert should_intervene(False, 120, 60) is False


def test_no_trigger_within_cooldown():
    assert should_intervene(True, 10, 60) is False
