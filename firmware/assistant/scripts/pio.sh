#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -x "$DIR/../../.tools/bringup-venv/bin/pio" ]]; then PIO="$DIR/../../.tools/bringup-venv/bin/pio"
elif [[ -x "$DIR/.venv/bin/pio" ]]; then PIO="$DIR/.venv/bin/pio"
elif command -v pio >/dev/null 2>&1; then PIO="$(command -v pio)"
else echo "PlatformIO 未安装，参考 bringup/scripts/setup.sh 建一个隔离环境。" >&2; exit 1; fi
cd "$DIR"; exec "$PIO" "$@"
