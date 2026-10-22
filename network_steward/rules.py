import ipaddress
import re

from .models import Finding
from .normalize import command_captures, line_has_interface, lines


def _eq(a, b):
    return str(a).casefold() == str(b).casefold()


def _line(captures, *needles):
    return list(lines(captures, *needles))


def _cmd(captures, *commands):
    return list(command_captures(captures, *commands))


def _next(sid, lab, captures, variant=""):
    if sid == "NS-01": return f"show interfaces {lab.get('expected_endpoint_interface', '<interface>')}"
    if sid == "NS-02": return "show interfaces trunk" if variant == "trunk_allowed_vlan" else "show vlan brief"
    if sid == "NS-03": return f"show access-lists {lab.get('acl_name', '<name>')}"
    if sid == "NS-04": return f"show ip ospf interface {lab.get('peer_interface', '<interface>')} on the other end"
    if sid == "NS-05": return "show ip protocols"
    if sid == "NS-06":
        iface = lab.get("client_vlan_interface", "<interface>")
        return f"show ip interface {iface}" if _cmd(captures, "show running-config interface") else f"show running-config interface {iface}"
    if sid == "NS-07": return "show ip dhcp binding"
    if sid == "NS-08": return "show ip dhcp pool" if _cmd(captures, "show running-config | section dhcp") else "show running-config | section dhcp"
    return ""


def _finding(sid, state="insufficient", **kw):
    return Finding(sid, state, **kw)


def rule_01(f, captures):
    lab, report = f["lab_map"], f["report"]
    interface = lab.get("expected_endpoint_interface")
    finding = _finding("NS-01", next_command=_next("NS-01", lab, captures))
    if not interface or not report.get("device"):
        finding.missing.append("expected endpoint-to-switch/interface mapping")
        return finding
    outputs = [(ci, cap) for ci, cap in _cmd(captures, "show ip interface brief", "show interfaces " + interface)
               if _eq(cap["device"], report["device"])]
    if not outputs:
        finding.missing.append("show ip interface brief or show interfaces for the mapped port")
        return finding
    found = []
    for ci, cap in outputs:
        for li, line in enumerate(cap["output"].splitlines(), 1):
            if not line_has_interface(line, interface): continue
            item = {"capture_index": ci, "line_number": li, "line": line}
            if "administratively down" in line.casefold(): found.append(item)
            elif re.search(r"\bup\s+up\b", line, re.I): finding.contradictory.append(item)
            elif re.search(r"\bdown\s+down\b", line, re.I):
                finding.contradictory.append(item)
                finding.expected_facts.append("down/down without administratively down indicates another link condition")
    if found:
        finding.state, finding.score = "supported", 2
        finding.evidence.extend(found)
        finding.expected_facts.append(f"mapped interface {interface} should be administratively up")
    elif finding.contradictory:
        finding.state = "contradicted"
    else:
        finding.missing.append(f"a state line for mapped interface {interface}")
    return finding


def rule_02(f, captures):
    lab = f["lab_map"]
    variant, vlan = lab.get("variant"), lab.get("expected_client_vlan")
    finding = _finding("NS-02", next_command=_next("NS-02", lab, captures, variant))
    if variant not in {"access_vlan", "trunk_allowed_vlan"} or not vlan:
        finding.missing.append("expected VLAN and explicit NS-02 variant")
        return finding
    if variant == "access_vlan":
        port = lab.get("access_port")
        if not port:
            finding.missing.append("expected access port")
            return finding
        caps = _cmd(captures, f"show interfaces {port} switchport")
        if not caps:
            finding.missing.append(f"show interfaces {port} switchport")
            return finding
        for ci, cap in caps:
            for li, line in enumerate(cap["output"].splitlines(), 1):
                if "access mode vlan" not in line.casefold(): continue
                m = re.search(r"access mode vlan\s*:\s*(\d+)", line, re.I)
                item = {"capture_index": ci, "line_number": li, "line": line}
                if not m: continue
                if m.group(1) != str(vlan):
                    finding.evidence.append(item); finding.expected_facts.append(f"{port} expected access VLAN {vlan}")
                else: finding.contradictory.append(item)
        if finding.evidence: finding.state, finding.score = "supported", 2
        elif finding.contradictory: finding.state = "contradicted"
        else: finding.missing.append("reported access VLAN for the expected port")
        return finding
    uplink = lab.get("uplink")
    if not uplink:
        finding.missing.append("expected uplink")
        return finding
    caps = _cmd(captures, "show interfaces trunk")
    if not caps:
        finding.missing.append("show interfaces trunk")
        return finding
    for ci, cap in caps:
        output = cap["output"].splitlines()
        operational = any(uplink.casefold() in line.casefold() and any(token.casefold() == "trunking" for token in line.split()) for line in output)
        if not operational:
            finding.contradictory.extend({"capture_index": ci, "line_number": n, "line": line} for n, line in enumerate(output, 1) if uplink.casefold() in line.casefold())
            continue
        header_idx = next((i for i, line in enumerate(output) if "allowed and active" in line.casefold()), None)
        vlan_line = output[header_idx + 1] if header_idx is not None and header_idx + 1 < len(output) else ""
        if not vlan_line:
            finding.missing.append("allowed-and-active VLAN list for the operational uplink")
            continue
        item = {"capture_index": ci, "line_number": header_idx + 2, "line": vlan_line}
        if not _vlan_contains(vlan_line, vlan):
            finding.evidence.append(item); finding.expected_facts.append(f"operational uplink {uplink} expected VLAN {vlan} in allowed-and-active list")
        else: finding.contradictory.append(item)
    if finding.evidence: finding.state, finding.score = "supported", 2
    elif finding.contradictory: finding.state = "contradicted"
    elif not finding.missing: finding.missing.append("operational trunk and allowed-and-active VLAN list")
    return finding


def _vlan_contains(text, expected):
    target = int(expected)
    text = text.strip().rsplit(None, 1)[-1]
    for part in text.strip().split(","):
        m = re.fullmatch(r"\s*(\d+)(?:\s*-\s*(\d+))?\s*", part)
        if m and int(m.group(1)) <= target <= int(m.group(2) or m.group(1)): return True
    return False


def _ip_match(rule_ip, expected):
    if rule_ip.casefold() == "any": return True
    try:
        net = ipaddress.ip_network(rule_ip, strict=False)
        addr = ipaddress.ip_address(expected)
        return addr in net
    except ValueError:
        return False


def rule_03(f, captures):
    lab = f["lab_map"]
    finding = _finding("NS-03", next_command=_next("NS-03", lab, captures))
    required = ["source", "destination", "protocol", "port", "interface", "direction", "acl_name"]
    missing = [x for x in required if not lab.get(x)]
    if missing:
        finding.missing.append("flow/path baseline: " + ", ".join(missing)); return finding
    attaches = []
    for ci, cap in _cmd(captures, f"show ip interface {lab['interface']}"):
        for li, line in enumerate(cap["output"].splitlines(), 1):
            m = re.search(r"(inbound|outbound|outgoing) access list is\s+(\S+)", line, re.I)
            if m:
                direction = "outbound" if m.group(1).casefold() in {"outbound", "outgoing"} else "inbound"
                attaches.append((direction, m.group(2), {"capture_index": ci, "line_number": li, "line": line}))
    if not attaches: finding.missing.append(f"ACL attachment and direction on {lab['interface']}")
    acl_caps = _cmd(captures, f"show access-lists {lab['acl_name']}")
    if not acl_caps: finding.missing.append(f"show access-lists {lab['acl_name']}")
    matching = []
    for ci, cap in acl_caps:
        for li, line in enumerate(cap["output"].splitlines(), 1):
            # IOS extended ACLs may qualify a single address with `host`.
            # Consume that operand while preserving the existing any/CIDR
            # matching and optional transport-port behavior.
            m = re.search(r"\bdeny\s+(\w+)\s+(?:host\s+)?(\S+)\s+(?:host\s+)?(\S+)(?:\s+(?:eq|range)\s+(\d+))?", line, re.I)
            if not m: continue
            proto, src, dst, port = m.groups()
            proto_ok = proto.casefold() in {lab["protocol"].casefold(), "ip"}
            if proto_ok and _ip_match(src, lab["source"]) and _ip_match(dst, lab["destination"]) and (port is None or port == str(lab["port"])):
                matching.append({"capture_index": ci, "line_number": li, "line": line})
    attached = any(_eq(name, lab["acl_name"]) and _eq(direction, lab["direction"]) for direction, name, _ in attaches)
    if matching and attached:
        finding.state, finding.score = "supported", 2
        finding.evidence.extend([a[2] for a in attaches if _eq(a[1], lab["acl_name"]) and _eq(a[0], lab["direction"])])
        finding.evidence.extend(matching)
        finding.expected_facts.append(f"{lab['acl_name']} {lab['direction']} on {lab['interface']} denies {lab['protocol']} {lab['source']} to {lab['destination']} port {lab['port']}")
    elif matching:
        finding.state = "contradicted"
        finding.contradictory.extend(matching)
        finding.expected_facts.append("matching deny is not shown attached in the relevant path and direction")
    elif attaches and acl_caps:
        finding.state = "contradicted"
        finding.contradictory.extend(a[2] for a in attaches)
    return finding


def rule_04(f, captures):
    lab = f["lab_map"]
    finding = _finding("NS-04", next_command=_next("NS-04", lab, captures))
    for key in ("peer_address", "local_interface", "peer_interface", "expected_area"):
        if not lab.get(key): finding.missing.append("OSPF topology baseline: " + key)
    if finding.missing: return finding
    neighbors = _cmd(captures, "show ip ospf neighbor")
    local = _cmd(captures, f"show ip ospf interface {lab['local_interface']}")
    peer = _cmd(captures, f"show ip ospf interface {lab['peer_interface']}")
    if not neighbors: finding.missing.append("show ip ospf neighbor")
    if not local: finding.missing.append(f"show ip ospf interface {lab['local_interface']}")
    if not peer: finding.missing.append(f"show ip ospf interface {lab['peer_interface']} on peer")
    peer_lines = []
    neighbor_context = []
    for ci, cap in neighbors:
        for li, line in enumerate(cap["output"].splitlines(), 1):
            if lab["peer_address"] in line:
                peer_lines.append({"capture_index": ci, "line_number": li, "line": line})
            elif line.strip() and "neighbor id" not in line.casefold():
                neighbor_context.append({"capture_index": ci, "line_number": li, "line": line})
    local_areas = _areas(local)
    peer_areas = _areas(peer)
    if local_areas and peer_areas and peer_lines and any("full" in x["line"].casefold() for x in peer_lines):
        finding.state = "contradicted"; finding.contradictory.extend(peer_lines)
    elif local_areas and peer_areas and local_areas[0][0] != peer_areas[0][0] and (not peer_lines or all("full" not in x["line"].casefold() for x in peer_lines)):
        finding.state, finding.score = "supported", 3
        finding.evidence.extend(local_areas[0][1] + peer_areas[0][1])
        if peer_lines: finding.evidence.extend(peer_lines)
        elif neighbor_context: finding.evidence.extend(neighbor_context)
        finding.expected_facts.append(f"direct peer interfaces should both use OSPF area {lab['expected_area']}; observed {local_areas[0]} and {peer_areas[0]}")
    else:
        if local_areas and peer_areas and local_areas[0][0] == peer_areas[0][0]: finding.contradictory.extend(local_areas[0][1] + peer_areas[0][1])
        elif not local_areas: finding.missing.append("local interface OSPF area line")
        elif not peer_areas: finding.missing.append("peer interface OSPF area line")
        if peer_lines: finding.evidence.extend(peer_lines)
    return finding


def _areas(captures):
    found = []
    for ci, cap in captures:
        for li, line in enumerate(cap["output"].splitlines(), 1):
            m = re.search(r"\bArea\s+(\S+)", line, re.I)
            if m: found.append((m.group(1).rstrip(","), [{"capture_index": ci, "line_number": li, "line": line}]))
    return found


def rule_05(f, captures):
    lab = f["lab_map"]
    prefix = lab.get("expected_prefix")
    finding = _finding("NS-05", next_command=_next("NS-05", lab, captures))
    if not prefix or not lab.get("router"):
        finding.missing.append("expected-prefix and router baseline"); return finding
    targeted_caps = _cmd(captures, f"show ip route {prefix}")
    caps = targeted_caps or _cmd(captures, "show ip route")
    if not caps:
        finding.missing.append(f"show ip route {prefix}"); return finding
    matching_routes = []
    matching_no_routes = []
    no_route_pattern = re.compile(r"not in table|route not found|no route", re.I)
    for ci, cap in caps:
        for li, line in enumerate(cap["output"].splitlines(), 1):
            if prefix in line:
                item = {"capture_index": ci, "line_number": li, "line": line}
                if no_route_pattern.search(line):
                    matching_no_routes.append(item)
                else:
                    matching_routes.append(item)
    default_intended = lab.get("default_route_intended_to_cover") is True
    default_lines = _line([c for _, c in caps], "0.0.0.0/0", "Gateway of last resort")
    if matching_routes:
        finding.state = "contradicted"; finding.contradictory.extend(matching_routes)
        finding.expected_facts.append(f"route for expected prefix {prefix} should be absent")
    elif default_intended and default_lines:
        finding.state = "contradicted"; finding.contradictory.extend(default_lines)
        finding.expected_facts.append("lab design intends the observed default route to cover this destination")
    else:
        # A named no-route result is relevant only when it names the investigated
        # prefix. An unqualified no-route result retains the existing behavior;
        # a different named prefix must not support this finding.
        generic_no_routes = []
        unrelated_no_routes = []
        for ci, cap in caps:
            for li, line in enumerate(cap["output"].splitlines(), 1):
                if not no_route_pattern.search(line): continue
                named_prefix = re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}\b", line)
                if named_prefix and prefix in line:
                    continue
                if named_prefix:
                    unrelated_no_routes.append({"capture_index": ci, "line_number": li, "line": line})
                else:
                    generic_no_routes.append({"capture_index": ci, "line_number": li, "line": line})
        relevant_no_routes = matching_no_routes + generic_no_routes
        if relevant_no_routes:
            finding.state, finding.score = "supported", 2
            finding.evidence.extend(relevant_no_routes)
            finding.expected_facts.append(f"{lab['router']} is expected to have a route to {prefix}")
        else:
            finding.contradictory.extend(unrelated_no_routes)
            finding.missing.append("explicit no-route result for the expected prefix")
    return finding


def rule_06(f, captures):
    lab = f["lab_map"]
    finding = _finding("NS-06", next_command=_next("NS-06", lab, captures))
    required = ("client_vlan_interface", "client_subnet", "dhcp_server_remote", "relay_expected")
    missing = [k for k in required if k not in lab]
    if missing: finding.missing.append("relay topology baseline: " + ", ".join(missing)); return finding
    if not lab["dhcp_server_remote"] or not lab["relay_expected"]:
        finding.state = "contradicted"; finding.expected_facts.append("relay is not required by the supplied topology"); return finding
    iface = lab["client_vlan_interface"]
    caps = _cmd(captures, f"show running-config interface {iface}")
    if not caps: finding.missing.append(f"show running-config interface {iface}"); return finding
    helper, address = [], []
    for ci, cap in caps:
        for li, line in enumerate(cap["output"].splitlines(), 1):
            item = {"capture_index": ci, "line_number": li, "line": line}
            if "ip helper-address" in line.casefold(): helper.append(item)
            if line.strip().startswith("ip address "): address.append(item)
    if helper:
        finding.state = "contradicted"; finding.contradictory.extend(helper)
        finding.expected_facts.append("client VLAN should have no helper only if the relay omission is present")
    elif address:
        finding.state, finding.score = "supported", 2
        finding.evidence.extend(address)
        finding.expected_facts.append(f"{iface} serves {lab['client_subnet']}; remote DHCP design requires a helper address")
    else:
        finding.missing.append("interface address line establishing the client VLAN interface")
    return finding


def _pool_records(captures):
    records = []
    for ci, cap in _cmd(captures, "show ip dhcp pool"):
        output = cap["output"].splitlines()
        headers = [i for i, line in enumerate(output)
                   if re.match(r"^\s*Pool\s+.+?\s*:\s*$", line, re.I)]
        starts = headers if headers else [0]
        for block_index, start in enumerate(starts):
            end = starts[block_index + 1] if block_index + 1 < len(starts) else len(output)
            rec = {"capture_index": ci, "network": None, "available": None, "lines": []}
            for li in range(start, end):
                line = output[li]
                item = {"capture_index": ci, "line_number": li + 1, "line": line}
                m = re.search(r"(?:network|subnet)\s*:?\s*(\d+\.\d+\.\d+\.\d+(?:\s*/\s*\d+)?)", line, re.I)
                if m: rec["network"] = m.group(1).replace(" ", "")
                m = re.search(r"available addresses\s*:?\s*(\d+)", line, re.I)
                if m: rec["available"] = int(m.group(1))
                if "utilization" in line.casefold() or "available addresses" in line.casefold() or "network" in line.casefold(): rec["lines"].append(item)
            records.append(rec)
    return records

def _network_equal(observed, expected):
    try: return ipaddress.ip_network(observed, strict=False) == ipaddress.ip_network(expected, strict=False)
    except ValueError: return False


def rule_07(f, captures):
    lab = f["lab_map"]
    finding = _finding("NS-07", next_command=_next("NS-07", lab, captures))
    subnet = lab.get("affected_client_subnet")
    if not subnet: finding.missing.append("affected client subnet baseline"); return finding
    pools = _pool_records(captures)
    if not pools: finding.missing.append("show ip dhcp pool"); return finding
    matches = [p for p in pools if p["network"] and _network_equal(p["network"], subnet)]
    if not matches:
        if any(p["network"] for p in pools):
            finding.missing.append(f"no pool mapped to affected subnet {subnet}; unrelated pool utilization cannot establish this fault")
        else: finding.missing.append("pool network mapped to affected client subnet")
        return finding
    target = matches[0]
    if target["available"] is None:
        finding.missing.append("available-address count for matching DHCP pool"); return finding
    if target["available"] == 0:
        finding.state, finding.score = "supported", 2
        finding.evidence.extend(target["lines"])
        finding.expected_facts.append(f"matching pool network {target['network']} should have available addresses")
    else:
        finding.state = "contradicted"
        finding.contradictory.extend(target["lines"])
        finding.expected_facts.append(f"matching pool has {target['available']} available addresses")
    return finding


def rule_08(f, captures):
    lab = f["lab_map"]
    finding = _finding("NS-08", next_command=_next("NS-08", lab, captures))
    required = ("affected_client_subnet", "matching_pool", "expected_dns")
    missing = [k for k in required if not lab.get(k)]
    if missing: finding.missing.append("DNS/pool baseline: " + ", ".join(missing)); return finding
    if not (lab.get("name_resolution_specific") or lab.get("ip_connectivity_works")):
        finding.missing.append("name-resolution-specific symptom or working IP-connectivity context"); return finding
    caps = _cmd(captures, "show running-config | section dhcp")
    if not caps: finding.missing.append("show running-config | section dhcp"); return finding
    output_lines = [(ci, li, line) for ci, cap in caps for li, line in enumerate(cap["output"].splitlines(), 1)]
    pool_idx = next((i for i, (_, _, line) in enumerate(output_lines) if re.search(r"^ip dhcp pool\s+", line, re.I) and line.split(None, 3)[-1].casefold() == str(lab["matching_pool"]).casefold()), None)
    if pool_idx is None:
        finding.missing.append(f"configuration block for pool {lab['matching_pool']}"); return finding
    block = []
    for item in output_lines[pool_idx:]:
        if item is not output_lines[pool_idx] and item[2].startswith("ip dhcp pool "): break
        block.append(item)
    network_item = next((x for x in block if re.search(r"^ network\s+", x[2], re.I)), None)
    dns_item = next((x for x in block if re.search(r"^ dns-server\s+", x[2], re.I)), None)
    if not network_item or not dns_item:
        finding.missing.append("matching pool network and dns-server lines"); return finding
    network_match = re.search(r"^ network\s+(\S+)(?:\s+(\S+))?", network_item[2], re.I)
    network = network_match.group(1)
    if network_match.group(2):
        try: network = str(ipaddress.IPv4Network((network, network_match.group(2)), strict=False))
        except ValueError: pass
    dns = re.search(r"^ dns-server\s+(\S+)", dns_item[2], re.I).group(1)
    if not _network_equal(network, lab["affected_client_subnet"]):
        finding.state = "contradicted"; finding.contradictory.append({"capture_index": network_item[0], "line_number": network_item[1], "line": network_item[2]})
        finding.expected_facts.append(f"pool {lab['matching_pool']} should serve {lab['affected_client_subnet']}")
    elif dns.casefold() != str(lab["expected_dns"]).casefold():
        finding.state, finding.score = "supported", 2
        finding.evidence.extend({"capture_index": x[0], "line_number": x[1], "line": x[2]} for x in (network_item, dns_item))
        finding.expected_facts.append(f"pool {lab['matching_pool']} for {lab['affected_client_subnet']} should advertise DNS {lab['expected_dns']}")
    else:
        finding.state = "contradicted"; finding.contradictory.append({"capture_index": dns_item[0], "line_number": dns_item[1], "line": dns_item[2]})
        finding.expected_facts.append(f"pool advertises expected DNS {lab['expected_dns']}")
    return finding


RULES = {"NS-01": rule_01, "NS-02": rule_02, "NS-03": rule_03, "NS-04": rule_04,
         "NS-05": rule_05, "NS-06": rule_06, "NS-07": rule_07, "NS-08": rule_08}


def evaluate(fixture):
    from .experimental_conflicts import apply_experimental_conflict_guards

    findings = [RULES[sid](fixture, fixture["captures"]) for sid in sorted(RULES)]
    experimental_reasons = apply_experimental_conflict_guards(fixture, findings)
    findings.sort(key=lambda x: ({"supported": 0, "contradicted": 1, "insufficient": 2}[x.state], -x.score, x.scenario_id))
    supported = [f for f in findings if f.state == "supported"]
    reasons = []
    if not supported: reasons.append("No scenario has all required evidence; the prototype cannot select a diagnosis.")
    if len(supported) > 1: reasons.append("Multiple scenario rules match; a single-cause conclusion would be unsafe.")
    if fixture["scenario_id"] is None: reasons.append("The reported failure is outside the eight declared scenarios or cannot be mapped to one.")
    # Ambiguity must be determined from findings and evidence-based conflict
    # guards above. `case_kind` is a labelled-case annotation, not runtime input.
    reasons.extend(experimental_reasons)
    return findings, bool(reasons), reasons
