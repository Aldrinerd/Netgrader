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


def test_evaluate_dynamic_subnetting_success():
    from src.models import EvaluationPolicies
    from src.criteria_generator import generate_criteria_from_topology

    # Instructor reference: R1-R2 on 192.168.1.0/30
    ref_r1 = "hostname R1\ninterface Gi0/0\n ip address 192.168.1.1 255.255.255.252\n no shutdown\n"
    ref_r2 = "hostname R2\ninterface Gi0/0\n ip address 192.168.1.2 255.255.255.252\n no shutdown\n"
    ref_top = process_bundle_dict({"R1.txt": ref_r1, "R2.txt": ref_r2})

    policies = EvaluationPolicies(
        allow_dynamic_subnetting=True,
        enforce_prefix_length=True
    )
    criteria = generate_criteria_from_topology(ref_top, lab_title="Dynamic Subnet Lab", policies=policies)

    # Student submission: R1-R2 on custom 10.99.5.0/30 (10.99.5.1 and 10.99.5.2)
    stu_r1 = "hostname R1\ninterface Gi0/0\n ip address 10.99.5.1 255.255.255.252\n no shutdown\n"
    stu_r2 = "hostname R2\ninterface Gi0/0\n ip address 10.99.5.2 255.255.255.252\n no shutdown\n"
    stu_top = process_bundle_dict({"R1.txt": stu_r1, "R2.txt": stu_r2})

    report = evaluate_student_submission(criteria, stu_top)
    assert report.total_score == criteria.total_points
    assert report.percentage == 100.0
    assert report.passed_count == len(criteria.rules)
    assert report.failed_count == 0


def test_evaluate_dynamic_subnetting_mismatch():
    from src.models import EvaluationPolicies
    from src.criteria_generator import generate_criteria_from_topology

    ref_r1 = "hostname R1\ninterface Gi0/0\n ip address 192.168.1.1 255.255.255.252\n no shutdown\n"
    ref_r2 = "hostname R2\ninterface Gi0/0\n ip address 192.168.1.2 255.255.255.252\n no shutdown\n"
    ref_top = process_bundle_dict({"R1.txt": ref_r1, "R2.txt": ref_r2})

    policies = EvaluationPolicies(allow_dynamic_subnetting=True)
    criteria = generate_criteria_from_topology(ref_top, lab_title="Dynamic Subnet Lab", policies=policies)

    # Student submission: R1 is on 10.1.1.1/30 and R2 is on 10.2.2.2/30 (Subnet Mismatch)
    stu_r1 = "hostname R1\ninterface Gi0/0\n ip address 10.1.1.1 255.255.255.252\n no shutdown\n"
    stu_r2 = "hostname R2\ninterface Gi0/0\n ip address 10.2.2.2 255.255.255.252\n no shutdown\n"
    stu_top = process_bundle_dict({"R1.txt": stu_r1, "R2.txt": stu_r2})

    report = evaluate_student_submission(criteria, stu_top)
    assert report.percentage < 100.0
    assert report.failed_count > 0

    sub_res = [r for r in report.results if r.category == "relational_subnet"]
    assert any("mismatch" in r.feedback.lower() for r in sub_res)


def test_evaluate_dynamic_subnetting_prefix_violation():
    from src.models import EvaluationPolicies
    from src.criteria_generator import generate_criteria_from_topology

    ref_r1 = "hostname R1\ninterface Gi0/0\n ip address 192.168.1.1 255.255.255.252\n no shutdown\n"
    ref_r2 = "hostname R2\ninterface Gi0/0\n ip address 192.168.1.2 255.255.255.252\n no shutdown\n"
    ref_top = process_bundle_dict({"R1.txt": ref_r1, "R2.txt": ref_r2})

    # Enforce /30 prefix
    policies = EvaluationPolicies(allow_dynamic_subnetting=True, enforce_prefix_length=True)
    criteria = generate_criteria_from_topology(ref_top, lab_title="Dynamic Subnet Lab", policies=policies)

    # Student configured matching subnet, but used /24 instead of /30
    stu_r1 = "hostname R1\ninterface Gi0/0\n ip address 10.1.1.1 255.255.255.0\n no shutdown\n"
    stu_r2 = "hostname R2\ninterface Gi0/0\n ip address 10.1.1.2 255.255.255.0\n no shutdown\n"
    stu_top = process_bundle_dict({"R1.txt": stu_r1, "R2.txt": stu_r2})

def test_evaluate_flexible_hostnames():
    from src.models import EvaluationPolicies
    from src.criteria_generator import generate_criteria_from_topology

    ref_r1 = "hostname R1\ninterface Gi0/0\n ip address 10.1.1.1 255.255.255.252\n no shutdown\n"
    ref_r2 = "hostname R2\ninterface Gi0/0\n ip address 10.1.1.2 255.255.255.252\n no shutdown\n"
    ref_top = process_bundle_dict({"R1.txt": ref_r1, "R2.txt": ref_r2})

    policies = EvaluationPolicies(allow_custom_hostnames=True, allow_dynamic_subnetting=True)
    criteria = generate_criteria_from_topology(ref_top, lab_title="Flexible Hostname Lab", policies=policies)

    # Student named routers Router_East and Router_West
    stu_r1 = "hostname Router_East\ninterface Gi0/0\n ip address 10.1.1.1 255.255.255.252\n no shutdown\n"
    stu_r2 = "hostname Router_West\ninterface Gi0/0\n ip address 10.1.1.2 255.255.255.252\n no shutdown\n"
    stu_top = process_bundle_dict({"East.txt": stu_r1, "West.txt": stu_r2})

    report = evaluate_student_submission(criteria, stu_top)
    assert report.total_score == criteria.total_points
    assert report.percentage == 100.0


def test_evaluate_cable_tolerance_auto_mdix():
    from src.models import EvaluationPolicies
    from src.criteria_generator import generate_criteria_from_topology

    clean_top = process_bundle_dict(load_preset("subnet_cabling_error"))
    # In subnet_cabling_error, R1 and R2 have a cabling conflict
    policies = EvaluationPolicies(strict_cable_type=False)
    criteria = generate_criteria_from_topology(clean_top, lab_title="Auto-MDIX Lab", policies=policies)

    report = evaluate_student_submission(criteria, clean_top)
    cabling_res = [r for r in report.results if r.category == "cabling"]
    # With strict_cable_type=False, cabling should pass despite conflict
    assert all(r.passed for r in cabling_res)
