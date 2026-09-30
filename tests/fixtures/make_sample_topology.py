"""
Generate tests/fixtures/sample_topology.xml, a synthetic Packet Tracer file.

Why synthetic: the tests previously used a real class activity file, which
contained the finished configuration (the answer key) and an author's profile
name. This topology is invented for the tests, so it is safe to publish.

It mirrors the structure of a decrypted .pkt: DEVICES with ENGINE / RUNNINGCONFIG
/ WORKSPACE coordinates, host PORTs with IP settings, LINKS keyed by
SAVE_REF_ID with real cable types, plus root-level NOTES and ELLIPSES for the
annotation work in issue #14.

    python tests/fixtures/make_sample_topology.py

Topology (all addressing invented, 172.20.0.0/16):

    L1, L2 -- Switch2 -- Router1 -- Router2 -- Router3 -- Router4 -- Router5 -- Switch3 -- PC1, PC2, Server0
              172.20.10.0/24       /30 point-to-point links, OSPF area 0           172.20.20.0/24
"""
import os
from xml.sax.saxutils import escape

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_topology.xml")

ENABLE = "enable secret 5 $1$fx7Q$Wm1dVq3ZsKp0cH9rTn2Lb."
VTY = ["line vty 0 4", " exec-timeout 10 0", " password 7 0822455D0A16", " login", " transport input telnet ssh", "!"]


def router_config(name, interfaces, ospf_networks):
    lines = ["!", "version 12.4", "service password-encryption", "!", f"hostname {name}", "!", ENABLE, "!"]
    for intf, desc, ip, mask in interfaces:
        lines += [f"interface {intf}", f" description {desc}", f" ip address {ip} {mask}",
                  " duplex auto", " speed auto", "!"]
    lines += ["interface Vlan1", " no ip address", " shutdown", "!", "router ospf 10",
              f" router-id 1.1.1.{name[-1]}", " log-adjacency-changes"]
    lines += [f" network {net} {wild} area 0" for net, wild in ospf_networks]
    lines += ["!", "ip classless", "!", "line con 0", "!"] + VTY + ["end"]
    return lines


def switch_config(name, access_ports, uplink, gateway):
    lines = ["!", "version 12.2", "service password-encryption", "!", f"hostname {name}", "!", ENABLE, "!"]
    for port in access_ports:
        lines += [f"interface {port}", " switchport access vlan 1", " switchport mode access", "!"]
    lines += [f"interface {uplink}", " description Uplink to router", "!",
              "interface Vlan1", " no ip address", " shutdown", "!",
              f"ip default-gateway {gateway}", "!", "line con 0", "!"] + VTY + ["end"]
    return lines


# name, PT type, model, x, y, running-config lines (routers/switches) or host port settings
ROUTERS = {
    "Router1": ([("FastEthernet0/0", "LAN Switch2", "172.20.10.1", "255.255.255.0"),
                 ("FastEthernet0/1", "Link to Router2", "172.20.0.1", "255.255.255.252")],
                [("172.20.10.0", "0.0.0.255"), ("172.20.0.0", "0.0.0.3")]),
    "Router2": ([("FastEthernet0/0", "Link to Router1", "172.20.0.2", "255.255.255.252"),
                 ("FastEthernet0/1", "Link to Router3", "172.20.0.5", "255.255.255.252")],
                [("172.20.0.0", "0.0.0.3"), ("172.20.0.4", "0.0.0.3")]),
    "Router3": ([("FastEthernet0/0", "Link to Router2", "172.20.0.6", "255.255.255.252"),
                 ("FastEthernet0/1", "Link to Router4", "172.20.0.9", "255.255.255.252")],
                [("172.20.0.4", "0.0.0.3"), ("172.20.0.8", "0.0.0.3")]),
    "Router4": ([("FastEthernet0/0", "Link to Router3", "172.20.0.10", "255.255.255.252"),
                 ("FastEthernet0/1", "Link to Router5", "172.20.0.13", "255.255.255.252")],
                [("172.20.0.8", "0.0.0.3"), ("172.20.0.12", "0.0.0.3")]),
    "Router5": ([("FastEthernet0/0", "Link to Router4", "172.20.0.14", "255.255.255.252"),
                 ("FastEthernet0/1", "LAN Switch3", "172.20.20.1", "255.255.255.0")],
                [("172.20.0.12", "0.0.0.3"), ("172.20.20.0", "0.0.0.255")]),
}

DEVICES = [
    ("Router1", "Router", "1841", 300, 300, router_config("Router1", *ROUTERS["Router1"])),
    ("Router2", "Router", "1841", 500, 200, router_config("Router2", *ROUTERS["Router2"])),
    ("Router3", "Router", "1841", 700, 200, router_config("Router3", *ROUTERS["Router3"])),
    ("Router4", "Router", "1841", 900, 200, router_config("Router4", *ROUTERS["Router4"])),
    ("Router5", "Router", "1841", 1100, 300, router_config("Router5", *ROUTERS["Router5"])),
    ("Switch2", "Switch", "2960-24TT", 300, 480,
     switch_config("Switch2", ["FastEthernet0/1", "FastEthernet0/2"], "GigabitEthernet0/1", "172.20.10.1")),
    ("Switch3", "Switch", "2960-24TT", 1100, 480,
     switch_config("Switch3", ["FastEthernet0/1", "FastEthernet0/2", "FastEthernet0/3"], "GigabitEthernet0/1", "172.20.20.1")),
    ("L1", "Laptop", "Laptop-PT", 220, 640, ("172.20.10.11", "255.255.255.0", "172.20.10.1")),
    ("L2", "Laptop", "Laptop-PT", 380, 640, ("172.20.10.12", "255.255.255.0", "172.20.10.1")),
    ("PC1", "Pc", "PC-PT", 1000, 640, ("172.20.20.11", "255.255.255.0", "172.20.20.1")),
    ("PC2", "Pc", "PC-PT", 1100, 640, ("172.20.20.12", "255.255.255.0", "172.20.20.1")),
    ("Server0", "Server", "Server-PT", 1200, 640, ("172.20.20.100", "255.255.255.0", "172.20.20.1")),
    ("Power Distribution Device0", "Power Distribution Device", "Power Distribution Device", 3900, 3900, None),
]

LINKS = [
    ("Switch2", "GigabitEthernet0/1", "Router1", "FastEthernet0/0", "eStraightThrough"),
    ("Router1", "FastEthernet0/1", "Router2", "FastEthernet0/0", "eCrossOver"),
    ("Router2", "FastEthernet0/1", "Router3", "FastEthernet0/0", "eCrossOver"),
    ("Router3", "FastEthernet0/1", "Router4", "FastEthernet0/0", "eCrossOver"),
    ("Router4", "FastEthernet0/1", "Router5", "FastEthernet0/0", "eCrossOver"),
    ("Router5", "FastEthernet0/1", "Switch3", "GigabitEthernet0/1", "eStraightThrough"),
    ("Switch2", "FastEthernet0/1", "L1", "FastEthernet0", "eStraightThrough"),
    ("Switch2", "FastEthernet0/2", "L2", "FastEthernet0", "eStraightThrough"),
    ("Switch3", "FastEthernet0/1", "PC1", "FastEthernet0", "eStraightThrough"),
    ("Switch3", "FastEthernet0/2", "PC2", "FastEthernet0", "eStraightThrough"),
    ("Switch3", "FastEthernet0/3", "Server0", "FastEthernet0", "eStraightThrough"),
]

NOTES = [
    (620, 90, "OSPF 10\nAREA 0"),
    (300, 560, "172.20.10.0/24"),
    (1100, 560, "172.20.20.0/24"),
]

ELLIPSES = [
    # left LAN, right LAN, in canvas coordinates
    ((160, 420, 460, 700), (170, 220, 255)),
    ((940, 420, 1260, 700), (255, 220, 170)),
]


def ref(name):
    """Stable SAVE_REF_ID per device, so regenerating gives an identical file."""
    return f"save-ref-id:{1000 + [d[0] for d in DEVICES].index(name)}"


def device_xml(name, ptype, model, x, y, payload):
    out = ["  <DEVICE>", "   <ENGINE>",
           f'    <TYPE customModel="" model="{escape(model)}">{escape(ptype)}</TYPE>',
           f"    <NAME>{escape(name)}</NAME>"]
    if isinstance(payload, list):
        out.append("    <RUNNINGCONFIG>")
        out += [f"     <LINE>{escape(line)}</LINE>" for line in payload]
        out.append("    </RUNNINGCONFIG>")
    elif isinstance(payload, tuple):
        ip, mask, gw = payload
        out += ["    <MODULE><TYPE>eNonRemovableModule</TYPE><SLOT><TYPE>ePtHostModule</TYPE><MODULE>",
                "     <PORT>",
                "      <TYPE>eCopperFastEthernet</TYPE>",
                f"      <IP>{ip}</IP>",
                f"      <SUBNET>{mask}</SUBNET>",
                f"      <PORT_GATEWAY>{gw}</PORT_GATEWAY>",
                "     </PORT>",
                "    </MODULE></SLOT></MODULE>"]
    out += [f"    <SAVE_REF_ID>{ref(name)}</SAVE_REF_ID>", "   </ENGINE>",
            "   <WORKSPACE>", "    <LOGICAL>", f"     <X>{x}</X>", f"     <Y>{y}</Y>", "    </LOGICAL>",
            "   </WORKSPACE>", "  </DEVICE>"]
    return out


def link_xml(a, pa, b, pb, cable):
    return ["  <LINK>", "   <TYPE>eCopper</TYPE>", "   <CABLE>",
            "    <LENGTH>1</LENGTH>", "    <FUNCTIONAL>true</FUNCTIONAL>",
            f"    <FROM>{ref(a)}</FROM>", f"    <PORT>{pa}</PORT>",
            f"    <TO>{ref(b)}</TO>", f"    <PORT>{pb}</PORT>",
            f"    <TYPE>{cable}</TYPE>", "   </CABLE>", "  </LINK>"]


def build() -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<PACKETTRACER5>",
             " <VERSION>8.2.2.0400</VERSION>", " <NETWORK>", "  <DEVICES>"]
    for d in DEVICES:
        lines += device_xml(*d)
    lines += ["  </DEVICES>", "  <LINKS>"]
    for link in LINKS:
        lines += link_xml(*link)
    lines += ["  </LINKS>", " </NETWORK>",
              " <USER_PROFILE><NAME></NAME><EMAIL></EMAIL><ADDITIONAL_INFO></ADDITIONAL_INFO></USER_PROFILE>",
              " <NOTES>"]
    for i, (x, y, text) in enumerate(NOTES):
        lines += [f'  <NOTE uuid="{{00000000-0000-0000-0000-{i:012d}}}">', f"   <X>{x}</X>", f"   <Y>{y}</Y>",
                  "   <Z>0.2</Z>", f'   <TEXT translate="true">{escape(text)}</TEXT>',
                  "   <NOTECLUSTERID></NOTECLUSTERID>", "  </NOTE>"]
    lines += [" </NOTES>", " <ELLIPSES>"]
    for i, ((x1, y1, x2, y2), (r, g, b)) in enumerate(ELLIPSES):
        lines += [f'  <ELLIPSE uuid="{{10000000-0000-0000-0000-{i:012d}}}">',
                  f"   <TopLeftX>{x1}</TopLeftX>", f"   <TopLeftY>{y1}</TopLeftY>",
                  f"   <BottomRightX>{x2}</BottomRightX>", f"   <BottomRightY>{y2}</BottomRightY>",
                  f"   <Color><Red>{r}</Red><Green>{g}</Green><Blue>{b}</Blue></Color>",
                  '   <Filled OUTLINECOLOR="#000000" OUTLINED="true">0</Filled>',
                  "   <ELLIPSECLUSTERID>1-1</ELLIPSECLUSTERID>", "  </ELLIPSE>"]
    lines += [" </ELLIPSES>", "</PACKETTRACER5>", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(build())
    print(f"wrote {OUT}")
