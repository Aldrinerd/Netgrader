# tests/test_topic_registry.py
"""
The topic registry: every rule category belongs to exactly one topic, and
the detected-only topics are found from explicit configuration only.
"""
import os

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.models import EvaluationRule, ParsedDevice, TopologyResult
from src.parsers import parse_device_bundle
from src.pkt_parser import parse_pkt_file
from src.topics.registry import TOPICS, TOPICS_BY_KEY, detect_topics, topic_for_category
from tests.fixtures import network_bundle

ALL_CATEGORIES = set(EvaluationRule.model_fields["category"].annotation.__args__)
SAMPLE_XML = os.path.join(os.path.dirname(__file__), "fixtures", "sample_topology.xml")


def _device_from(config: str) -> ParsedDevice:
    return parse_device_bundle(config, "D1.txt")


def test_every_rule_category_has_exactly_one_topic():
    owners: dict[str, str] = {}
    for topic in TOPICS:
        for category in topic.categories:
            assert category not in owners, f"{category} owned by {owners[category]} and {topic.key}"
            owners[category] = topic.key
    assert set(owners) == ALL_CATEGORIES


def test_registry_entries_are_well_formed():
    keys = [t.key for t in TOPICS]
    assert len(keys) == len(set(keys))
    for topic in TOPICS:
        if topic.gradeable:
            assert topic.categories, topic.key
        else:
            assert not topic.categories and topic.detect is not None, topic.key


def test_topic_for_category():
    assert topic_for_category("routing").key == "ospf"
    assert topic_for_category("relational_subnet").key == "ip_addressing"
    assert topic_for_category("interface_ip") is TOPICS_BY_KEY["ip_addressing"]


DETECTION_CASES = [
    ("static_routing", "hostname R1\nip route 192.168.2.0 255.255.255.0 10.0.0.2\n"),
    ("stp", "hostname S1\nspanning-tree mode rapid-pvst\n"),
    ("stp", "hostname S1\nspanning-tree vlan 10 priority 4096\n"),
    ("stp", "hostname S1\ninterface FastEthernet0/1\n spanning-tree portfast\n"),
    ("etherchannel", "hostname S1\ninterface FastEthernet0/1\n channel-group 1 mode active\n"),
    ("port_security", "hostname S1\ninterface FastEthernet0/1\n switchport port-security\n"),
    ("hsrp", "hostname R1\ninterface GigabitEthernet0/0\n standby 1 ip 192.168.1.254\n"),
    ("dhcp", "hostname R1\nip dhcp pool LAN\n network 192.168.1.0 255.255.255.0\n"),
    ("dhcp", "hostname R1\ninterface GigabitEthernet0/0\n ip helper-address 10.0.0.5\n"),
    ("inter_vlan_routing", "hostname R1\ninterface GigabitEthernet0/0.10\n encapsulation dot1Q 10\n"),
    ("acl", "hostname R1\naccess-list 10 permit 192.168.1.0 0.0.0.255\n"),
    ("acl", "hostname R1\nip access-list extended BLOCK\n"),
    ("nat", "hostname R1\ninterface GigabitEthernet0/0\n ip nat inside\n"),
    ("ssh", "hostname R1\nip ssh version 2\n"),
    ("ssh", "hostname R1\nline vty 0 4\n transport input ssh\n"),
    ("eigrp", "hostname R1\nrouter eigrp 100\n"),
    ("rip", "hostname R1\nrouter rip\n version 2\n"),
    ("ipv6", "hostname R1\nipv6 unicast-routing\n"),
]


@pytest.mark.parametrize("key,config", DETECTION_CASES)
def test_detector_fires_on_explicit_config(key, config):
    assert TOPICS_BY_KEY[key].detect(_device_from(config))


FACTORY_SWITCH = """hostname Switch
!
spanning-tree mode pvst
spanning-tree extend system-id
!
interface FastEthernet0/1
!
interface Vlan1
 no ip address
 shutdown
!
line con 0
!
line vty 0 4
 login
line vty 5 15
 login
!
end
"""

FACTORY_ROUTER = """hostname Router
!
ip cef
no ipv6 cef
!
interface GigabitEthernet0/0
 no ip address
 duplex auto
 speed auto
 shutdown
!
ip classless
!
ip flow-export version 9
!
line con 0
!
line aux 0
!
line vty 0 4
 login
!
end
"""


@pytest.mark.parametrize("config", [FACTORY_SWITCH, FACTORY_ROUTER])
def test_factory_default_config_detects_nothing(config):
    device = _device_from(config)
    assert [t.key for t in TOPICS if t.detect and t.detect(device)] == []


def test_management_svi_on_layer2_switch_is_not_inter_vlan_routing():
    config = "hostname S1\ninterface Vlan99\n ip address 192.168.99.2 255.255.255.0\nip default-gateway 192.168.99.1\n"
    assert not TOPICS_BY_KEY["inter_vlan_routing"].detect(_device_from(config))


def test_routed_svis_are_inter_vlan_routing():
    config = "hostname MLS1\nip routing\ninterface Vlan10\n ip address 192.168.10.1 255.255.255.0\n"
    assert TOPICS_BY_KEY["inter_vlan_routing"].detect(_device_from(config))


def test_config_lines_are_captured_but_never_serialized():
    device = _device_from("hostname R1\n!\nrouter rip\n")
    assert device.config_lines == ["hostname R1", "!", "router rip"]
    assert "config_lines" not in device.model_dump()
    assert "config_lines" not in device.model_dump_json()


def test_pkt_upload_feeds_detection():
    with open(SAMPLE_XML, "rb") as f:
        devices, links = parse_pkt_file(f.read(), filename="sample_topology.xml")
    found = detect_topics(TopologyResult(devices=devices, links=links, conflicts=[]))
    # Every router in the sample allows `transport input telnet ssh`.
    assert any(name.startswith("Router") for name in found.get("ssh", []))


def test_analyze_response_carries_no_raw_config():
    client = TestClient(app, client=("127.0.0.1", 50000))
    bundle = network_bundle("ospf_clean")
    files = [("files", (name, text.encode("utf-8"), "text/plain")) for name, text in bundle.items()]
    data = client.post("/api/analyze", files=files).json()
    assert data["devices"]
    assert all("config_lines" not in dev for dev in data["devices"].values())
