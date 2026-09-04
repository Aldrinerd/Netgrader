# src/models.py
from typing import Literal
from pydantic import BaseModel, Field

class InterfaceData(BaseModel):
    name: str
    ip_address: str | None = None
    ipv6_address: str | None = None
    subnet_mask: str | None = None
    cidr: int | None = None
    network_address: str | None = None
    admin_status: str = "up"         # up / administratively down
    line_status: str = "up"          # up / down
    is_switchport: bool = False
    switchport_mode: str | None = None  # access / trunk
    access_vlan: int | None = None
    trunk_allowed_vlans: list[int] = Field(default_factory=list)
    trunk_native_vlan: int = 1
    description: str | None = None
    evidence_lines: dict[str, int] = Field(default_factory=dict)


class CDPNeighbor(BaseModel):
    device_id: str
    local_interface: str
    remote_interface: str
    capabilities: list[str] = Field(default_factory=list)
    remote_ip: str | None = None
    platform: str | None = None
    evidence_line: int | None = None

class RouteEntry(BaseModel):
    network: str
    cidr: int
    protocol: str                    # C, S, O, D, etc.
    next_hop: str | None = None
    outgoing_interface: str | None = None
    metric: int | None = None
    evidence_line: int | None = None

class MACTableEntry(BaseModel):
    vlan: int
    mac_address: str
    entry_type: str                  # DYNAMIC / STATIC
    port: str
    evidence_line: int | None = None

class ParsedDevice(BaseModel):
    hostname: str
    canonical_name: str
    display_name: str = ""
    is_placeholder: bool = False
    placeholder_for_device: str | None = None
    placeholder_for_interface: str | None = None
    device_type: Literal["router", "switch", "l3_switch", "host", "unknown"] = "router"
    raw_filename: str = ""
    interfaces: dict[str, InterfaceData] = Field(default_factory=dict)
    cdp_neighbors: list[CDPNeighbor] = Field(default_factory=list)
    routes: list[RouteEntry] = Field(default_factory=list)
    mac_table: list[MACTableEntry] = Field(default_factory=list)
    vlans: dict[int, str] = Field(default_factory=dict)

class ContributingSignal(BaseModel):
    signal_type: str
    description: str
    weight: float
    evidence: list[str] = Field(default_factory=list)

class DiscoveredLink(BaseModel):
    source_device: str
    source_interface: str
    target_device: str
    target_interface: str
    confidence: float
    classification: Literal["verified", "inferred", "unverified"]
    signals: list[ContributingSignal] = Field(default_factory=list)
    is_bidirectional: bool = True
    conflicts: list[str] = Field(default_factory=list)

class ConflictIssue(BaseModel):
    severity: Literal["error", "warning", "info"]
    category: str
    title: str
    description: str
    involved_devices: list[str] = Field(default_factory=list)
    involved_interfaces: list[str] = Field(default_factory=list)
    evidence_citations: list[str] = Field(default_factory=list)

class TopologyResult(BaseModel):
    devices: dict[str, ParsedDevice] = Field(default_factory=dict)
    links: list[DiscoveredLink] = Field(default_factory=list)
    conflicts: list[ConflictIssue] = Field(default_factory=list)
