#!/usr/bin/env bash
set -euo pipefail

MODEL="${AMH_MODEL:-llama3.1}"
ollama pull "$MODEL"
ollama list | grep -i "$MODEL"
