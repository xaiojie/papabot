#!/usr/bin/env python3
"""在主机上编译并运行可测的纯逻辑（脏矩形、布局、解析）。"""
import os, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "test/.build/logic-tests"
out.parent.mkdir(parents=True, exist_ok=True)
subprocess.run([os.environ.get("CXX","c++"), "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic",
                "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                "-I"+str(ROOT/"include"), str(ROOT/"test/test_logic.cpp"), "-o", str(out)], check=True)
raise SystemExit(subprocess.run([str(out)]).returncode)
