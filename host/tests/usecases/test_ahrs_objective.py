from amh.usecases.ahrs.objective import AhrsUseCase
from amh.usecases.ahrs.schema import Sample


def test_is_violation_below_threshold():
    uc = AhrsUseCase(battery_threshold=3.5)
    assert uc.is_violation(Sample(0.1, 3.4)) is True
    assert uc.is_violation(Sample(0.1, 3.6)) is False


def test_observation_exposes_fields():
    uc = AhrsUseCase(battery_threshold=3.5)
    obs = uc.observation(Sample(0.25, 3.7))
    assert obs == {"drift_variance": 0.25, "battery": 3.7}
