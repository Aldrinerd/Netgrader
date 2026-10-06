"""Tests for GitHub Actions CI workflow configuration (Issue #27)."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent


def test_ci_workflow_structure():
    workflow_file = ROOT / ".github" / "workflows" / "ci.yml"
    assert workflow_file.is_file(), ".github/workflows/ci.yml must exist"
    
    with open(workflow_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    # Check trigger rules
    triggers = data.get("on") or data.get(True)  # YAML 'on' can parse as boolean True
    assert triggers is not None
    assert "push" in triggers
    assert "pull_request" in triggers
    assert "master" in triggers["push"]["branches"]
    assert "master" in triggers["pull_request"]["branches"]
    
    # Check job definition
    jobs = data.get("jobs", {})
    assert "test" in jobs
    job = jobs["test"]
    
    # Check matrix
    strategy = job.get("strategy", {})
    matrix = strategy.get("matrix", {})
    os_list = matrix.get("os", [])
    assert "ubuntu-latest" in os_list
    assert "windows-latest" in os_list
    py_list = matrix.get("python-version", [])
    assert "3.12" in py_list
    
    # Check defaults
    defaults = job.get("defaults", {})
    assert defaults.get("run", {}).get("shell") == "bash"
    
    # Check steps
    steps = job.get("steps", [])
    step_uses = [s.get("uses", "") for s in steps]
    step_runs = [s.get("run", "") for s in steps]
    
    # Checkout
    assert any("actions/checkout" in u for u in step_uses)
    # Node setup
    assert any("actions/setup-node" in u for u in step_uses)
    # Python setup
    assert any("actions/setup-python" in u for u in step_uses)
    # Twofish compile on Linux
    assert any("build_libtwofish.py" in r for r in step_runs)
    # Pip install
    assert any("pip install -r requirements-dev.txt" in r for r in step_runs)
    # Pytest with -rs
    assert any("pytest -q -rs" in r for r in step_runs)
    # Validation JSON output
    assert any("python -m validation --json" in r and "validation-report.json" in r for r in step_runs)
    # Artifact upload with if: always()
    upload_steps = [s for s in steps if "actions/upload-artifact" in s.get("uses", "")]
    assert len(upload_steps) == 1
    assert upload_steps[0].get("if") == "always()"
