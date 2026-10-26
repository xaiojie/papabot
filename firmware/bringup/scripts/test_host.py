#!/usr/bin/env python3
"""Compile and execute the real control policies on the host with sanitizers."""
import os
import subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "test/.build/control-tests"
out.parent.mkdir(parents=True, exist_ok=True)
subprocess.run([os.environ.get("CXX", "c++"), "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic", "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-I" + str(ROOT / "include"), str(ROOT / "test/test_control_logic.cpp"), "-o", str(out)], check=True)
raise SystemExit(subprocess.run([str(out)]).returncode)
