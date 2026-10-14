#!/usr/bin/env python3
"""Build/verify the supported Spanish resource pack from a user-supplied disc image."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import struct
import tempfile

import dw2pack

ROOT = Path(__file__).resolve().parents[1]
MAGIC = b"DW2ESPK\0"
HEADER = struct.Struct("<8sIIQ32sQ")
ENTRY = struct.Struct("<IIQ")


def expectations():
    # The runtime's compiled hashes are also the extractor's source of truth.
    text = (ROOT / "host/language_es_manifest.inc").read_text(encoding="ascii")
    def digest(value):
        return bytes(int(byte, 16) for byte in re.findall(r"0x([0-9a-f]{2})", value))
    base = digest(re.search(r"language_base_exe_sha\[32\] = \{([^}]+)\}", text)[1])
    records = re.findall(r"\{(\d+), (\d+), \{([^}]+)\}, \{([^}]+)\}\}", text)
    expected = {int(i): (int(size), digest(original), digest(translated))
                for i, size, original, translated in records}
    if len(base) != 32 or len(expected) != 92 or len(records) != 92:
        raise ValueError("Invalid compiled language manifest")
    return base, expected


def encode(resources, base, expected):
    if set(resources) != set(expected):
        raise ValueError("Resource inventory mismatch")
    offset = HEADER.size + len(expected) * ENTRY.size
    index, bodies = bytearray(), []
    for resource_id, (size, _, translated) in sorted(expected.items()):
        body = resources[resource_id]
        if len(body) != size or hashlib.sha256(body).digest() != translated:
            raise ValueError(f"Spanish resource {resource_id} checksum/size mismatch")
        index.extend(ENTRY.pack(resource_id, size, offset))
        offset += size
        bodies.append(body)
    return HEADER.pack(MAGIC, 1, len(expected), offset, base, 0) + index + b"".join(bodies)


def validate(bundle, base, expected):
    total = HEADER.size + len(expected) * ENTRY.size + sum(v[0] for v in expected.values())
    if len(bundle) != total:
        raise ValueError("Language package size mismatch")
    if HEADER.unpack_from(bundle) != (MAGIC, 1, len(expected), total, base, 0):
        raise ValueError("Unsupported language package header/base")
    cursor = HEADER.size + len(expected) * ENTRY.size
    for position, (resource_id, (size, _, translated)) in enumerate(sorted(expected.items())):
        if ENTRY.unpack_from(bundle, HEADER.size + position * ENTRY.size) != (resource_id, size, cursor):
            raise ValueError("Language package index mismatch")
        if hashlib.sha256(bundle[cursor:cursor + size]).digest() != translated:
            raise ValueError(f"Spanish resource {resource_id} checksum mismatch")
        cursor += size


def extract(image_path, base, expected):
    manifest = dw2pack.read_manifest()
    if bytes.fromhex(manifest["exe"]) != base:
        raise ValueError("Original pack manifest does not match language base")
    if any(bytes.fromhex(manifest[i]) != entry[1] for i, entry in expected.items()):
        raise ValueError("Original resource hashes do not match language base")
    image = dw2pack.Image(str(image_path))
    resources = {}
    try:
        for resource_id, _, _, form, body in dw2pack.read_files(image):
            digest = hashlib.sha256(body).digest()
            if resource_id in expected:
                size, _, translated = expected[resource_id]
                if form != dw2pack.FORMAT_DATA or len(body) != size or digest != translated:
                    raise ValueError(f"Unsupported Spanish resource {resource_id}; translation revision differs")
                resources[resource_id] = body
            elif digest.hex() != manifest[resource_id]:
                raise ValueError(f"Unexpected change to {resource_id}; unsupported image")
    finally:
        image.f.close()
    return encode(resources, base, expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", nargs="?", type=Path, help="raw 2352-byte-sector Spanish .bin/.img")
    parser.add_argument("-o", "--output", type=Path, default=ROOT / "build/languages/es.langpak")
    parser.add_argument("--verify", type=Path, help="verify an existing pack instead of extracting")
    args = parser.parse_args()
    if (args.image is None) == (args.verify is None):
        parser.error("specify either an image or --verify PACK")
    temporary = None
    try:
        base, expected = expectations()
        if args.verify:
            bundle = args.verify.read_bytes()
        else:
            bundle = extract(args.image, base, expected)
        validate(bundle, base, expected)
        if not args.verify:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=args.output.parent, suffix=".tmp", delete=False) as stream:
                temporary = stream.name
                stream.write(bundle)
            os.replace(temporary, args.output)
            temporary = None
        print(f"Spanish pack verified: {len(expected)} resources, {len(bundle)} bytes")
        print(f"SHA-256: {hashlib.sha256(bundle).hexdigest()}")
    except (OSError, ValueError, dw2pack.DiscError) as error:
        parser.exit(1, f"dw2lang: {error}\n")
    finally:
        if temporary is not None:
            os.unlink(temporary)


if __name__ == "__main__":
    main()
