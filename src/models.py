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

    # --- Interface-level protocol settings (link-agreement Phase 2) ---
    # All optional: an unset value means the IOS default, which the link
    # attribute registry supplies. None here means "not written in the
    # config", not "no value in effect".
    ospf_hello_interval: int | None = None
    ospf_dead_interval: int | None = None
    ospf_area: int | None = None
    ospf_network_type: str | None = None      # broadcast / point-to-point / ...
    ospf_authentication: str | None = None    # message-digest / text / null
    mtu: int | None = None
    speed: str | None = None                  # auto / 10 / 100 / 1000
    duplex: str | None = None                 # auto / full / half
    channel_group: int | None = None
    channel_group_mode: str | None = None     # active / passive / on / desirable / auto
    encapsulation: str | None = None          # ppp / hdlc / frame-relay
    clock_rate: int | None = None

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
    x_coord: float | None = None
    y_coord: float | None = None
    default_gateway: str | None = None
    has_enable_secret: bool = False
    has_password_encryption: bool = False
    has_vty_login: bool = False
    has_ip_routing: bool = False
    hardware_model: str = ""
    ospf_processes: list[dict] = Field(default_factory=list)
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
    cable_type: str | None = None
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


# --- Evaluation & Policy Models ---
class EvaluationPolicies(BaseModel):
    # IP & Subnetting Policies
    allow_dynamic_subnetting: bool = False      # If True: verifies mutual subnet matching, CIDR & uniqueness rather than exact IP
    enforce_prefix_length: bool = True          # If True: requires student's custom subnet to match required CIDR (e.g. /30 for P2P, /24 for LAN)
    verify_default_gateways: bool = True        # If True: verifies PCs/Switches have default gateway matching connected router subnet

    # Topology & Hardware Policies
    allow_custom_hostnames: bool = False        # If True: matches devices by type, topological role, and neighbor links
    strict_port_matching: bool = True           # If False: allows equivalent interfaces of same speed class
    strict_cable_type: bool = True              # If False: allows Auto-MDIX copper equivalence (Straight-Through vs Cross-Over)

    # Routing, Security & Documentation Policies
    allow_flexible_process_ids: bool = True     # If True: ignores locally-significant OSPF/EIGRP process IDs; checks Area & networks
    grade_security_baseline: bool = False       # If True: checks 'enable secret', 'service password-encryption', 'line vty'
    grade_interface_descriptions: bool = False  # If True: checks descriptive interface labels matching peer

    # Link Agreement Policies
    # If False (default): both ends of a link need only agree with EACH OTHER.
    # A trunk whose two ends both use native VLAN 999 works, whatever the
    # instructor's own file used. If True: the agreed value must also equal the
    # reference, for labs where the instructor dictated exact values.
    enforce_reference_link_values: bool = False


class EvaluationRule(BaseModel):
    rule_id: str
    category: Literal[
        "device",
        "interface_ip",
        "interface_status",
        "cabling",
        "vlan_trunk",
        "routing",
        "relational_subnet",
        "link_agreement",
        "gateway",
        "security",
        "documentation"
    ]
    description: str
    points: float = 10.0
    target_device: str
    target_interface: str | None = None
    expected_value: dict | str | int | float | None = None


class EvaluationCriteria(BaseModel):
    lab_title: str = "Packet Tracer Lab Assignment"
    lab_description: str = ""
    total_points: float = 100.0
    policies: EvaluationPolicies = Field(default_factory=EvaluationPolicies)
    rules: list[EvaluationRule] = Field(default_factory=list)
    reference_summary: dict = Field(default_factory=dict)


class RuleResult(BaseModel):
    rule_id: str
    category: str
    description: str
    points_possible: float
    points_earned: float
    passed: bool
    actual_value: str | None = None
    feedback: str
    target_device: str
    target_interface: str | None = None
    # Why the requirement exists and how to satisfy it. Populated for failed
    # checkpoints only. Deterministic: see src/feedback.py.
    guidance: str | None = None


class StudyTopic(BaseModel):
    """A concept to revisit, ranked by how many points it cost."""
    topic: str
    why_it_matters: str
    points_lost: float
    checkpoints_failed: int


class EvaluationReport(BaseModel):
    lab_title: str
    total_score: float
    max_score: float
    percentage: float
    passed_count: int
    failed_count: int
    grade_letter: str
    results: list[RuleResult] = Field(default_factory=list)
    study_topics: list[StudyTopic] = Field(default_factory=list)
    topology: TopologyResult

