"""Asset-free language package tests: python -m unittest discover -s tools -p test_dw2lang.py."""
import hashlib
import struct
import unittest
from unittest.mock import Mock, patch
import dw2lang


class LanguagePackTests(unittest.TestCase):
    def setUp(self):
        self.base = b"x" * 32
        self.resources = {3: b"a" * 2048, 9: b"b" * 4096}
        self.expected = {i: (len(body), b"o" * 32, hashlib.sha256(body).digest())
                         for i, body in self.resources.items()}
        self.bundle = dw2lang.encode(self.resources, self.base, self.expected)

    def test_roundtrip(self):
        dw2lang.validate(self.bundle, self.base, self.expected)
        self.assertEqual(self.bundle, dw2lang.encode(dict(reversed(list(self.resources.items()))),
                                                   self.base, self.expected))

    def test_bad_headers_and_index(self):
        for offset in (0, 8, 12, 16, 24, 56, 64, 68, 72):
            with self.subTest(offset=offset):
                broken = bytearray(self.bundle)
                broken[offset] ^= 1
                with self.assertRaises(ValueError):
                    dw2lang.validate(broken, self.base, self.expected)

    def test_invalid_offset(self):
        broken = bytearray(self.bundle)
        struct.pack_into("<Q", broken, 72, 2**64 - 1)
        with self.assertRaises(ValueError):
            dw2lang.validate(broken, self.base, self.expected)

    def test_size_and_body(self):
        for broken in (self.bundle[:-1], self.bundle + b"x", self.bundle[:-1] + b"x"):
            with self.assertRaises(ValueError):
                dw2lang.validate(broken, self.base, self.expected)

    def test_encode_rejects_bad_inventory_and_content(self):
        for resources in ({}, {3: b"bad", 9: self.resources[9]}, {**self.resources, 10: b"extra"}):
            with self.assertRaises(ValueError):
                dw2lang.encode(resources, self.base, self.expected)

    def test_compiled_manifest_matches_original(self):
        base, expected = dw2lang.expectations()
        manifest = dw2lang.dw2pack.read_manifest()
        self.assertEqual(base.hex(), manifest["exe"])
        for resource_id, (size, original, translated) in expected.items():
            self.assertEqual(original.hex(), manifest[resource_id])
            self.assertEqual(len(translated), 32)
            self.assertEqual(size % 2048, 0)

    def test_extract_checks_unchanged_resources_and_closes_image(self):
        exe_body = b"dummy executable"
        base = hashlib.sha256(exe_body).digest()
        manifest = {"exe": base.hex(), 3: (b"o" * 32).hex(), 9: (b"o" * 32).hex(),
                    4: hashlib.sha256(b"unchanged").hexdigest()}
        records = [("exe", 0, 0, 0, exe_body), (3, 10, 1, 0, self.resources[3]),
                   (9, 20, 2, 0, self.resources[9]), (4, 30, 1, 0, b"unchanged")]
        for changed in (False, True):
            image = Mock()
            sequence = records.copy()
            if changed:
                sequence[-1] = (4, 30, 1, 0, b"unexpected")
            with patch.object(dw2lang.dw2pack, "Image", return_value=image), \
                 patch.object(dw2lang.dw2pack, "read_manifest", return_value=manifest), \
                 patch.object(dw2lang.dw2pack, "read_files", return_value=iter(sequence)):
                if changed:
                    with self.assertRaises(ValueError):
                        dw2lang.extract("dummy.bin", base, self.expected)
                else:
                    dw2lang.validate(dw2lang.extract("dummy.bin", base, self.expected), base, self.expected)
            image.f.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
