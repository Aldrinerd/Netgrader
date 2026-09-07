# tests/test_pkt_parser.py
import os
import pytest
from src.pkt_parser import parse_pkt_xml, parse_pkt_file

TRIAL_XML_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cisco-pka-to-xml", "trial.xml")

def test_parse_trial_xml():
    assert os.path.exists(TRIAL_XML_PATH), "trial.xml should exist"
    with open(TRIAL_XML_PATH, "rb") as f:
        xml_bytes = f.read()
    
    devices, links = parse_pkt_xml(xml_bytes, filename="trial.xml")
    
    # Verify routers, switches, laptops are parsed
    assert "Router1" in devices
    assert "Switch2" in devices
    assert "L1" in devices
    assert "L2" in devices
    
    # Check device types
    assert devices["Router1"].device_type == "router"
    assert devices["Switch2"].device_type == "switch"
    assert devices["L1"].device_type == "host"
    
    # Check coordinates
    assert devices["L1"].x_coord is not None
    assert devices["L1"].y_coord is not None
    
    # Check router interfaces extracted from running-config
    assert "FastEthernet0/0" in devices["Router1"].interfaces
    assert "FastEthernet0/1" in devices["Router1"].interfaces
    
    # Check links
    assert len(links) >= 10
    
    # Find link between Switch2 and L1
    sw_l1_link = next((l for l in links if (l.source_device == "Switch2" and l.target_device == "L1") or (l.source_device == "L1" and l.target_device == "Switch2")), None)
    assert sw_l1_link is not None
    assert sw_l1_link.confidence == 1.0
    assert sw_l1_link.classification == "verified"
    assert sw_l1_link.cable_type == "eStraightThrough"

def test_parse_pkt_file_wrapper_with_xml():
    with open(TRIAL_XML_PATH, "rb") as f:
        xml_bytes = f.read()
    
    devices, links = parse_pkt_file(xml_bytes, filename="sample.xml")
    assert len(devices) >= 10
    assert len(links) >= 10

def test_parse_pkt_invalid_xml():
    with pytest.raises(ValueError, match="Malformed Packet Tracer XML"):
        parse_pkt_xml(b"<PACKETTRACER5><UNCLOSED>", filename="bad.xml")
