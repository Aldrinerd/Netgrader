# tests/test_criteria_generator.py
import os
import re

import pytest
from src.criteria_generator import (
    format_criteria_to_instructions_txt,
    generate_criteria_from_topology,
    parse_instructions_txt,
)
from src.pkt_parser import parse_pkt_file
from tests.fixtures import network_bundle
from src.models import EvaluationPolicies, TopologyResult
from src.app import process_bundle_dict


def test_generate_criteria_from_pt_xml():
    xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "fixtures", "sample_topology.xml")
    if not os.path.exists(xml_path):
        pytest.skip("sample_topology.xml not available")

    with open(xml_path, "rb") as f:
        devs, lnks = parse_pkt_file(f.read(), filename="sample_topology.xml")

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
    bundle = network_bundle("ospf_clean")
    top = process_bundle_dict(bundle)

    criteria = generate_criteria_from_topology(top, lab_title="OSPF Ring Lab")
    assert len(criteria.rules) >= 6

    # IP rules should exist for 10.0.0.1, 10.0.0.5, etc.
    ip_rules = [r for r in criteria.rules if r.category == "interface_ip"]
    assert len(ip_rules) > 0

    txt = format_criteria_to_instructions_txt(criteria)
    parsed = parse_instructions_txt(txt)
    assert parsed.lab_title == "OSPF Ring Lab"


def test_parse_invalid_instructions_txt():
    with pytest.raises(ValueError, match="Instructions document is empty"):
        parse_instructions_txt("")

    with pytest.raises(ValueError, match="Missing '--- CRITERIA SPEC START ---'"):
        parse_instructions_txt("This is just a random text file with no spec block.")


def test_generate_criteria_with_dynamic_subnetting_policy():
    from src.models import EvaluationPolicies
    bundle = network_bundle("ospf_clean")
    top = process_bundle_dict(bundle)
    
    policies = EvaluationPolicies(
        allow_dynamic_subnetting=True,
        enforce_prefix_length=True,
        allow_flexible_process_ids=True
    )
    criteria = generate_criteria_from_topology(
        top,
        lab_title="Dynamic OSPF Challenge",
        policies=policies
    )
    assert criteria.policies.allow_dynamic_subnetting is True
    
    # Check that relational_subnet rules were generated instead of static interface_ip rules for connected links
    rel_rules = [r for r in criteria.rules if r.category == "relational_subnet"]
    assert len(rel_rules) > 0
    assert rel_rules[0].expected_value.get("link_type") == "point_to_point" or "expected_prefixlen" in rel_rules[0].expected_value
    
    # Format and verify instructions text
    txt = format_criteria_to_instructions_txt(criteria)
    assert "Dynamic Subnetting" in txt
    assert "DYNAMIC & RELATIONAL SUBNETTING POLICY" in txt or "Relational Subnet" in txt
    
    # Parse back
    parsed = parse_instructions_txt(txt)
    assert parsed.policies.allow_dynamic_subnetting is True
    assert parsed.policies.enforce_prefix_length is True
    assert len(parsed.rules) == len(criteria.rules)


def test_generate_criteria_with_security_and_description_policies():
    from src.models import EvaluationPolicies
    bundle = network_bundle("ospf_clean")
    top = process_bundle_dict(bundle)
    
    policies = EvaluationPolicies(
        grade_security_baseline=True,
        grade_interface_descriptions=True
    )
    criteria = generate_criteria_from_topology(
        top,
        lab_title="Hardened OSPF Network",
        policies=policies
    )
    assert criteria.policies.grade_security_baseline is True
    assert criteria.policies.grade_interface_descriptions is True
    
    sec_rules = [r for r in criteria.rules if r.category == "security"]
    assert len(sec_rules) >= 3  # enable_secret, password_encryption, vty_login


def _static_chain():
    return process_bundle_dict(network_bundle("static_chain"))


def _cabling_at_zero():
    defaults = generate_criteria_from_topology(_static_chain()).topic_weights
    weights = dict(defaults)
    weights["static_routing"] = round(weights["static_routing"] + weights["cabling"], 1)
    weights["cabling"] = 0.0
    return generate_criteria_from_topology(_static_chain(), topic_weights=weights)


def test_instructions_show_grading_weights():
    criteria = generate_criteria_from_topology(_static_chain(), lab_title="Static Lab")
    txt = format_criteria_to_instructions_txt(criteria)
    assert "3. GRADING WEIGHTS" in txt
    pct = criteria.topic_weights["static_routing"]
    assert re.search(rf"Static Routing\s+\|\s+{pct:.1f} %", txt)


def test_section_numbers_are_consecutive():
    txt = format_criteria_to_instructions_txt(_cabling_at_zero())
    numbers = [int(n) for n in re.findall(r"^(\d+)\. [A-Z]", txt, re.MULTILINE)]
    assert numbers == list(range(1, len(numbers) + 1))
    assert len(numbers) >= 6


def test_static_routing_section_in_both_addressing_modes():
    txt = format_criteria_to_instructions_txt(generate_criteria_from_topology(_static_chain()))
    assert "STATIC ROUTING REQUIREMENTS" in txt
    assert re.search(r"R1\s+\|\s+192\.168\.2\.0/24\s+\|\s+R2", txt)
    assert re.search(r"R2\s+\|\s+default route \(0\.0\.0\.0/0\)\s+\|\s+R1", txt)
    dynamic = format_criteria_to_instructions_txt(generate_criteria_from_topology(
        _static_chain(), policies=EvaluationPolicies(allow_dynamic_subnetting=True)))
    assert re.search(r"R1\s+\|\s+the LAN on R2 GigabitEthernet0/1 \(/24\)\s+\|\s+R2", dynamic)


def test_unmappable_summary_is_explained_under_dynamic_subnetting():
    bundle = network_bundle("static_chain")
    anchor = "ip route 192.168.3.0 255.255.255.0 GigabitEthernet0/1\n"
    bundle["R1.txt"] = bundle["R1.txt"].replace(anchor, anchor + "ip route 172.16.0.0 255.240.0.0 10.0.12.2\n")
    txt = format_criteria_to_instructions_txt(generate_criteria_from_topology(
        process_bundle_dict(bundle), policies=EvaluationPolicies(allow_dynamic_subnetting=True)))
    assert "172.16.0.0/12 summary, any static route via R2 accepted" in txt


def test_zero_weight_sections_are_marked_reference_only():
    criteria = _cabling_at_zero()
    txt = format_criteria_to_instructions_txt(criteria)
    assert "PHYSICAL CABLING & PORT CONNECTIONS (REFERENCE ONLY, NOT GRADED)" in txt
    assert re.search(r"Cabling\s+\|\s+0\.0 % \| reference only, not graded", txt)
    rubric = txt.split("RUBRIC & POINT BREAKDOWN")[1].split("DO NOT MODIFY")[0]
    graded_part, reference_part = rubric.split("REFERENCE ONLY (NOT GRADED)")
    assert "Cable connection between R1" not in graded_part
    assert "Cable connection between R1" in reference_part
    assert f"Total Checkpoints: {sum(r.graded for r in criteria.rules)} items" in txt


def test_rubric_is_grouped_by_topic_with_subtotals():
    criteria = generate_criteria_from_topology(_static_chain())
    txt = format_criteria_to_instructions_txt(criteria)
    static_points = sum(r.points for r in criteria.rules if r.category == "static_route")
    assert f"Static Routing ({static_points:.1f} pts)" in txt


def test_weights_and_graded_flags_survive_the_round_trip():
    criteria = _cabling_at_zero()
    parsed = parse_instructions_txt(format_criteria_to_instructions_txt(criteria))
    assert parsed.topic_weights == criteria.topic_weights
    assert [r.graded for r in parsed.rules] == [r.graded for r in criteria.rules]


def test_rubric_without_topic_weights_has_no_weights_section():
    criteria = generate_criteria_from_topology(_static_chain())
    criteria.topic_weights = {}
    assert "GRADING WEIGHTS" not in format_criteria_to_instructions_txt(criteria)
