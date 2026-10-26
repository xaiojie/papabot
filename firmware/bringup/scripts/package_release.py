#!/usr/bin/env python3
"""Package an already verified build; fail if firmware or its source has changed."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((ROOT / "artifacts/firmware/flash-manifest.json").read_text())
    if not manifest.get("source_sha256"):
        raise RuntimeError("Build source hashes missing. Run bash scripts/pio.sh run first.")
    for name, expected in manifest["source_sha256"].items():
        if digest(ROOT / name) != expected:
            raise RuntimeError("Source changed since compilation: " + name)
    for item in manifest["images"]:
        if digest(ROOT / "artifacts/firmware" / item["file"]) != item["sha256"]:
            raise RuntimeError("Firmware checksum mismatch: " + item["file"])
    if "[SUCCESS]" not in (ROOT / "build.log").read_text():
        raise RuntimeError("Successful cross-build log missing")
    if "0 failures" not in (ROOT / "test/host-test-results.txt").read_text():
        raise RuntimeError("Passing host test log missing")
    selected = [ROOT / name for name in ("README.md", "platformio.ini", "wiring.json", "build.log", ".gitignore")]
    for folder in ("src", "include", "scripts", "docs"):
        selected += [p for p in (ROOT / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    selected += list((ROOT / "test").glob("*.cpp"))
    selected.append(ROOT / "test/host-test-results.txt")
    selected += [p for p in (ROOT / "artifacts/firmware").glob("*") if p.is_file()]
    selected += [ROOT / "artifacts" / n for n in ("image-info.txt", "bootloader-info.txt", "compile-config-check.json")]
    selected = sorted(set(selected))
    checksums = "\n".join(f"{digest(p)}  {p.relative_to(ROOT)}" for p in selected) + "\n"
    (ROOT / "dist").mkdir(exist_ok=True)
    archive = ROOT / "dist/DesktopAssistant-开发测试包-v1.zip"
    prefix = "DesktopAssistant-Bringup-v1/"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in selected: z.write(p, prefix + str(p.relative_to(ROOT)))
        z.writestr(prefix + "SHA256SUMS.txt", checksums)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None: raise RuntimeError("ZIP CRC error")
        for p in selected:
            if hashlib.sha256(z.read(prefix + str(p.relative_to(ROOT)))).hexdigest() != digest(p):
                raise RuntimeError("ZIP payload mismatch: " + str(p))
    result = {"file": archive.name, "bytes": archive.stat().st_size, "sha256": digest(archive),
              "payload_files": len(selected) + 1, "crc_passed": True, "payload_sha256_passed": True}
    (ROOT / "dist/package-validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
