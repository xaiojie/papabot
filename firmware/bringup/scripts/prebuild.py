"""Fail the build on pin drift and regenerate firmware pins before compilation."""
Import("env")
import subprocess
import sys
from pathlib import Path

subprocess.run([sys.executable, str(Path(env.subst("$PROJECT_DIR")) / "scripts/generate_wiring.py")], check=True)
