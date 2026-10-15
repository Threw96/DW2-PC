# Optional Spanish resource pack

F1 > Game > Idioma del juego selects English or Spanish. Close and reopen
the game to apply the choice; it is saved as `language = en` or `language = es`.
Existing saves are not converted. The original English `dw2.pak` is unchanged
and still passes its original manifest checks.

Spanish resources come from the user-supplied Alemito translation, not from
a new translation by this contribution's author. This repository contains
only code, sizes and hashes, never ROMs or translated resource bodies.
Alemito agreed to adapting his translation for this PC port in a reply supplied
by the contributor on 2026-10-15, and offered dialogue files to help with the
integration. Credit for the translation remains with Alemito. This approval
is not presented as a general license for the game data. No downloadable
translation pack is provided in this code-only contribution.

## Generate Locally

Requires Python 3 and the supported translated USA raw 2352-byte-sector image.
No Node.js, external extraction directory, PIL, or second original image is
needed for this step. Obtain images independently; no download tool is included.

```sh
python tools/dw2lang.py "/path/to/spanish.bin"
python tools/dw2lang.py --verify build/languages/es.langpak
```

The tool reuses `dw2pack.Image` and `dw2pack.read_files`, verifies the executable,
all 3583 unchanged resources and the 92 supported overrides, then atomically
writes `build/languages/es.langpak`. Other translation revisions are rejected,
not silently accepted or used to rewrite the compiled manifest.

Run the existing native build normally. If the generated pack exists, the
build script validates it and copies it into `languages/es.langpak` beside the
built executable (and the Windows x64 release in `build/play`). Without it,
the build works normally in English. For an existing executable, use `-o`:

```sh
python tools/dw2lang.py "/path/to/spanish.bin" -o /path/to/client/languages/es.langpak
```

The path is relative to the executable, not the working directory. If the
pack is missing or invalid, the runtime falls back to English and reports
the reason in F1. To remove an installed pack, delete that file beside each
executable; removing only the build staging copy does not uninstall old copies.

The 92 overrides include dialogue, fonts, common messages, item/skill data
and graphics. Embedded C text and other untranslated content retain English.
The settings window itself is not fully translated. This is not a claim that
the entire game or every translated dialogue has been tested.

## Tests

Asset-free format/integrity tests:

```sh
python -m unittest discover -s tools -p test_dw2lang.py
```

Optional native runtime tests, using independently generated packs:

```sh
python tools/test_language_runtime.py --exe build/play/dw2.exe --pak build/play/dw2.pak --language-pack build/languages/es.langpak
```

Tests use temporary settings, saves and executable copies, not the player's
files. They cover native startup, Spanish New Game, persistence, English and
six invalid/missing-package cases. They do not test an entire campaign, real
audio, hardware GPU rendering or physical controller input.

## Format v1

Little-endian header (64 bytes): magic `DW2ESPK\0` (8), version u32 (1),
count u32 (92), total bytes u64, base executable SHA-256 (32), reserved u64 (0).
Then 92 entries, sorted by ID: ID u32, size u32, absolute offset u64.
Payloads are contiguous Form 1 data, padded to 2048-byte sectors.

The compiled `host/language_es_manifest.inc` fixes IDs, sizes, original and
translated hashes. The runtime verifies all entries before exposing any
override; code overlays and executable data are never overridden. A different
translation requires an explicitly reviewed manifest change. Active resources
remain immutable for the lifetime of the process, avoiding mixed cached fonts
and dialogue when the user changes the setting.
