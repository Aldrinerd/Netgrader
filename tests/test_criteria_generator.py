# tests/test_criteria_generator.py
import os
import pytest
from src.criteria_generator import (
    format_criteria_to_instructions_txt,
    generate_criteria_from_topology,
    parse_instructions_txt,
)
from src.pkt_parser import parse_pkt_file
from src.presets import load_preset
from src.models import TopologyResult
from src.app import process_bundle_dict


def test_generate_criteria_from_pt_xml():
    xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cisco-pka-to-xml", "trial.xml")
    if not os.path.exists(xml_path):
        pytest.skip("trial.xml not available")

    with open(xml_path, "rb") as f:
        devs, lnks = parse_pkt_file(f.read(), filename="trial.xml")

    top = TopologyResult(devices=devs, links=lnks, conflicts=[])
    criteria = generate_criteria_from_topology(
        topology=top,
        lab_title="CCNA Enterprise Topology Lab",
        lab_description="Configure Multi-Tier Routing and Switching",
        target_total_points=100.0
    )

    assert criteria.lab_title == "CCNA Enterprise Topology Lab"
    assert criteria.total_points == 100.0
    assert len(criteria.rules) > 5

    # Check total points sum
    total_pts = sum(r.points for r in criteria.rules)
    assert abs(total_pts - 100.0) < 0.2

    # Check rule categories present
    categories = {r.category for r in criteria.rules}
    assert "device" in categories
    assert "cabling" in categories

    # Test formatting to instructions.txt
    txt = format_criteria_to_instructions_txt(criteria)
    assert "CCNA Enterprise Topology Lab" in txt
    assert "--- CRITERIA SPEC START ---" in txt
    assert "--- CRITERIA SPEC END ---" in txt

    # Test parsing back
    parsed_crit = parse_instructions_txt(txt)
    assert parsed_crit.lab_title == criteria.lab_title
    assert len(parsed_crit.rules) == len(criteria.rules)
    assert parsed_crit.total_points == criteria.total_points


def test_generate_criteria_from_ospf_preset():
    bundle = load_preset("ospf_clean")
    top = process_bundle_dict(bundle)

    criteria = generate_criteria_from_topology(top, lab_title="OSPF Ring Lab")
    assert len(criteria.rules) >= 6

    # IP rules should exist for 10.0.0.1, 10.0.0.5, etc.
    ip_rules = [r for r in criteria.rules if r.category == "interface_ip"]
    assert len(ip_rules) > 0

    txt = format_criteria_to_instructions_txt(criteria)
    parsed = parse_instructions_txt(txt)
    assert parsed.lab_title == "OSPF Ring Lab"


def test_generate_criteria_with_dynamic_policies():
    from src.models import EvaluationPolicies
    bundle = load_preset("ospf_clean")
    top = process_bundle_dict(bundle)

    policies = EvaluationPolicies(
        allow_dynamic_subnetting=True,
        enforce_prefix_length=True,
        allow_custom_hostnames=True,
        strict_cable_type=False,
        grade_security_baseline=True,
        grade_interface_descriptions=True,
    )

    criteria = generate_criteria_from_topology(
        top,
        lab_title="Dynamic Subnetting & OSPF Lab",
        policies=policies,
    )

    assert criteria.policies.allow_dynamic_subnetting is True
    assert criteria.policies.allow_custom_hostnames is True

    # Relational subnet rules should be present
    subnet_rules = [r for r in criteria.rules if r.category == "relational_subnet"]
    assert len(subnet_rules) > 0

    # Instructions text formatting should include policy summary
    txt = format_criteria_to_instructions_txt(criteria)
    assert "Dynamic Subnetting" in txt
    assert "Custom Hostnames" in txt or "Custom /" in txt
    assert "--- CRITERIA SPEC START ---" in txt

    # Parse back and verify policies preserved
    parsed = parse_instructions_txt(txt)
    assert parsed.policies.allow_dynamic_subnetting is True
    assert parsed.policies.strict_cable_type is False
    assert parsed.policies.grade_security_baseline is True
