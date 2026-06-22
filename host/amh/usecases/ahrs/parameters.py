from amh.core.parameters import Parameter

PARAMETERS = [
    Parameter(
        name="IMU_POLL_RATE_MS",
        ctype="int", minimum=10, maximum=100, default=20,
        description="Time between IMU reads in milliseconds.",
        heuristic_rule=(
            "Higher values save battery but cause cursor lag and stutter on fast hand "
            "flicks."
        ),
    ),
    Parameter(
        name="FILTER_ALPHA",
        ctype="float", minimum=0.80, maximum=0.99, default=0.96,
        description="Complementary filter gyroscope weight.",
        heuristic_rule=(
            "If IMU_POLL_RATE_MS is increased (slower reads), you MUST lower FILTER_ALPHA "
            "to trust the accelerometer more, otherwise the cursor drifts across the screen "
            "while the hand is held still."
        ),
    ),
]
