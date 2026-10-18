# tests/test_weights_rebalance_js.py
"""
Dragging one topic's slider rescales the others so the total stays 100%.
The rebalancing is a pure function in static/js/app.js; these tests run it
in node, and skip when node is not installed.
"""
import json
import os
import shutil
import subprocess

import pytest

APP_JS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "js", "app.js")
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


def _function_source(name: str) -> str:
    with open(APP_JS, encoding="utf-8") as f:
        source = f.read()
    start = source.index(f"function {name}(")
    return source[start:source.index("\n    }\n", start) + len("\n    }\n")]


def _rebalance(weights: dict, key: str, value: float) -> dict:
    script = (_function_source("largestRemainder") + _function_source("rebalanceWeights")
              + f"process.stdout.write(JSON.stringify(rebalanceWeights({json.dumps(weights)}, "
              + f"{json.dumps(key)}, {value})));")
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


BASE = {"devices": 10.0, "ip_addressing": 40.0, "cabling": 20.0, "static_routing": 30.0}


def test_others_scale_proportionally_and_total_stays_100():
    result = _rebalance(BASE, "static_routing", 65.0)
    assert result["static_routing"] == 65.0
    assert round(sum(result.values()), 1) == 100.0
    # 35% left, shared 10:40:20 -> 5.0 / 20.0 / 10.0
    assert (result["devices"], result["ip_addressing"], result["cabling"]) == (5.0, 20.0, 10.0)


def test_zero_topics_stay_off():
    result = _rebalance({**BASE, "cabling": 0.0, "ip_addressing": 60.0}, "static_routing", 50.0)
    assert result["cabling"] == 0.0
    assert round(sum(result.values()), 1) == 100.0


def test_only_topic_with_weight_spreads_the_rest_evenly():
    result = _rebalance({"devices": 0.0, "ip_addressing": 0.0, "static_routing": 100.0}, "static_routing", 40.0)
    assert result == {"devices": 30.0, "ip_addressing": 30.0, "static_routing": 40.0}


def test_value_is_clamped_and_rounded_to_tenths():
    result = _rebalance(BASE, "static_routing", 140.0)
    assert result["static_routing"] == 100.0
    assert all(v == 0.0 for k, v in result.items() if k != "static_routing")
    assert _rebalance(BASE, "static_routing", 33.333)["static_routing"] == 33.3
