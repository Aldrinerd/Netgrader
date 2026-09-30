"""Smoke tests for pka2xml.

Run with ``python -m pytest`` or directly via ``python tests/test_roundtrip.py``.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pka2xml import Twofish, decrypt_pka, encrypt_pka


def test_twofish_kat():
    # I=3, 128-bit case from Twofish reference vectors
    key = bytes.fromhex("9F589F5CF6122C32B6BFEC2F2AE8C35A")
    pt = bytes.fromhex("D491DB16E7B1C39E86CB086B789F5419")
    ct = bytes.fromhex("019F9809DE1711858FAAC3A3BA20FBC3")
    c = Twofish(key)
    assert c.encrypt(pt) == ct
    assert c.decrypt(ct) == pt


def test_roundtrip():
    xml = b"<PACKETTRACER5><VERSION>9.0.0.0000</VERSION></PACKETTRACER5>"
    enc = encrypt_pka(xml)
    dec = decrypt_pka(enc)
    assert dec == xml


if __name__ == "__main__":
    test_twofish_kat()
    test_roundtrip()
    print("OK")
