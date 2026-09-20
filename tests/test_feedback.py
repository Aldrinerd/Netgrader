# tests/test_feedback.py
"""
Phase A guidance layer.

The load-bearing test here is test_guidance_cannot_change_a_score. The whole
architectural defence (audit finding R4-1) rests on the claim that the
explanation layer cannot influence grading, so that claim is asserted rather
than assumed.
"""
import pytest

from src.app import process_bundle_dict
from src.criteria_generator import generate_criteria_from_topology
from src.evaluator import evaluate_student_submission
from src.feedback import attach_guidance, explain, study_topics
from src.models import EvaluationPolicies, EvaluationRule, RuleResult
from tests.fixtures import network_bundle

# Every category the rule generator can emit.
ALL_CATEGORIES = [
    "device", "interface_ip", "interface_status", "cabling", "vlan_trunk",
    "routing", "relational_subnet", "link_agreement", "gateway", "security",
    "documentation",
]


def _failed(category, **overrides):
    base = dict(
        rule_id=f"r_{category}",
        category=category,
        description=f"Some {category} requirement",
        points_possible=10.0,
        points_earned=0.0,
        passed=False,
        actual_value="something wrong",
        feedback="it did not match",
        target_device="R1",
        target_interface="GigabitEthernet0/0",
    )
    base.update(overrides)
    return RuleResult(**base)


@pytest.fixture(scope="module")
def graded_report():
    reference = process_bundle_dict(network_bundle("ospf_clean"))
    criteria = generate_criteria_from_topology(
        reference, lab_title="OSPF Ring Lab", policies=EvaluationPolicies()
    )
    student = process_bundle_dict(network_bundle("subnet_cabling_error"))
    return evaluate_student_submission(criteria, student)


@pytest.mark.parametrize("category", ALL_CATEGORIES)
def test_every_category_produces_guidance(category):
    """Coverage is total by construction, so no category may fall through."""
    text = explain(_failed(category))
    assert text, f"no guidance for category '{category}'"
    assert len(text) > 80, f"guidance for '{category}' is too thin to teach anything"


def test_categories_match_the_rule_model():
    """
    If a new rule category is added to the model, this test fails until
    guidance exists for it.
    """
    declared = set(EvaluationRule.model_fields["category"].annotation.__args__)
    assert declared == set(ALL_CATEGORIES), (
        "EvaluationRule categories and guidance coverage have diverged: "
        f"{declared ^ set(ALL_CATEGORIES)}"
    )


def test_passed_checkpoints_get_no_guidance():
    passed = _failed("interface_ip", passed=True, points_earned=10.0)
    assert explain(passed) is None


def test_guidance_distinguishes_failure_modes_within_a_category():
    """A mask error and a wrong-network error must not read identically."""
    wrong_mask = _failed(
        "interface_ip",
        actual_value="10.0.0.1/24",
        feedback="IP address 10.0.0.1 is correct, but subnet mask /24 is incorrect. Expected /30.",
    )
    wrong_network = _failed(
        "interface_ip",
        actual_value="192.168.1.1/24",
        feedback="Configured IP (192.168.1.1/24) does not match expected (10.0.0.1/30).",
    )
    unassigned = _failed("interface_ip", actual_value="No IP configured (Unassigned)")

    texts = {explain(wrong_mask), explain(wrong_network), explain(unassigned)}
    assert len(texts) == 3, "distinct failure modes produced identical guidance"
    assert "mask" in explain(wrong_mask).lower()


def test_relational_subnet_modes_are_distinguished():
    mismatch = _failed("relational_subnet", feedback="Subnet mismatch: R1 and R2 are on different subnets.")
    duplicate = _failed("relational_subnet", feedback="Subnet 10.0.0.0/30 is already used on a different network segment.")
    assert explain(mismatch) != explain(duplicate)
    assert "same subnet" in explain(mismatch).lower()


def test_guidance_does_not_hand_over_the_answer():
    """
    Pedagogical stance: name the concept and the command to investigate with,
    not a paste-ready fix. A bare 'no shutdown' line would defeat the exercise.
    """
    text = explain(_failed("interface_status", actual_value="administratively down"))
    assert "administratively down" in text
    assert "show ip interface brief" in text
    # The literal remediation command must not appear on its own as a fix to copy.
    assert "\nno shutdown" not in text


def test_study_topics_are_ranked_by_points_lost():
    results = [
        _failed("documentation", points_possible=2.0),
        _failed("interface_ip", points_possible=30.0),
        _failed("cabling", points_possible=8.0),
    ]
    topics = study_topics(results)
    assert [t.points_lost for t in topics] == [30.0, 8.0, 2.0]
    assert topics[0].topic == "IPv4 addressing and subnet masks"
    assert topics[0].checkpoints_failed == 1


def test_study_topics_aggregate_repeated_failures():
    results = [_failed("interface_ip", points_possible=5.0) for _ in range(4)]
    topics = study_topics(results)
    assert len(topics) == 1
    assert topics[0].points_lost == 20.0
    assert topics[0].checkpoints_failed == 4


def test_report_is_annotated_end_to_end(graded_report):
    assert graded_report.failed_count > 0
    assert graded_report.study_topics, "a failing report must produce study topics"
    for result in graded_report.results:
        if result.passed:
            assert result.guidance is None
        else:
            assert result.guidance, f"no guidance on failed checkpoint {result.rule_id}"


def test_guidance_cannot_change_a_score(graded_report):
    """
    The architectural boundary, asserted.

    Re-annotating a finished report must leave every score field byte-identical.
    If this ever fails, the explanation layer has gained the ability to affect
    grading and the R4-1 defence no longer holds.
    """
    before = {
        "total": graded_report.total_score,
        "max": graded_report.max_score,
        "percentage": graded_report.percentage,
        "passed": graded_report.passed_count,
        "failed": graded_report.failed_count,
        "letter": graded_report.grade_letter,
        "earned": [r.points_earned for r in graded_report.results],
        "outcomes": [r.passed for r in graded_report.results],
    }

    attach_guidance(graded_report)
    attach_guidance(graded_report)   # idempotent, twice for good measure

    assert graded_report.total_score == before["total"]
    assert graded_report.max_score == before["max"]
    assert graded_report.percentage == before["percentage"]
    assert graded_report.passed_count == before["passed"]
    assert graded_report.failed_count == before["failed"]
    assert graded_report.grade_letter == before["letter"]
    assert [r.points_earned for r in graded_report.results] == before["earned"]
    assert [r.passed for r in graded_report.results] == before["outcomes"]


def test_explain_never_raises_on_malformed_input():
    """Guidance is presentational; it must never break a delivered grade."""
    weird = _failed("interface_ip", actual_value=None, feedback="", target_interface=None)
    assert explain(weird)
    unknown = _failed("a_category_that_does_not_exist")
    assert explain(unknown)


def test_old_reports_without_guidance_still_deserialise():
    """A report serialised before this change must still load."""
    from src.models import EvaluationReport
    legacy = {
        "lab_title": "Old Lab", "total_score": 50.0, "max_score": 100.0,
        "percentage": 50.0, "passed_count": 1, "failed_count": 1,
        "grade_letter": "F", "results": [], "topology": {"devices": {}, "links": [], "conflicts": []},
    }
    report = EvaluationReport(**legacy)
    assert report.study_topics == []
