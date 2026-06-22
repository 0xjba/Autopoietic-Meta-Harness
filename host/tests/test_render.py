from amh.render import render_config


def test_render_formats_by_type():
    out = render_config({"IMU_POLL_RATE_MS": 40, "FILTER_ALPHA": 0.96, "BLE_TX_POWER": 0})
    assert "#define IMU_POLL_RATE_MS 40" in out
    assert "#define FILTER_ALPHA     0.9600f" in out
    assert "#define BLE_TX_POWER     0" in out
    assert "AMH_CONFIG_H" in out


def test_render_is_deterministic():
    v = {"IMU_POLL_RATE_MS": 40, "FILTER_ALPHA": 0.96, "BLE_TX_POWER": 0}
    assert render_config(v) == render_config(v)
