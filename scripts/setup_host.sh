#!/usr/bin/env bash
set -euo pipefail

# Provisions the host Python environment. A managed CPython 3.13 is used via uv
# rather than a Homebrew interpreter: the Homebrew python@3.13 bottle on this
# platform links pyexpat against an incompatible system libexpat, which breaks
# pip and any XML/plist path. uv's standalone interpreter avoids that linkage.

cd "$(dirname "$0")/.."

uv venv host/.venv --python 3.13
uv pip install --python host/.venv/bin/python -e 'host[dev]'
host/.venv/bin/python -c "import bleak, ollama, jinja2, yaml; print('host environment ready')"
