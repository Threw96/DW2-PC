#!/usr/bin/env python3
"""Optional native smoke tests; requires a built executable and user-generated packs."""
import argparse
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

import dw2lang


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--pak", type=Path, required=True)
    parser.add_argument("--language-pack", type=Path, required=True)
    args = parser.parse_args()
    exe, pak = args.exe.resolve(), args.pak.resolve()
    bundle = args.language_pack.read_bytes()
    dw2lang.validate(bundle, *dw2lang.expectations())
    with tempfile.TemporaryDirectory(prefix="dw2-language-test-") as temporary:
        folder = Path(temporary)
        client = folder / exe.name
        shutil.copy2(exe, client)
        for dependency in exe.parent.glob("*.dll"):
            shutil.copy2(dependency, folder / dependency.name)
        languages = folder / "languages"
        languages.mkdir()
        package = languages / "es.langpak"
        package.write_bytes(bundle)
        settings = folder / "settings.ini"
        completed = 0

        def run(name, active, change=None, fallback=False, frames=120, presses=()):
            nonlocal completed
            command = [str(client), "--pak", str(pak), "--no-window", "--fast",
                       "--vblanks", str(frames), "--no-update-check", "--settings", str(settings),
                       "--save-dir", str(folder / "saves")]
            if change is not None:
                command += ["--settings-set", "language=" + change]
            for press in presses:
                command += ["--press", press]
            result = subprocess.run(command, cwd=folder, capture_output=True, text=True,
                                    errors="replace", timeout=90)
            log = result.stdout + result.stderr
            if (result.returncode != 0 or "[host] shutdown" not in log or
                    f"[language] active={active}" not in log or "all match the manifest" not in log or
                    (fallback and "falling back to English" not in log)):
                raise AssertionError(f"{name} failed:\n{log}")
            print("PASS " + name, flush=True)
            completed += 1

        run("default English", "en")
        run("Spanish New Game", "es", "es", frames=1700,
            presses=("300:Start:4", "650:Up:4", "700:Cross:4"))
        if "language = es" not in settings.read_text():
            raise AssertionError("Spanish preference not saved")
        run("Spanish persisted", "es")
        run("back to English", "en", "en")
        if "language = en" not in settings.read_text():
            raise AssertionError("English preference not saved")
        run("English persisted", "en")
        cases = {"missing": None, "truncated": bundle[:-1]}
        damaged = bytearray(bundle); damaged[-1] ^= 1
        cases["checksum"] = damaged
        damaged = bytearray(bundle); struct.pack_into("<I", damaged, 64, 3675)
        cases["invalid ID"] = damaged
        damaged = bytearray(bundle); struct.pack_into("<Q", damaged, 72, 2**64 - 1)
        cases["invalid offset"] = damaged
        damaged = bytearray(bundle); damaged[24] ^= 1
        cases["wrong base"] = damaged
        for name, data in cases.items():
            if data is None:
                package.unlink()
            else:
                package.write_bytes(data)
            run("fallback: " + name, "en", "es", fallback=True)
        print(f"Runtime language tests passed: {completed} scenarios")


if __name__ == "__main__":
    main()
