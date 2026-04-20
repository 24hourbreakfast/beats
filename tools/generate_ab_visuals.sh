#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "Missing OPENAI_API_KEY"
  exit 1
fi

python3 tools/generate_ab_visuals.py --config ab/visual-prompts.json --output-dir assets/ab --manifest assets/ab/manifest.json "$@"
