# tests/test_frontend_escaping.py
"""
Issue #31: strings taken from an uploaded file or a filename (device names,
interface descriptions, config lines, conflict text, student names) reached
innerHTML unescaped, so a device named <img onerror=...> ran script in the
instructor's browser. This scans every JS module for any template interpolation of those
fields that is not wrapped in escapeHtml().
"""
import os
import re

JS_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "js")

# Fields whose values come from a student's file or filename.
UNTRUSTED_FIELDS = (
    "description", "title", "hostname", "display_name", "name", "device_id",
    "local_interface", "remote_interface", "platform", "signal_type",
    "evidence", "cit", "student", "placeholder_for_device",
    "placeholder_for_interface", "admin_status", "line_status", "msg",
)

# ${ ... } whose expression mentions an untrusted field and is not escapeHtml(...)
INTERPOLATION = re.compile(r"\$\{([^{}]*)\}")


def _js_sources():
    for root, _dirs, files in os.walk(JS_ROOT):
        for name in sorted(files):
            if name.endswith(".js"):
                path = os.path.join(root, name)
                with open(path, encoding="utf-8") as f:
                    yield os.path.relpath(path, JS_ROOT).replace("\\", "/"), f.read()


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


def _unsafe_interpolations(source: str, filename: str = "app.js") -> list[str]:
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
                hits.append(f"{filename}:{lineno}: ${{{expr}}}")
    return hits


def _function_body(name: str) -> str:
    """The function's text up to its closing brace, top-level or indented once."""
    for _file, source in _js_sources():
        marker = f"function {name}"
        if marker in source:
            body = source[source.index(marker):]
            ends = [i for i in (body.find("\n}\n"), body.find("\n    }\n")) if i != -1]
            return body[:min(ends)] if ends else body
    raise AssertionError(f"{name} not found in any module")


def test_untrusted_fields_are_escaped_before_reaching_html():
    hits = []
    for name, source in _js_sources():
        hits += _unsafe_interpolations(source, name)
    assert not hits, "Unescaped untrusted values in HTML templates:\n" + "\n".join(hits)


def test_toast_renders_text_not_html():
    assert "innerHTML" not in _function_body("showToast")


def test_escape_helper_covers_attribute_quotes():
    helper = _function_body("escapeHtml")
    assert "&quot;" in helper and "&#39;" in helper
