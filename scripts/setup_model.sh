#!/usr/bin/env bash
set -euo pipefail

MODEL="${AMH_MODEL:-qwen2.5-coder}"
ollama pull "$MODEL"
ollama list | grep -i "$MODEL"
