from pathlib import Path

from jinja2 import Template

from amh.parameters import PARAMETERS

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "config.h.j2"


def _format_value(ctype: str, value) -> str:
    if ctype == "int":
        return str(int(value))
    return f"{float(value):.4f}f"


def render_config(values: dict) -> str:
    width = max(len(p.name) for p in PARAMETERS)
    lines = [
        f"#define {p.name.ljust(width)} {_format_value(p.ctype, values[p.name])}"
        for p in PARAMETERS
    ]
    template = Template(TEMPLATE_PATH.read_text())
    return template.render(body="\n".join(lines))
