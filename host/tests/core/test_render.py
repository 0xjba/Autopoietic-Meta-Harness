from pathlib import Path

from amh.core.parameters import defaults
from amh.core.render import render_config
from amh.usecases.ahrs.objective import AhrsUseCase
from amh.usecases.ahrs.parameters import PARAMETERS

_CONFIG_H = Path(__file__).resolve().parents[3] / "firmware" / "amh_node" / "config.h"


def test_render_formats_by_type():
    out = render_config(PARAMETERS,
                        {"IMU_POLL_RATE_MS": 40, "FILTER_ALPHA": 0.96, "BLE_TX_POWER": 0},
                        AhrsUseCase.template_path)
    assert "#define IMU_POLL_RATE_MS 40" in out
    assert "#define FILTER_ALPHA     0.9600f" in out
    assert "#define BLE_TX_POWER     0" in out
    assert "AMH_CONFIG_H" in out


def test_render_is_deterministic():
    v = {"IMU_POLL_RATE_MS": 40, "FILTER_ALPHA": 0.96, "BLE_TX_POWER": 0}
    assert (render_config(PARAMETERS, v, AhrsUseCase.template_path)
            == render_config(PARAMETERS, v, AhrsUseCase.template_path))


def test_render_defaults_byte_exact_with_checked_in_config():
    rendered = render_config(PARAMETERS, defaults(PARAMETERS), AhrsUseCase.template_path)
    assert rendered == _CONFIG_H.read_text()
