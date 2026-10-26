"""PlatformIO post-build action: preserve the exact images and offsets it selected."""
Import("env")
import hashlib
import json
import shutil
from pathlib import Path


def export_images(source, target, env):
    project = Path(env.subst("$PROJECT_DIR"))
    build = Path(env.subst("$BUILD_DIR"))
    out = project / "artifacts/firmware"
    out.mkdir(parents=True, exist_ok=True)
    entries = []
    images = list(env.get("FLASH_EXTRA_IMAGES", []))
    images.append((env.subst("$ESP32_APP_OFFSET"), str(build / "firmware.bin")))
    for offset, filename in images:
        path = Path(env.subst(str(filename)))
        address = int(str(offset), 0) if not isinstance(offset, int) else offset
        destination = out / path.name
        shutil.copyfile(path, destination)
        entries.append({"offset": hex(address), "file": destination.name, "bytes": destination.stat().st_size,
                        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()})
    entries.sort(key=lambda item: int(item["offset"], 0))
    for current, following in zip(entries, entries[1:]):
        assert int(current["offset"], 0) + current["bytes"] <= int(following["offset"], 0), "Flash image overlap"
    inputs = [project / "platformio.ini", project / "wiring.json"]
    inputs += sorted((project / "src").glob("*.cpp")) + sorted((project / "include").glob("*.h"))
    inputs += [project / "scripts" / name for name in ("generate_wiring.py", "prebuild.py", "export_firmware.py")]
    hashes = {str(path.relative_to(project)): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
    manifest = {"board": "LCKFB ESP32S3R8N8", "chip": "esp32s3", "flash_size": "8MB",
                "status": "cross-compiled; not flashed or tested on hardware",
                "source": "PlatformIO FLASH_EXTRA_IMAGES and ESP32_APP_OFFSET", "images": entries,
                "source_sha256": hashes}
    (out / "flash-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Exported firmware + build-selected offsets:", out)


env.AddPostAction("$BUILD_DIR/${PROGNAME}.bin", export_images)
