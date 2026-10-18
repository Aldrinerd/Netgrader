# tests/test_topic_weights.py
"""
Topic weights (src/topics/weights.py): defaults reproduce today's rubric,
a requested split is applied exactly, a 0% topic is ungraded but kept, and
every invalid request is refused with a reason that names the topic.
"""
import pytest

from src.app import process_bundle_dict
from src.criteria_generator import generate_criteria_from_topology
from src.evaluator import evaluate_student_submission
from src.models import EvaluationCriteria, EvaluationPolicies
from src.topics.weights import TopicWeightError, largest_remainder, minimum_percent, rules_by_topic
from tests.fixtures import network_bundle


def _static_chain():
    return process_bundle_dict(network_bundle("static_chain"))


def _defaults(total=100.0, policies=None):
    return generate_criteria_from_topology(
        _static_chain(), target_total_points=total, policies=policies).topic_weights


def _focus(defaults, key, share=50.0):
    """The Teacher Studio's Focus button: `key` gets `share`, the rest scale down."""
    others = [k for k in defaults if k != key]
    units = largest_remainder([defaults[k] for k in others], round((100 - share) * 10))
    weights = {k: u / 10 for k, u in zip(others, units)}
    weights[key] = share
    return weights


def _zero(defaults, key, onto="static_routing"):
    """Move `key`'s whole share onto `onto`, leaving `key` at 0%."""
    weights = dict(defaults)
    weights[onto] = round(weights[onto] + weights[key], 1)
    weights[key] = 0.0
    return weights


def _with(defaults, **overrides):
    """Defaults with overrides; ip_addressing absorbs the difference so the sum stays 100."""
    weights = dict(defaults)
    weights.update(overrides)
    weights["ip_addressing"] = round(weights["ip_addressing"] + 100 - sum(weights.values()), 1)
    return weights


@pytest.mark.parametrize("weights,units", [([1, 1, 1], 1000), ([8, 8, 8], 500), ([0.3, 0.3, 0.4], 7), ([5, 0, 5], 3)])
def test_largest_remainder_sums_exactly(weights, units):
    alloc = largest_remainder(weights, units)
    assert sum(alloc) == units
    assert all(a >= 0 for a in alloc)


def test_largest_remainder_breaks_ties_by_order_and_skips_zero_weights():
    assert largest_remainder([1, 1, 1], 1000) == [334, 333, 333]
    assert largest_remainder([5, 0, 5], 3) == [2, 0, 1]
    assert largest_remainder([0, 0], 10) == [0, 0]


def test_minimum_percent():
    assert minimum_percent(12, 100.0) == 1.2
    assert minimum_percent(7, 10.0) == 7.0
    assert minimum_percent(3, 37.0) == 0.9   # 0.3 pt of 37 is 0.81%, rounded up


@pytest.mark.parametrize("bundle", ["ospf_clean", "static_chain", "vlan_trunk_mismatch"])
def test_sending_the_defaults_reproduces_the_unweighted_rubric(bundle):
    unweighted = generate_criteria_from_topology(process_bundle_dict(network_bundle(bundle)))
    again = generate_criteria_from_topology(
        process_bundle_dict(network_bundle(bundle)), topic_weights=dict(unweighted.topic_weights))
    assert [(r.rule_id, r.points, r.graded) for r in again.rules] == \
           [(r.rule_id, r.points, r.graded) for r in unweighted.rules]
    assert again.topic_weights == unweighted.topic_weights


def test_default_percent_equals_topic_points_at_100():
    criteria = generate_criteria_from_topology(_static_chain())
    assert criteria.reference_summary["default_topic_weights"] == criteria.topic_weights
    for key, rules in rules_by_topic(criteria.rules).items():
        assert criteria.topic_weights[key] == pytest.approx(round(sum(r.points for r in rules), 1))


@pytest.mark.parametrize("total", [100.0, 50.0, 37.0, 1000.0])
def test_default_weights_sum_to_exactly_100(total):
    assert round(sum(_defaults(total).values()) * 10) == 1000


@pytest.mark.parametrize("total", [100.0, 50.0, 37.0, 1000.0])
def test_focused_rubric_totals_exactly(total):
    weights = _focus(_defaults(total), "static_routing")
    criteria = generate_criteria_from_topology(_static_chain(), target_total_points=total, topic_weights=weights)
    assert round(sum(r.points for r in criteria.rules) * 10) == round(total * 10)
    static_points = sum(r.points for r in criteria.rules if r.category == "static_route")
    assert static_points == pytest.approx(total * 0.5, abs=0.05)
    assert criteria.topic_weights == weights


def test_points_inside_a_topic_keep_base_proportions():
    defaults = generate_criteria_from_topology(process_bundle_dict(network_bundle("vlan_trunk_mismatch"))).topic_weights
    criteria = generate_criteria_from_topology(
        process_bundle_dict(network_bundle("vlan_trunk_mismatch")),
        topic_weights=_focus(defaults, "vlans_trunking"))
    vlan = [r for r in criteria.rules if r.category == "vlan_trunk"]
    trunks = [r.points for r in vlan if r.expected_value["switchport_mode"] == "trunk"]
    access = [r.points for r in vlan if r.expected_value["switchport_mode"] == "access"]
    assert trunks and access
    assert min(trunks) > max(access)   # base 8 vs 6


def test_zero_weight_topic_is_ungraded_but_kept():
    criteria = generate_criteria_from_topology(_static_chain(), topic_weights=_zero(_defaults(), "cabling"))
    cabling = [r for r in criteria.rules if r.category == "cabling"]
    assert cabling and all(not r.graded and r.points == 0.0 for r in cabling)
    assert round(sum(r.points for r in criteria.rules) * 10) == 1000


def test_evaluator_skips_ungraded_rules():
    criteria = generate_criteria_from_topology(_static_chain(), topic_weights=_zero(_defaults(), "cabling"))
    report = evaluate_student_submission(criteria, _static_chain())
    assert all(r.category != "cabling" for r in report.results)
    assert report.max_score == 100.0
    assert report.passed_count + report.failed_count == sum(r.graded for r in criteria.rules)


def test_device_mapping_survives_device_presence_at_zero():
    policies = EvaluationPolicies(allow_custom_hostnames=True)
    weights = _zero(_defaults(policies=policies), "devices")
    criteria = generate_criteria_from_topology(_static_chain(), policies=policies, topic_weights=weights)
    bundle = network_bundle("static_chain")
    bundle["R2.txt"] = bundle["R2.txt"].replace("hostname R2", "hostname BRANCH2")
    bundle["R1.txt"] = bundle["R1.txt"].replace("Device ID: R2", "Device ID: BRANCH2")
    assert evaluate_student_submission(criteria, process_bundle_dict(bundle)).percentage == 100.0


INVALID = [
    (lambda d: [], "JSON object of topic -> percent"),
    (lambda d: {**d, "static_routing": "50"}, "JSON object of topic -> percent"),
    (lambda d: {**d, "static_routing": True}, "JSON object of topic -> percent"),
    (lambda d: {**d, "routing_magic": 0}, 'Unknown topic "routing_magic"'),
    (lambda d: {**d, "stp": 0}, '"stp" cannot be weighted: it is not graded yet'),
    (lambda d: {**d, "security_baseline": 0}, '"Security Baseline" is not part of this rubric'),
    (lambda d: {k: v for k, v in d.items() if k != "cabling"}, 'Missing a weight for "Cabling"'),
    (lambda d: _with(d, cabling=-1.0), '"Cabling" must be between 0 and 100'),
    (lambda d: _with(d, cabling=10.25), '"Cabling" allows one decimal place'),
    (lambda d: {**d, "cabling": round(d["cabling"] - 2.5, 1)}, "Weights add up to 97.5%, they must add up to 100%"),
    (lambda d: {k: 0 for k in d}, "At least one topic must carry points"),
]


@pytest.mark.parametrize("build,message", INVALID)
def test_invalid_weights_are_rejected_with_a_named_reason(build, message):
    with pytest.raises(TopicWeightError) as err:
        generate_criteria_from_topology(_static_chain(), topic_weights=build(_defaults()))
    assert message in str(err.value)


def test_topic_share_too_small_for_its_checkpoints():
    weights = dict(_defaults(10.0))
    spare = round(weights["ip_addressing"] - 0.5, 1)
    weights["ip_addressing"] = 0.5
    weights["static_routing"] = round(weights["static_routing"] + spare, 1)
    with pytest.raises(TopicWeightError, match=r'"IP Addressing" needs at least 7\.0% for its 7 checkpoints'):
        generate_criteria_from_topology(_static_chain(), target_total_points=10.0, topic_weights=weights)


def test_whole_numbers_and_float_sums_are_accepted():
    weights = {k: 0 for k in _defaults()}
    weights.update(static_routing=33.3, ip_addressing=33.3, interface_status=33.4)
    criteria = generate_criteria_from_topology(_static_chain(), topic_weights=weights)
    assert criteria.topic_weights["static_routing"] == 33.3
    assert all(isinstance(v, float) for v in criteria.topic_weights.values())


def test_rubric_from_before_topic_weights_still_grades_identically():
    data = generate_criteria_from_topology(_static_chain()).model_dump()
    data.pop("topic_weights")
    for rule in data["rules"]:
        rule.pop("graded")
    old = EvaluationCriteria(**data)
    assert old.topic_weights == {} and all(r.graded for r in old.rules)
    assert evaluate_student_submission(old, _static_chain()).percentage == 100.0
