"""
Every theme defines every colour token, and the pairs people read pass WCAG:
4.5:1 for text in standard contrast, 7:1 in high contrast, 3:1 for focus
rings and map strokes against the page background.
"""
import os
import re

import pytest

TOKENS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "css", "tokens.css")

BLOCKS = {
    "dark": ':root, :root[data-theme="dark"]',
    "light": ':root[data-theme="light"]',
    "dark-high": ':root[data-theme="dark"][data-contrast="high"]',
    "light-high": ':root[data-theme="light"][data-contrast="high"]',
}
COLOUR_TOKENS = [
    "surface-base", "surface", "surface-raised", "surface-sunken", "line", "line-strong",
    "text", "text-muted", "on-accent", "accent", "accent-strong", "status-ok", "status-bad",
    "status-warn", "focus-ring", "map-router", "map-switch", "map-host", "map-unknown",
    "map-device-fill", "map-link-ok", "map-link-inferred", "map-link-unverified", "map-link-bad",
    "map-badge-bg", "map-port", "map-ip", "map-label",
]
TINTS = [f"tint-{k}-{s}" for k in ("accent", "ok", "bad", "warn", "host", "neutral") for s in ("weak", "mid", "strong")]


def _block(css: str, selector: str) -> dict:
    start = css.index(selector + " {")
    body = css[start + len(selector) + 2: css.index("}", start)]
    return dict(re.findall(r"--([\w-]+)\s*:\s*([^;]+);", body))


@pytest.fixture(scope="module")
def themes():
    css = open(TOKENS, encoding="utf-8").read()
    dark, light = _block(css, BLOCKS["dark"]), _block(css, BLOCKS["light"])
    return {
        "dark": dark,
        "light": light,
        "dark-high": {**dark, **_block(css, BLOCKS["dark-high"])},
        "light-high": {**light, **_block(css, BLOCKS["light-high"])},
    }


def _lum(hex_colour: str) -> float:
    h = hex_colour.strip().lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _ratio(a: str, b: str) -> float:
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("theme", list(BLOCKS))
def test_every_colour_token_is_defined(themes, theme):
    missing = [t for t in COLOUR_TOKENS + TINTS if t not in themes[theme]]
    assert not missing, f"{theme} lacks {missing}"


@pytest.mark.parametrize("theme", list(BLOCKS))
def test_text_contrast(themes, theme):
    t = themes[theme]
    need = 7.0 if theme.endswith("high") else 4.5
    fails = []
    for fg in ("text", "text-muted", "status-ok", "status-bad", "status-warn"):
        for bg in ("surface-base", "surface", "surface-raised"):
            r = _ratio(t[fg], t[bg])
            if r < need:
                fails.append(f"{fg} on {bg} = {r:.2f}")
    r = _ratio(t["on-accent"], t["accent"])
    if r < need:
        fails.append(f"on-accent on accent = {r:.2f}")
    assert not fails, f"{theme} below {need}:1: {fails}"


@pytest.mark.parametrize("theme", list(BLOCKS))
def test_focus_and_map_strokes_are_visible(themes, theme):
    t = themes[theme]
    graphic = ("focus-ring", "map-router", "map-switch", "map-host", "map-link-ok",
               "map-link-inferred", "map-link-unverified", "map-link-bad", "map-unknown", "map-label")
    fails = [f"{g} on {bg} = {_ratio(t[g], t[bg]):.2f}" for g in graphic
             for bg in ("surface-base", "surface-sunken") if _ratio(t[g], t[bg]) < 3.0]
    assert not fails, f"{theme} graphics below 3:1: {fails}"


@pytest.mark.parametrize("theme", list(BLOCKS))
def test_map_text_contrast(themes, theme):
    t = themes[theme]
    need = 7.0 if theme.endswith("high") else 4.5
    texts = ("map-port", "map-ip", "map-label", "map-link-ok", "map-link-inferred",
             "map-link-unverified", "map-link-bad", "map-unknown")
    fails = [f"{g} on {bg} = {_ratio(t[g], t[bg]):.2f}" for g in texts
             for bg in ("map-badge-bg", "surface-sunken") if _ratio(t[g], t[bg]) < need]
    assert not fails, f"{theme} map text below {need}:1: {fails}"


def _blend(rgba: str, base: str) -> str:
    r, g, b, a = [float(x) for x in re.findall(r"[\d.]+", rgba)]
    h = base.strip().lstrip("#")
    bc = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(c * a + k * (1 - a)):02X}" for c, k in zip((r, g, b), bc))


@pytest.mark.parametrize("theme", ["dark-high", "light-high"])
def test_badge_text_on_its_tint_in_high_contrast(themes, theme):
    t = themes[theme]
    pairs = (("status-ok", "ok"), ("status-bad", "bad"), ("status-warn", "warn"), ("accent", "accent"))
    fails = []
    for fg, tint in pairs:
        bg = _blend(t[f"tint-{tint}-mid"], t["surface"])
        if _ratio(t[fg], bg) < 7.0:
            fails.append(f"{fg} on tint-{tint}-mid = {_ratio(t[fg], bg):.2f}")
    assert not fails, f"{theme} badge text below 7:1: {fails}"


def test_legacy_aliases_point_at_semantic_tokens():
    css = open(TOKENS, encoding="utf-8").read()
    for alias, target in (("bg-base", "surface-base"), ("text-primary", "text"),
                          ("accent-blue", "accent"), ("accent-red", "status-bad")):
        assert re.search(rf"--{alias}\s*:\s*var\(--{target}\)", css), alias


def test_text_sizes_scale_the_root():
    css = open(TOKENS, encoding="utf-8").read()
    for size, pct in (("sm", "87.5%"), ("md", "100%"), ("lg", "112.5%"), ("xl", "125%")):
        assert re.search(rf':root\[data-text-size="{size}"\]\s*\{{\s*font-size:\s*{re.escape(pct)}', css), size
