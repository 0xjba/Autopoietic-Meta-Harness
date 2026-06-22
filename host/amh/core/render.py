from pathlib import Path

from jinja2 import Template


def _format_value(ctype: str, value) -> str:
    if ctype == "int":
        return str(int(value))
    return f"{float(value):.4f}f"


def render_config(params, values: dict, template_path: str) -> str:
    width = max(len(p.name) for p in params)
    lines = [
        f"#define {p.name.ljust(width)} {_format_value(p.ctype, values[p.name])}"
        for p in params
    ]
    template = Template(Path(template_path).read_text())
    return template.render(body="\n".join(lines))
