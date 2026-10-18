# tests/test_static_routes.py
"""
Static-route grading (src/topics/static_routes.py).

The reference is the static_chain bundle: R1 in the middle, R2 and R3 each
with a LAN, R1 routing to both LANs (one route by next hop, one by exit
interface) and R2/R3 pointing a default route back at R1.
"""
import pytest

from src.app import process_bundle_dict
from src.evaluator import make_eval_context
from src.models import EvaluationCriteria, EvaluationPolicies, RouteEntry
from src.topics.static_routes import evaluate, generate_rules, is_static
from tests.fixtures import network_bundle

STRICT = EvaluationPolicies()
DYNAMIC = EvaluationPolicies(allow_dynamic_subnetting=True)
CUSTOM_NAMES = EvaluationPolicies(allow_custom_hostnames=True)

R1_TO_R2_LAN = "ip route 192.168.2.0 255.255.255.0 10.0.12.2\n"
R1_TO_R3_LAN = "ip route 192.168.3.0 255.255.255.0 GigabitEthernet0/1\n"
R2_DEFAULT = "ip route 0.0.0.0 0.0.0.0 10.0.12.1\n"
R2_ROUTING_TABLE = """R2# show ip route
Gateway of last resort is 10.0.12.1 to network 0.0.0.0
C    10.0.12.0/30 is directly connected, GigabitEthernet0/0
C    192.168.2.0/24 is directly connected, GigabitEthernet0/1
S*   0.0.0.0/0 [1/0] via 10.0.12.1
"""


def _bundle(**edits):
    """static_chain with text edits per device: _bundle(R1=[(old, new), ...])."""
    bundle = network_bundle("static_chain")
    for device, changes in edits.items():
        name = f"{device}.txt"
        for old, new in changes:
            assert old in bundle[name], f"{old!r} not found in {name}"
            bundle[name] = bundle[name].replace(old, new, 1)
    return bundle


def _topology(**edits):
    return process_bundle_dict(_bundle(**edits))


def _grade(reference, student, policies=STRICT):
    """Grade only the static-route rules. Returns ({device: outcome}, rules, warnings)."""
    rules, warnings = generate_rules(reference, policies)
    ctx = make_eval_context(EvaluationCriteria(policies=policies, rules=rules), student)
    return {rule.target_device: evaluate(rule, ctx) for rule in rules}, rules, warnings


def test_one_rule_per_router_with_resolved_routes():
    rules, warnings = generate_rules(_topology(), STRICT)
    assert warnings == []
    by_device = {r.target_device: r for r in rules}
    assert set(by_device) == {"R1", "R2", "R3"}
    r1 = by_device["R1"]
    assert r1.category == "static_route"
    assert r1.points == 8.0
    assert r1.description == "Configure static routes on R1 (2 destinations)"
    routes = {r["network"]: r for r in r1.expected_value["routes"]}
    assert (routes["192.168.2.0"]["via_device"], routes["192.168.2.0"]["style"]) == ("R2", "next_hop")
    assert (routes["192.168.2.0"]["dest_device"], routes["192.168.2.0"]["dest_interface"]) == ("R2", "GigabitEthernet0/1")
    assert (routes["192.168.3.0"]["via_device"], routes["192.168.3.0"]["style"]) == ("R3", "exit_interface")
    default = by_device["R2"].expected_value["routes"][0]
    assert default["is_default"] is True
    assert default["dest_device"] is None
    assert default["via_device"] == "R1"


def test_identical_submission_passes_every_route():
    outcomes, _, _ = _grade(_topology(), _topology())
    assert all(o.passed and o.points_earned == 8.0 for o in outcomes.values())


def test_missing_route_earns_partial_credit():
    outcomes, _, _ = _grade(_topology(), _topology(R1=[(R1_TO_R2_LAN, "")]))
    r1 = outcomes["R1"]
    assert not r1.passed
    assert r1.points_earned == 4.0
    assert r1.actual == "1 of 2 static routes correct"
    assert "no static route to 192.168.2.0/24" in r1.feedback


def test_route_to_the_wrong_neighbor_fails():
    wrong = R1_TO_R2_LAN.replace("10.0.12.2", "10.0.13.2")
    outcomes, _, _ = _grade(_topology(), _topology(R1=[(R1_TO_R2_LAN, wrong)]))
    assert "route to 192.168.2.0/24 points at R3, it should go via R2" in outcomes["R1"].feedback


def test_next_hop_that_is_not_directly_connected_fails():
    far = R1_TO_R2_LAN.replace("10.0.12.2", "10.0.99.9")
    outcomes, _, _ = _grade(_topology(), _topology(R1=[(R1_TO_R2_LAN, far)]))
    assert "next hop 10.0.99.9 is not on a network directly connected to R1" in outcomes["R1"].feedback


def test_missing_default_route_fails():
    outcomes, _, _ = _grade(_topology(), _topology(R2=[(R2_DEFAULT, "")]))
    assert outcomes["R2"].points_earned == 0.0
    assert "no default route (0.0.0.0/0)" in outcomes["R2"].feedback


def test_exit_interface_form_is_accepted():
    by_interface = "ip route 192.168.2.0 255.255.255.0 GigabitEthernet0/0\n"
    outcomes, _, _ = _grade(_topology(), _topology(R1=[(R1_TO_R2_LAN, by_interface)]))
    assert outcomes["R1"].passed


def test_dynamic_subnetting_follows_the_students_own_lan():
    student = _topology(
        R2=[("ip address 192.168.2.1 255.255.255.0", "ip address 192.168.20.1 255.255.255.0")],
        R1=[(R1_TO_R2_LAN, "ip route 192.168.20.0 255.255.255.0 10.0.12.2\n")],
    )
    dynamic, _, _ = _grade(_topology(), student, DYNAMIC)
    strict, _, _ = _grade(_topology(), student, STRICT)
    assert dynamic["R1"].passed
    assert "no static route to 192.168.2.0/24" in strict["R1"].feedback


def test_dynamic_subnetting_reports_an_unaddressed_destination_lan():
    student = _topology(R2=[("ip address 192.168.2.1 255.255.255.0", "no ip address")])
    outcomes, _, _ = _grade(_topology(), student, DYNAMIC)
    assert "the destination LAN on R2 GigabitEthernet0/1 has no address" in outcomes["R1"].feedback


def test_unmappable_summary_checks_the_neighbor_only_under_dynamic_subnetting():
    summary = "ip route 172.16.0.0 255.240.0.0 10.0.12.2\n"
    reference = _topology(R1=[(R1_TO_R3_LAN, R1_TO_R3_LAN + summary)])
    rules, _ = generate_rules(reference, DYNAMIC)
    r1_routes = next(r for r in rules if r.target_device == "R1").expected_value["routes"]
    assert next(r for r in r1_routes if r["network"] == "172.16.0.0")["dest_device"] is None
    dynamic, _, _ = _grade(reference, _topology(), DYNAMIC)
    strict, _, _ = _grade(reference, _topology(), STRICT)
    assert dynamic["R1"].passed          # R1 still has a static route via R2
    assert "no static route to 172.16.0.0/12" in strict["R1"].feedback


@pytest.mark.parametrize("extra,reason", [
    ("ip route 10.9.0.0 255.255.0.0 10.0.12.99\n", "next hop 10.0.12.99 belongs to no device"),
    ("ip route 10.8.0.0 255.255.0.0 10.0.12.1\n", "next hop 10.0.12.1 is one of R1's own addresses"),
    ("ip route 10.7.0.0 255.255.0.0 GigabitEthernet0/2\n",
     "exit interface GigabitEthernet0/2 leads to an unidentified device"),
    ("ip route 10.6.0.0 255.255.0.0 GigabitEthernet0/3\n", "exit interface GigabitEthernet0/3 has no link"),
])
def test_broken_reference_routes_are_skipped_and_reported(extra, reason):
    reference = _topology(R1=[(R1_TO_R3_LAN, R1_TO_R3_LAN + extra)])
    outcomes, rules, warnings = _grade(reference, _topology())
    network = extra.split()[2]
    assert warnings == [f"R1: static route to {network}/16 was not graded because {reason}."]
    assert len(next(r for r in rules if r.target_device == "R1").expected_value["routes"]) == 2
    assert outcomes["R1"].passed     # the class can still reach 100%


def test_routing_table_entries_count_once_and_star_means_static():
    assert is_static(RouteEntry(network="0.0.0.0", cidr=0, protocol="S*"))
    assert is_static(RouteEntry(network="10.0.0.0", cidr=8, protocol="S"))
    assert not is_static(RouteEntry(network="10.0.0.0", cidr=8, protocol="O"))
    with_table = [("R2# show cdp neighbors detail", R2_ROUTING_TABLE + "R2# show cdp neighbors detail")]
    rules, _ = generate_rules(_topology(R2=with_table), STRICT)
    assert len(next(r for r in rules if r.target_device == "R2").expected_value["routes"]) == 1
    student = _topology(R2=[(R2_DEFAULT, "")] + with_table)
    outcomes, _, _ = _grade(_topology(), student)
    assert outcomes["R2"].passed


def test_missing_or_placeholder_student_device_scores_zero():
    gone = _topology()
    del gone.devices["R1"]
    placeholder = _topology()
    placeholder.devices["R1"].is_placeholder = True
    for student in (gone, placeholder):
        outcomes, _, _ = _grade(_topology(), student)
        assert outcomes["R1"].points_earned == 0.0
        assert outcomes["R1"].feedback == "Cannot evaluate static routes: device 'R1' missing."


def test_renamed_neighbor_is_matched_under_custom_hostnames():
    student = _topology(
        R2=[("hostname R2", "hostname BRANCH2")],
        R1=[("Device ID: R2", "Device ID: BRANCH2")],
    )
    outcomes, _, _ = _grade(_topology(), student, CUSTOM_NAMES)
    assert outcomes["R1"].passed and outcomes["R2"].passed


from src.criteria_generator import generate_criteria_from_topology  # noqa: E402
from src.evaluator import evaluate_student_submission  # noqa: E402
from src.topics.registry import TOPICS_BY_KEY, topic_for_category  # noqa: E402


def test_static_routing_topic_is_gradeable():
    topic = TOPICS_BY_KEY["static_routing"]
    assert topic.gradeable and topic.categories == ("static_route",)
    assert topic_for_category("static_route") is topic


def test_generator_adds_static_rules_and_reference_warnings():
    reference = _topology(R1=[(R1_TO_R3_LAN, R1_TO_R3_LAN + "ip route 10.9.0.0 255.255.0.0 10.0.12.99\n")])
    criteria = generate_criteria_from_topology(reference, lab_title="Static Lab")
    assert {r.target_device for r in criteria.rules if r.category == "static_route"} == {"R1", "R2", "R3"}
    assert criteria.reference_summary["reference_warnings"] == [
        "R1: static route to 10.9.0.0/16 was not graded because next hop 10.0.12.99 belongs to no device."
    ]
    assert round(sum(r.points for r in criteria.rules) * 10) == 1000


def test_full_pipeline_scores_a_correct_submission_at_100():
    criteria = generate_criteria_from_topology(_topology())
    assert evaluate_student_submission(criteria, _topology()).percentage == 100.0


def test_full_pipeline_explains_a_wrong_neighbor():
    criteria = generate_criteria_from_topology(_topology())
    wrong = R1_TO_R2_LAN.replace("10.0.12.2", "10.0.13.2")
    report = evaluate_student_submission(criteria, _topology(R1=[(R1_TO_R2_LAN, wrong)]))
    failed = [r for r in report.results if not r.passed]
    assert [(r.category, r.target_device) for r in failed] == [("static_route", "R1")]
    assert "it should go via R2" in failed[0].feedback
    assert "wrong neighbour" in failed[0].guidance
    assert "Static routing and next-hop selection" in [t.topic for t in report.study_topics]


def test_classful_routing_table_children_take_the_subnetted_prefix():
    """IOS prints `10.0.0.0/30 is subnetted` and then child lines with no prefix."""
    extra = "ip route 10.0.99.0 255.255.255.252 10.0.12.2\n"
    table = """R1# show ip route
     10.0.0.0/30 is subnetted, 3 subnets
C       10.0.12.0 is directly connected, GigabitEthernet0/0
C       10.0.13.0 is directly connected, GigabitEthernet0/1
S       10.0.99.0 [1/0] via 10.0.12.2
"""
    reference = _topology(R1=[(R1_TO_R3_LAN, R1_TO_R3_LAN + extra),
                              ("R1# show cdp neighbors detail", table + "R1# show cdp neighbors detail")])
    rules, _ = generate_rules(reference, STRICT)
    r1_routes = next(r for r in rules if r.target_device == "R1").expected_value["routes"]
    assert sorted((r["network"], r["cidr"]) for r in r1_routes if r["network"].startswith("10.")) == [("10.0.99.0", 30)]
    outcomes, _, _ = _grade(reference, _topology(R1=[(R1_TO_R3_LAN, R1_TO_R3_LAN + extra)]))
    assert outcomes["R1"].passed


def test_recursive_reference_next_hop_is_skipped_and_reported():
    recursive = "ip route 192.168.3.0 255.255.255.0 10.0.13.2\n"
    reference = _topology(R2=[(R2_DEFAULT, R2_DEFAULT + recursive)])
    outcomes, rules, warnings = _grade(reference, _topology(R2=[(R2_DEFAULT, R2_DEFAULT + recursive)]))
    assert warnings == ["R2: static route to 192.168.3.0/24 was not graded because "
                        "next hop 10.0.13.2 is not on a network directly connected to R2."]
    assert len(next(r for r in rules if r.target_device == "R2").expected_value["routes"]) == 1
    assert outcomes["R2"].passed


def test_floating_routes_are_graded_regardless_of_line_order():
    primary = "ip route 192.168.2.0 255.255.255.0 10.0.12.2\n"
    backup = "ip route 192.168.2.0 255.255.255.0 10.0.13.2 5\n"
    reference = _topology(R1=[(primary, primary + backup)])
    rules, _ = generate_rules(reference, STRICT)
    r1_routes = next(r for r in rules if r.target_device == "R1").expected_value["routes"]
    assert sorted(r["via_device"] for r in r1_routes if r["network"] == "192.168.2.0") == ["R2", "R3"]
    outcomes, _, _ = _grade(reference, _topology(R1=[(primary, backup + primary)]))
    assert outcomes["R1"].passed
