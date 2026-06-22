from amh.settings import Settings, load_settings


def test_load_settings_applies_defaults(tmp_path):
    f = tmp_path / "c.yaml"
    f.write_text("mode: unattended\nbattery_threshold: 3.4\n")
    s = load_settings(str(f))
    assert isinstance(s, Settings)
    assert s.mode == "unattended"
    assert s.battery_threshold == 3.4
    assert s.cooldown_s == 30


def test_load_settings_rejects_unknown_mode(tmp_path):
    f = tmp_path / "c.yaml"
    f.write_text("mode: chaos\n")
    try:
        load_settings(str(f))
        assert False
    except ValueError:
        pass
