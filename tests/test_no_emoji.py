# tests/test_no_emoji.py
"""No emoji in the UI (issue #15). Icons come from the Tabler sprite."""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(__file__))
EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF☀-➿⬀-⯿⌀-⏿️⃣]"
)


def test_no_emoji_in_templates_or_scripts():
    hits = []
    files = glob.glob(os.path.join(ROOT, "templates", "**", "*.html"), recursive=True)
    files += glob.glob(os.path.join(ROOT, "static", "js", "**", "*.js"), recursive=True)
    for path in files:
        with open(path, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                for ch in EMOJI_RE.findall(line):
                    hits.append(f"{os.path.relpath(path, ROOT)}:{lineno}: U+{ord(ch):04X}")
    assert not hits, "\n".join(hits)


def test_upload_boxes_say_what_they_accept():
    with open(os.path.join(ROOT, "templates", "partials", "panel_grading.html"), encoding="utf-8") as f:
        grading = f.read()
    assert "Accepts .txt or .json" in grading
    assert "Accepts .pkt, .pka, .xml, .zip or .txt" in grading
