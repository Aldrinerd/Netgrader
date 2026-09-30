# tests/test_frontend_escaping.py
"""
Issue #31: strings taken from an uploaded file or a filename (device names,
interface descriptions, config lines, conflict text, student names) reached
innerHTML unescaped, so a device named <img onerror=...> ran script in the
instructor's browser. This scans app.js for any template interpolation of those
fields that is not wrapped in escapeHtml().
"""
import os
import re

APP_JS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "js", "app.js")

# Fields whose values come from a student's file or filename.
UNTRUSTED_FIELDS = (
    "description", "title", "hostname", "display_name", "name", "device_id",
    "local_interface", "remote_interface", "platform", "signal_type",
    "evidence", "cit", "student", "placeholder_for_device",
    "placeholder_for_interface", "admin_status", "line_status", "msg",
)

# ${ ... } whose expression mentions an untrusted field and is not escapeHtml(...)
INTERPOLATION = re.compile(r"\$\{([^{}]*)\}")


def _blank_text_only_calls(source: str) -> str:
    """
    Blank out showToast(...) arguments, keeping line numbers. The toast sets
    textContent, so its message is not an HTML sink, even across lines.
    """
    out, i = [], 0
    while True:
        start = source.find("showToast(", i)
        if start < 0:
            out.append(source[i:])
            return "".join(out)
        out.append(source[i:start])
        depth, j = 0, start + len("showToast")
        while j < len(source):
            depth += {"(": 1, ")": -1}.get(source[j], 0)
            j += 1
            if depth == 0:
                break
        out.append(re.sub(r"[^\n]", " ", source[start:j]))
        i = j


def _unsafe_interpolations(source: str) -> list[str]:
    source = _blank_text_only_calls(source)
    hits = []
    for lineno, line in enumerate(source.splitlines(), 1):
        # Only lines that build HTML. textContent, attributes on SVG nodes,
        # downloads and plain-text reports are not HTML sinks.
        if "textContent" in line or "reportTxt" in line:
            continue
        for expr in INTERPOLATION.findall(line):
            expr = expr.strip()
            if expr.startswith("escapeHtml("):
                continue
            if re.search(r"(?:^|[.\s(])(?:%s)\b" % "|".join(UNTRUSTED_FIELDS), expr):
                hits.append(f"app.js:{lineno}: ${{{expr}}}")
    return hits


def test_untrusted_fields_are_escaped_before_reaching_html():
    with open(APP_JS, encoding="utf-8") as f:
        hits = _unsafe_interpolations(f.read())
    assert not hits, "Unescaped untrusted values in HTML templates:\n" + "\n".join(hits)


def test_toast_renders_text_not_html():
    with open(APP_JS, encoding="utf-8") as f:
        source = f.read()
    toast = source[source.index("function showToast"):]
    toast = toast[:toast.index("\n    }\n")]
    assert "innerHTML" not in toast


def test_escape_helper_covers_attribute_quotes():
    with open(APP_JS, encoding="utf-8") as f:
        source = f.read()
    helper = source[source.index("function escapeHtml"):]
    helper = helper[:helper.index("\n    }\n")]
    assert "&quot;" in helper and "&#39;" in helper
