# tests/test_validation.py
"""
Tests for the validation harness itself.

A measurement instrument that always reports success is worse than no
instrument, so the important test here is the negative control: deliberately
break the engine and confirm the harness notices.
"""

import pytest

from src.criteria_generator import generate_criteria_from_topology
from src.evaluator import evaluate_student_submission
from src.models import EvaluationPolicies
from validation import harness
from validation.mutations import CATALOGUE, by_id
from validation.reference import build_reference


def test_the_reference_is_a_correct_network():
    """
    The precondition the whole suite rests on. Checked under every policy set
    the catalogue uses, because a rubric its own reference cannot satisfy puts
    100% out of reach for the class and makes every other figure meaningless.
    """
    for policies in {m.policies.model_dump_json() for m in CATALOGUE}:
        pol = EvaluationPolicies.model_validate_json(policies)
        reference = build_reference()
        report = evaluate_student_submission(
            generate_criteria_from_topology(reference, policies=pol),
            build_reference(),
        )
        assert report.percentage == 100.0, (
            f"reference is not clean under {pol.model_dump()}: "
            f"{[(r.rule_id, r.actual_value) for r in report.results if not r.passed]}"
        )


def test_every_catalogue_entry_behaves_as_declared():
    """The suite's own pass condition, run as an ordinary test."""
    report = harness.run()
    assert report.reference_clean
    failures = [
        (o.mutation.id, sorted(o.failed_categories), o.guidance_note)
        for o in report.outcomes if not o.passed
    ]
    assert not failures, failures


def test_catalogue_covers_both_directions():
    positives = [m for m in CATALOGUE if not m.is_negative]
    negatives = [m for m in CATALOGUE if m.is_negative]
    assert len(positives) >= 10
    assert len(negatives) >= 4, (
        "specificity needs negative cases: a suite of only faults cannot tell "
        "a strict grader from an accurate one"
    )


def test_mutation_ids_are_unique():
    ids = [m.id for m in CATALOGUE]
    assert len(ids) == len(set(ids))


def test_mutations_do_not_leak_into_each_other():
    """Each case must start from a pristine reference."""
    first = build_reference()
    by_id("interface_shutdown").apply(first)
    assert first.devices["R1"].interfaces["GigabitEthernet0/0"].admin_status != "up"
    second = build_reference()
    assert second.devices["R1"].interfaces["GigabitEthernet0/0"].admin_status == "up"


# --- Negative control: the harness must fail when the engine is wrong -------

def test_harness_reports_a_missed_fault(monkeypatch):
    """Blind the engine and the recall figure must drop."""
    real = harness.evaluate_student_submission

    def blind(criteria, topology):
        report = real(criteria, topology)
        for result in report.results:
            if result.category == "interface_status":
                result.passed = True
                result.points_earned = result.points_possible
        return report

    monkeypatch.setattr(harness, "evaluate_student_submission", blind)
    outcome = harness.run_mutation(by_id("interface_shutdown"))
    assert not outcome.detected
    assert not outcome.passed


def test_harness_reports_a_false_positive(monkeypatch):
    """Make the engine over-strict and specificity must drop."""
    real = harness.evaluate_student_submission

    def over_strict(criteria, topology):
        report = real(criteria, topology)
        for result in report.results:
            if result.category == "device":
                result.passed = False
                result.points_earned = 0.0
        return report

    monkeypatch.setattr(harness, "evaluate_student_submission", over_strict)
    outcome = harness.run_mutation(by_id("native_vlan_agreed"))
    assert outcome.failed_categories == {"device"}
    assert not outcome.passed


def test_harness_reports_non_determinism(monkeypatch):
    """A grader that wobbles between runs must not be reported as consistent."""
    real = harness.evaluate_student_submission
    counter = {"n": 0}

    def wobbly(criteria, topology):
        report = real(criteria, topology)
        counter["n"] += 1
        report.percentage = round(report.percentage - counter["n"], 1)
        return report

    monkeypatch.setattr(harness, "evaluate_student_submission", wobbly)
    outcome = harness.run_mutation(by_id("wrong_ip"))
    assert not outcome.deterministic
    assert not outcome.passed


def test_harness_reports_unusable_guidance(monkeypatch):
    """Strip the explanations and feedback reliability must drop."""
    real = harness.evaluate_student_submission

    def mute(criteria, topology):
        report = real(criteria, topology)
        for result in report.results:
            result.guidance = None
            result.feedback = ""
        return report

    monkeypatch.setattr(harness, "evaluate_student_submission", mute)
    outcome = harness.run_mutation(by_id("native_vlan_mismatch"))
    assert not outcome.guidance_ok
    assert "no guidance" in outcome.guidance_note


def test_report_renders_without_raising():
    text = harness.format_report(harness.run())
    assert "SOP #3" in text
    assert "Accuracy" in text
    assert "Consistency" in text
