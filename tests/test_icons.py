# tests/test_icons.py
"""Every icon the UI asks for exists in the vendored sprite, and the licence ships with it."""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(__file__))
SPRITE = os.path.join(ROOT, "static", "icons", "sprite.svg")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _sprite_ids():
    return set(re.findall(r'<symbol id="([a-z-]+)"', _read(SPRITE)))


def _requested_ids():
    found = set()
    for path in glob.glob(os.path.join(ROOT, "templates", "**", "*.html"), recursive=True):
        found |= set(re.findall(r"sprite\.svg[^#\"']*#([a-z-]+)", _read(path)))
    for path in glob.glob(os.path.join(ROOT, "static", "js", "**", "*.js"), recursive=True):
        for call in re.findall(r"\bicon(?:Markup)?\(([^()]*)\)", _read(path)):
            found |= set(re.findall(r"['\"]([a-z-]+)['\"]", call))
    return found


def test_every_requested_icon_is_in_the_sprite():
    missing = sorted(_requested_ids() - _sprite_ids())
    assert not missing, f"icons used but not in sprite.svg: {missing}"


def test_sprite_matches_the_build_script():
    from scripts.build_icon_sprite import ICONS
    assert _sprite_ids() == set(ICONS)


def test_tabler_licence_ships_with_the_sprite():
    licence = _read(os.path.join(ROOT, "static", "icons", "LICENSE-tabler.txt"))
    assert "MIT" in licence and "Tabler Icons" in licence.splitlines()[0]


def test_sprite_is_self_contained():
    sprite = _read(SPRITE)
    assert "http://" not in sprite.replace('xmlns="http://www.w3.org/2000/svg"', "")
    assert "<script" not in sprite
