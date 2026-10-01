# tests/test_styles.py
"""
Colours come only from tokens.css, so every theme reaches every element, and
font sizes are in rem, so the text-size setting reaches every element.
Static checks, no browser.
"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(__file__))
COLOUR_RE = re.compile(r"#[0-9A-Fa-f]{3,8}\b|rgba?\(")
PX_FONT_RE = re.compile(r"font-size\s*:\s*[0-9.]+px")
REM_FONT_RE = re.compile(r"font-size\s*:\s*([0-9.]+)rem")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _css_without_comments(text):
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def _styled_files():
    files = [os.path.join(ROOT, "static", "css", "legacy.css")]
    files += glob.glob(os.path.join(ROOT, "static", "css", "layouts", "*.css"))
    files += glob.glob(os.path.join(ROOT, "templates", "**", "*.html"), recursive=True)
    files += [os.path.join(ROOT, "static", "js", "legacy", "app.js")]
    return files


def test_no_hard_coded_colours_outside_tokens():
    hits = []
    for path in _styled_files():
        text = _css_without_comments(_read(path)) if path.endswith(".css") else _read(path)
        for lineno, line in enumerate(text.splitlines(), 1):
            if COLOUR_RE.search(line):
                hits.append(f"{os.path.relpath(path, ROOT)}:{lineno}: {line.strip()[:90]}")
    assert not hits, "Use a token from tokens.css:\n" + "\n".join(hits)


def test_font_sizes_are_rem_and_at_least_12px():
    hits = []
    for path in _styled_files():
        text = _read(path)
        for lineno, line in enumerate(text.splitlines(), 1):
            if PX_FONT_RE.search(line):
                hits.append(f"{os.path.relpath(path, ROOT)}:{lineno}: px font size")
            for value in REM_FONT_RE.findall(line):
                if float(value) < 0.75:
                    hits.append(f"{os.path.relpath(path, ROOT)}:{lineno}: {value}rem is below 12px")
    assert not hits, "\n".join(hits)
