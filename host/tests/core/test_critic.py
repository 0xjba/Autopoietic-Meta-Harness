import pytest

from amh.core.critic import Verdict, parse_critic_response


def test_parse_critic_response_accept():
    v = parse_critic_response({"accept": True, "reason": "within envelope"})
    assert isinstance(v, Verdict)
    assert v.accept is True
    assert v.reason == "within envelope"


def test_parse_critic_response_rejects_malformed():
    with pytest.raises(ValueError):
        parse_critic_response({"reason": "no verdict"})
