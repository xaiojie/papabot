#!/usr/bin/env bash
set -euo pipefail
BRINGUP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -x "$BRINGUP_DIR/.venv/bin/pio" ]]; then
  BRINGUP_PIO="$BRINGUP_DIR/.venv/bin/pio"
elif [[ -x "$BRINGUP_DIR/../../.tools/bringup-venv/bin/pio" ]]; then
  BRINGUP_PIO="$BRINGUP_DIR/../../.tools/bringup-venv/bin/pio"
elif command -v pio >/dev/null 2>&1; then
  BRINGUP_PIO="$(command -v pio)"
else
  echo "PlatformIO 未安装。请先运行 bash scripts/setup.sh。" >&2
  exit 1
fi
cd "$BRINGUP_DIR"
exec "$BRINGUP_PIO" "$@"
