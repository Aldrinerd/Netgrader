# src/llm.py
"""
Local LLM client (Phase B).

Talks to a local Ollama daemon over HTTP. Deliberately uses only the standard
library: the lab install must not grow a dependency for an optional feature,
and a school computer should not need extra packages to run the tool.

Three properties this module must guarantee, because the grading architecture
depends on them:

1. It NEVER raises into a caller. Every failure path returns None, and the
   caller falls back to deterministic text.
2. It NEVER sees a score. Callers pass findings; scoring is finished before
   any of this runs.
3. It NEVER blocks indefinitely. Every call is bounded by a timeout, so a
   wedged daemon cannot hang a student's report.

Configuration (all optional):
    NCA_LLM_ENABLED   "0" disables the layer entirely. Default: enabled.
    NCA_LLM_HOST      Ollama base URL. Default: http://127.0.0.1:11434
    NCA_LLM_MODEL     Model tag. Default: llama3.2:3b
    NCA_LLM_TIMEOUT   Seconds per generation. Default: 45
"""

import json
import os
import time
import urllib.error
import urllib.request

DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "llama3.2:3b"
DEFAULT_TIMEOUT = 45.0

# Availability is cached briefly so that grading a class of 40 does not make
# 40 probe requests to a daemon that is not there.
_AVAILABILITY_TTL_SECONDS = 30.0
_availability_cache: dict = {"checked_at": 0.0, "available": False, "models": []}


def _host() -> str:
    return os.environ.get("NCA_LLM_HOST", DEFAULT_HOST).rstrip("/")


def model_name() -> str:
    return os.environ.get("NCA_LLM_MODEL", DEFAULT_MODEL)


def _timeout() -> float:
    try:
        return float(os.environ.get("NCA_LLM_TIMEOUT", DEFAULT_TIMEOUT))
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT


def is_enabled() -> bool:
    return os.environ.get("NCA_LLM_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")


def reset_availability_cache() -> None:
    """Forget the cached probe. Used by tests and after a config change."""
    _availability_cache.update({"checked_at": 0.0, "available": False, "models": []})


def status() -> dict:
    """
    Describe the layer for diagnostics and for the UI.

    Never raises. A machine with no Ollama simply reports available=False, and
    everything downstream continues on deterministic text.
    """
    if not is_enabled():
        return {"enabled": False, "available": False, "model": model_name(),
                "host": _host(), "detail": "disabled by NCA_LLM_ENABLED"}

    now = time.monotonic()
    if now - _availability_cache["checked_at"] < _AVAILABILITY_TTL_SECONDS:
        available = _availability_cache["available"]
        models = _availability_cache["models"]
    else:
        available, models = False, []
        try:
            request = urllib.request.Request(_host() + "/api/tags", method="GET")
            with urllib.request.urlopen(request, timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
            models = [m.get("name", "") for m in payload.get("models", [])]
            available = True
        except Exception:
            available, models = False, []
        _availability_cache.update({"checked_at": now, "available": available, "models": models})

    wanted = model_name()
    # Ollama reports "llama3.2:3b"; accept a bare "llama3.2" match too.
    has_model = any(m == wanted or m.split(":")[0] == wanted.split(":")[0] for m in models)

    if not available:
        detail = f"no Ollama daemon at {_host()}"
    elif not has_model:
        detail = f"daemon running, but model '{wanted}' is not pulled"
    else:
        detail = "ready"

    return {
        "enabled": True,
        "available": bool(available and has_model),
        "model": wanted,
        "host": _host(),
        "models_present": models,
        "detail": detail,
    }


def is_available() -> bool:
    return status()["available"]


def generate(prompt: str, system: str = "", max_tokens: int = 320) -> str | None:
    """
    Run one generation. Returns None on ANY failure.

    Returning None rather than raising is the whole contract: the caller
    already holds correct deterministic text and only wants better phrasing.
    """
    if not is_enabled():
        return None

    body = {
        "model": model_name(),
        "prompt": prompt,
        "stream": False,
        "options": {
            # Low temperature: this is explanation of fixed findings, not
            # creative writing. Determinism is a feature here.
            "temperature": 0.2,
            "num_predict": max_tokens,
        },
    }
    if system:
        body["system"] = system

    try:
        request = urllib.request.Request(
            _host() + "/api/generate",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=_timeout()) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
        text = (payload.get("response") or "").strip()
        return text or None
    except Exception:
        # Daemon down, model missing, timeout, malformed JSON, anything at all.
        return None


def chat(messages: list[dict], system: str = "", max_tokens: int = 400) -> str | None:
    """
    Run one multi-turn chat completion. Returns None on ANY failure.

    ``messages`` is a list of {"role": "user"|"assistant", "content": str},
    oldest first. Same contract as generate(): bounded by the timeout, never
    raises, and the caller decides what to show when it returns None.
    """
    if not is_enabled():
        return None

    body = {
        "model": model_name(),
        "messages": ([{"role": "system", "content": system}] if system else []) + list(messages),
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": max_tokens},
    }
    try:
        request = urllib.request.Request(
            _host() + "/api/chat",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=_timeout()) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
        text = ((payload.get("message") or {}).get("content") or "").strip()
        return text or None
    except Exception:
        return None
