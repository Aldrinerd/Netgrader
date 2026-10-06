"""Tests for repository licensing and third-party notices (Issue #18)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_root_license_exists():
    license_file = ROOT / "LICENSE"
    assert license_file.is_file(), "LICENSE file must exist at repo root"
    content = license_file.read_text(encoding="utf-8")
    assert "MIT License" in content
    assert "Copyright (c) 2026 Netgrader Contributors" in content


def test_third_party_notices_exists():
    notices_file = ROOT / "THIRD_PARTY_NOTICES.md"
    assert notices_file.is_file(), "THIRD_PARTY_NOTICES.md must exist at repo root"
    content = notices_file.read_text(encoding="utf-8")
    assert "pka2xml" in content
    assert "Twofish" in content
    assert "Tabler Icons" in content
    assert "Outfit" in content
    assert "JetBrains Mono" in content
    assert "SIL Open Font License" in content
    assert "BSD 3-Clause" in content


def test_font_ofl_notice_exists():
    ofl_file = ROOT / "static" / "fonts" / "OFL.txt"
    assert ofl_file.is_file(), "static/fonts/OFL.txt must exist alongside web fonts"
    content = ofl_file.read_text(encoding="utf-8")
    assert "SIL OPEN FONT LICENSE Version 1.1" in content


def test_readme_references_license():
    readme_file = ROOT / "README.md"
    assert readme_file.is_file(), "README.md must exist"
    content = readme_file.read_text(encoding="utf-8")
    assert "## License" in content
    assert "[MIT License](LICENSE)" in content
    assert "[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)" in content
