# tests/test_ospf.py
"""OSPF grading: both config styles (issue #2) and full network coverage (issue #1)."""
from src.app import process_bundle_dict
from src.criteria_generator import generate_criteria_from_topology
from src.evaluator import evaluate_student_submission
from src.models import EvaluationPolicies
from src.ospf import ospf_enablements, statement_covers
from src.parsers import parse_device_bundle


def _router(ospf_lines: str, interface_ospf: str = "") -> dict:
    return {"R1.txt": f"""hostname R1
interface GigabitEthernet0/0
 ip address 10.0.1.1 255.255.255.0
{interface_ospf}
interface GigabitEthernet0/1
 ip address 10.0.2.1 255.255.255.0
{interface_ospf}
interface GigabitEthernet0/2
 ip address 10.0.3.1 255.255.255.0
{interface_ospf}
!
{ospf_lines}
"""}


ALL_THREE = """router ospf 1
 network 10.0.1.0 0.0.0.255 area 0
 network 10.0.2.0 0.0.0.255 area 0
 network 10.0.3.0 0.0.0.255 area 0
"""


def _routing_result(reference: dict, student: dict, policies=None):
    criteria = generate_criteria_from_topology(
        process_bundle_dict(reference), lab_title="OSPF", policies=policies or EvaluationPolicies())
    report = evaluate_student_submission(criteria, process_bundle_dict(student))
    routing = [r for r in report.results if r.category == "routing"]
    assert len(routing) == 1
    return routing[0]


def test_interface_mode_ospf_is_parsed_into_the_normalised_view():
    d = parse_device_bundle(
        "hostname R1\ninterface GigabitEthernet0/0\n ip address 10.0.0.1 255.255.255.0\n ip ospf 1 area 0\n!\n",
        "R1.txt")
    assert ospf_enablements(d) == [{
        "process_id": 1, "interface": "GigabitEthernet0/0", "area": 0, "subnet": "10.0.0.0/24"}]


def test_reference_rule_lists_every_required_network():
    criteria = generate_criteria_from_topology(process_bundle_dict(_router(ALL_THREE)), lab_title="OSPF")
    rule = next(r for r in criteria.rules if r.category == "routing")
    assert sorted(n["subnet"] for n in rule.expected_value["networks"]) == [
        "10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]


def test_one_of_three_networks_does_not_pass():
    student = _router("router ospf 1\n network 10.0.1.0 0.0.0.255 area 0\n")
    result = _routing_result(_router(ALL_THREE), student)
    assert result.passed is False
    assert 0 < result.points_earned < result.points_possible
    assert "10.0.2.0/24" in result.feedback and "10.0.3.0/24" in result.feedback


def test_wildcard_summary_covering_all_networks_passes():
    student = _router("router ospf 1\n network 10.0.0.0 0.0.255.255 area 0\n")
    assert _routing_result(_router(ALL_THREE), student).passed is True


def test_wrong_area_does_not_count():
    student = _router("router ospf 1\n network 10.0.0.0 0.0.255.255 area 1\n")
    result = _routing_result(_router(ALL_THREE), student)
    assert result.passed is False
    assert result.points_earned == 0.0


def test_interface_mode_reference_generates_routing_rules():
    reference = _router("", interface_ospf=" ip ospf 1 area 0")
    criteria = generate_criteria_from_topology(process_bundle_dict(reference), lab_title="OSPF")
    assert any(r.category == "routing" for r in criteria.rules)


def test_interface_mode_student_satisfies_network_statement_reference():
    student = _router("", interface_ospf=" ip ospf 1 area 0")
    assert _routing_result(_router(ALL_THREE), student).passed is True


def test_network_statement_student_satisfies_interface_mode_reference():
    reference = _router("", interface_ospf=" ip ospf 1 area 0")
    assert _routing_result(reference, _router(ALL_THREE)).passed is True


def test_process_id_still_enforced_when_flexibility_is_off():
    strict = EvaluationPolicies(allow_flexible_process_ids=False)
    student = _router("", interface_ospf=" ip ospf 7 area 0")
    assert _routing_result(_router(ALL_THREE), student, strict).passed is False


def test_statement_covers_requires_every_host_bit_to_be_wildcarded():
    assert statement_covers({"network": "10.0.0.0", "wildcard": "0.0.255.255"}, "10.0.2.0/24")
    assert not statement_covers({"network": "10.0.1.0", "wildcard": "0.0.0.255"}, "10.0.2.0/24")
    # a /25 statement does not cover the whole /24
    assert not statement_covers({"network": "10.0.2.0", "wildcard": "0.0.0.127"}, "10.0.2.0/24")
