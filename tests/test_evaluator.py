# tests/test_evaluator.py
import pytest
from src.criteria_generator import generate_criteria_from_topology
from src.evaluator import evaluate_student_submission
from src.presets import load_preset
from src.app import process_bundle_dict


def test_evaluate_perfect_submission():
    bundle = load_preset("ospf_clean")
    top = process_bundle_dict(bundle)
    criteria = generate_criteria_from_topology(top, lab_title="Perfect OSPF Submission")

    report = evaluate_student_submission(criteria, top)

    assert report.total_score == criteria.total_points
    assert report.percentage == 100.0
    assert report.grade_letter in ("A", "A+")
    assert report.failed_count == 0
    assert report.passed_count == len(criteria.rules)

    for res in report.results:
        assert res.passed is True
        assert res.points_earned == res.points_possible


def test_evaluate_flawed_submission():
    # Instructor reference: OSPF Clean
    clean_top = process_bundle_dict(load_preset("ospf_clean"))
    criteria = generate_criteria_from_topology(clean_top, lab_title="OSPF Challenge")

    # Student submission: Scenario 2 (has R1 and R2 with wrong subnets and missing R3)
    flawed_top = process_bundle_dict(load_preset("subnet_cabling_error"))

    report = evaluate_student_submission(criteria, flawed_top)

    assert report.percentage < 100.0
    assert report.failed_count > 0

    # R3 was missing in student submission
    r3_results = [r for r in report.results if r.target_device == "R3"]
    assert any(not r.passed for r in r3_results)
    assert any("not found" in r.feedback.lower() for r in r3_results)


def test_evaluate_vlan_mismatch_submission():
    clean_sw = process_bundle_dict(load_preset("vlan_trunk_mismatch"))
    criteria = generate_criteria_from_topology(clean_sw, lab_title="VLAN Lab")

    report = evaluate_student_submission(criteria, clean_sw)
    assert report.total_score > 0


def test_dynamic_subnetting_valid_custom_ip_scheme():
    from src.models import EvaluationPolicies
    ref_top = process_bundle_dict(load_preset("ospf_clean"))
    policies = EvaluationPolicies(
        allow_dynamic_subnetting=True,
        enforce_prefix_length=True,
        verify_default_gateways=True
    )
    criteria = generate_criteria_from_topology(ref_top, lab_title="Dynamic Subnetting Lab", policies=policies)
    
    # Student submission uses completely different IP scheme: 172.16.0.0/30 instead of 10.0.0.0/30
    student_bundle = {
        "R1.txt": """hostname R1
interface GigabitEthernet0/0
 ip address 172.16.0.1 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 172.16.0.5 255.255.255.252
 no shutdown
interface GigabitEthernet0/2
 ip address 172.16.10.1 255.255.255.0
 no shutdown
show cdp neighbors detail
Device ID: R2
Interface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet0/0
Device ID: R3
Interface: GigabitEthernet0/1, Port ID (outgoing port): GigabitEthernet0/0
""",
        "R2.txt": """hostname R2
interface GigabitEthernet0/0
 ip address 172.16.0.2 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 172.16.0.9 255.255.255.252
 no shutdown
interface GigabitEthernet0/2
 ip address 172.16.20.1 255.255.255.0
 no shutdown
show cdp neighbors detail
Device ID: R1
Interface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet0/0
Device ID: R3
Interface: GigabitEthernet0/1, Port ID (outgoing port): GigabitEthernet0/1
""",
        "R3.txt": """hostname R3
interface GigabitEthernet0/0
 ip address 172.16.0.6 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 172.16.0.10 255.255.255.252
 no shutdown
interface GigabitEthernet0/2
 ip address 172.16.30.1 255.255.255.0
 no shutdown
show cdp neighbors detail
Device ID: R1
Interface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet0/1
Device ID: R2
Interface: GigabitEthernet0/1, Port ID (outgoing port): GigabitEthernet0/1
"""
    }
    student_top = process_bundle_dict(student_bundle)
    report = evaluate_student_submission(criteria, student_top)
    
    assert report.percentage == 100.0
    assert report.grade_letter in ("A", "A+")
    assert report.failed_count == 0
    rel_results = [r for r in report.results if r.category == "relational_subnet"]
    assert len(rel_results) > 0
    for r in rel_results:
        assert r.passed is True
        assert "subnet" in r.feedback.lower()


def test_dynamic_subnetting_mismatched_subnet_pair():
    from src.models import EvaluationPolicies
    ref_top = process_bundle_dict(load_preset("ospf_clean"))
    policies = EvaluationPolicies(allow_dynamic_subnetting=True)
    criteria = generate_criteria_from_topology(ref_top, lab_title="Dynamic Subnetting Lab", policies=policies)
    
    flawed_bundle = {
        "R1.txt": """hostname R1
interface GigabitEthernet0/0
 ip address 172.16.0.1 255.255.255.252
 no shutdown
show cdp neighbors detail
Device ID: R2
Interface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet0/0
""",
        "R2.txt": """hostname R2
interface GigabitEthernet0/0
 ip address 172.16.1.2 255.255.255.252
 no shutdown
show cdp neighbors detail
Device ID: R1
Interface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet0/0
"""
    }
    student_top = process_bundle_dict(flawed_bundle)
    report = evaluate_student_submission(criteria, student_top)
    
    r1_r2_rel = [r for r in report.results if r.category == "relational_subnet" and "r1" in r.rule_id and "r2" in r.rule_id]
    assert len(r1_r2_rel) > 0
    assert r1_r2_rel[0].passed is False
    assert "different subnets" in r1_r2_rel[0].feedback.lower() or "mismatch" in r1_r2_rel[0].feedback.lower()


def test_flexible_hostnames_matching():
    from src.models import EvaluationPolicies
    ref_top = process_bundle_dict(load_preset("ospf_clean"))
    policies = EvaluationPolicies(
        allow_custom_hostnames=True,
        allow_dynamic_subnetting=True
    )
    criteria = generate_criteria_from_topology(ref_top, lab_title="Custom Hostnames Lab", policies=policies)
    
    custom_bundle = {
        "Router_East.txt": """hostname Router_East
interface GigabitEthernet0/0
 ip address 10.0.0.1 255.255.255.252
 no shutdown
show cdp neighbors detail
Device ID: Router_Central
Interface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet0/0
""",
        "Router_Central.txt": """hostname Router_Central
interface GigabitEthernet0/0
 ip address 10.0.0.2 255.255.255.252
 no shutdown
show cdp neighbors detail
Device ID: Router_East
Interface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet0/0
"""
    }
    student_top = process_bundle_dict(custom_bundle)
    report = evaluate_student_submission(criteria, student_top)
    r1_dev_rule = [r for r in report.results if r.target_device == "R1" and r.category == "device"][0]
    assert r1_dev_rule.passed is True
    assert "Matched by topological role" in r1_dev_rule.feedback or "matched" in r1_dev_rule.feedback.lower()


def test_automdix_cabling_tolerance():
    from src.models import EvaluationPolicies
    clean_top = process_bundle_dict(load_preset("ospf_clean"))
    policies = EvaluationPolicies(strict_cable_type=False)
    criteria = generate_criteria_from_topology(clean_top, lab_title="Cabling Tolerance", policies=policies)
    
    flawed_top = process_bundle_dict(load_preset("ospf_clean"))
    for l in flawed_top.links:
        l.conflicts.append("Cable type mismatch: Straight-Through used instead of Cross-Over")
    
    report = evaluate_student_submission(criteria, flawed_top)
    cabling_results = [r for r in report.results if r.category == "cabling"]
    for r in cabling_results:
        assert r.passed is True
        assert "Auto-MDIX" in r.feedback or "accepted" in r.feedback.lower()


def test_flexible_ospf_process_ids():
    from src.models import EvaluationPolicies, EvaluationRule
    ref_top = process_bundle_dict(load_preset("ospf_clean"))
    policies = EvaluationPolicies(allow_flexible_process_ids=True)
    criteria = generate_criteria_from_topology(ref_top, lab_title="OSPF Process ID Lab", policies=policies)
    
    criteria.rules.append(EvaluationRule(
        rule_id="ospf_area0_r1",
        category="routing",
        description="Configure OSPF Area 0 routing on R1",
        points=10.0,
        target_device="R1",
        expected_value={"protocol": "ospf", "process_id": 1, "area": 0, "network": "10.0.0.0"}
    ))
    
    student_bundle = {
        "R1.txt": """hostname R1
interface GigabitEthernet0/0
 ip address 10.0.0.1 255.255.255.252
router ospf 99
 network 10.0.0.0 0.0.0.3 area 0
"""
    }
    student_top = process_bundle_dict(student_bundle)
    report = evaluate_student_submission(criteria, student_top)
    ospf_res = [r for r in report.results if r.rule_id == "ospf_area0_r1"][0]
    assert ospf_res.passed is True
    assert "process ID 99 accepted" in ospf_res.feedback
