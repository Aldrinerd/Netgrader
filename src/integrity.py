# src/integrity.py
"""
Server-side signatures for things the browser holds and later sends back.

The student chat is grounded in a report, and continues a conversation, that
both live in the page. Without a check, a student could edit the report's
free-text fields into instructions for the model, or plant assistant turns
the model never wrote (issue #19). Each is signed here when the server
produces it and verified when it comes back.

The key is random per server process and never leaves memory. Restarting the
server therefore invalidates open pages: the student grades the lab again.
"""

import hashlib
import hmac
import json
import secrets

from src.models import EvaluationReport

_KEY = secrets.token_bytes(32)


def _sign(kind: str, payload: str) -> str:
    return hmac.new(_KEY, f"{kind}\0{payload}".encode("utf-8"), hashlib.sha256).hexdigest()


def _verify(kind: str, payload: str, signature) -> bool:
    if not isinstance(signature, str) or not signature:
        return False
    return hmac.compare_digest(_sign(kind, payload), signature)


def _report_fingerprint(report: EvaluationReport) -> str:
    """Every report field the chat context is built from, in a fixed form."""
    return json.dumps({
        "lab_title": report.lab_title,
        "passed_count": report.passed_count,
        "failed_count": report.failed_count,
        "study_topics": [
            [t.topic, t.checkpoints_failed, t.why_it_matters] for t in report.study_topics
        ],
        "results": [
            [r.passed, r.target_device, r.target_interface, r.description, r.feedback, r.actual_value]
            for r in report.results
        ],
    }, sort_keys=True, ensure_ascii=True)


def sign_report(report: EvaluationReport) -> str:
    return _sign("report", _report_fingerprint(report))


def verify_report(report: EvaluationReport) -> bool:
    return _verify("report", _report_fingerprint(report), report.findings_signature)


def sign_reply(text: str) -> str:
    return _sign("assistant", text)


def verify_reply(text: str, signature) -> bool:
    return _verify("assistant", text, signature)
