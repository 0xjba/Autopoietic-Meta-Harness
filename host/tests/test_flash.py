from amh.flash import parse_compile_output


SAMPLE = (
    "Sketch uses 123456 bytes (15%) of program storage space. Maximum is 811008 bytes.\n"
    "Global variables use 45678 bytes (18%) of dynamic memory, leaving 200000 bytes.\n"
)


def test_parse_compile_output_extracts_usage():
    r = parse_compile_output(SAMPLE)
    assert r.flash_bytes == 123456
    assert r.ram_bytes == 45678
    assert r.flash_pct == 15
