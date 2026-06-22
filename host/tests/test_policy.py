from amh.policy import FlashDecision, decide_flash


def test_guarded_requires_critic_and_validator():
    assert decide_flash("guarded", critic_accept=True, validator_ok=True).flash is True
    assert decide_flash("guarded", critic_accept=False, validator_ok=True).flash is False
    assert decide_flash("guarded", critic_accept=True, validator_ok=False).flash is False


def test_unattended_ignores_critic():
    assert decide_flash("unattended", critic_accept=False, validator_ok=True).flash is True
    assert decide_flash("unattended", critic_accept=True, validator_ok=False).flash is False


def test_approval_defers_to_human():
    d = decide_flash("approval", critic_accept=True, validator_ok=True)
    assert d.flash is False
    assert d.needs_confirmation is True
