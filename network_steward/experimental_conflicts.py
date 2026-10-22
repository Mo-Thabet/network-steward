"""Narrow experimental guards for conflicting synthetic observations.

These guards are intentionally separate from the approved prototype rules.
They only downgrade an otherwise supported candidate when mutually
inconsistent or materially ambiguous observations occur in the same capture.
"""

import ipaddress
import re

from .normalize import line_has_interface


def _item(capture_index, line_number, line):
    return {"capture_index": capture_index, "line_number": line_number, "line": line}


def _command_captures(fixture, contains):
    needle = contains.casefold()
    return [(ci, cap) for ci, cap in enumerate(fixture["captures"])
            if needle in cap.get("command", "").casefold()]


def _ns01(fixture):
    lab = fixture["lab_map"]
    interface = lab.get("expected_endpoint_interface")
    device = lab.get("device")
    if not interface or not device:
        return None
    for ci, cap in _command_captures(fixture, "show ip interface brief") + _command_captures(fixture, "show interfaces " + interface):
        if cap.get("device", "").casefold() != device.casefold():
            continue
        lines = []
        states = set()
        for li, line in enumerate(cap.get("output", "").splitlines(), 1):
            if not line_has_interface(line, interface):
                continue
            lowered = line.casefold()
            if "administratively down" in lowered:
                states.add("administratively down")
                lines.append(_item(ci, li, line))
            if re.search(r"\bup\s+up\b", lowered):
                states.add("up/up")
                lines.append(_item(ci, li, line))
        if {"administratively down", "up/up"}.issubset(states):
            return "Mapped interface has mutually exclusive administratively down and up/up observations in one capture.", lines
    return None


def _ns02_access(fixture):
    lab = fixture["lab_map"]
    port = lab.get("access_port")
    if lab.get("variant") != "access_vlan" or not port:
        return None
    def canonical(name):
        value = name.strip().casefold()
        for short, long in (("gi", "gigabitethernet"), ("fa", "fastethernet"),
                            ("te", "tengigabitethernet"), ("eth", "ethernet")):
            if value.startswith(short) and value[len(short):len(short) + 1].isdigit():
                return long + value[len(short):]
        return value

    expected_port = canonical(port)
    for ci, cap in _command_captures(fixture, f"show interfaces {port} switchport"):
        observed = []
        current_port = None
        for li, line in enumerate(cap.get("output", "").splitlines(), 1):
            name_match = re.match(r"^\s*Name\s*:\s*(\S+)", line, re.I)
            if name_match:
                current_port = name_match.group(1)
            match = re.search(r"^\s*Access Mode VLAN\s*:\s*(\d+)\b", line, re.I)
            if match and current_port and canonical(current_port) == expected_port:
                observed.append((int(match.group(1)), _item(ci, li, line)))
        values = {value for value, _ in observed}
        if len(values) > 1:
            return f"The same access port {port} has multiple reported access VLANs.", [item for _, item in observed]
    return None


def _ns02_trunk(fixture):
    lab = fixture["lab_map"]
    uplink = lab.get("uplink")
    expected = lab.get("expected_client_vlan")
    if lab.get("variant") != "trunk_allowed_vlan" or not uplink or expected is None:
        return None
    for ci, cap in _command_captures(fixture, "show interfaces trunk"):
        in_allowed_section = False
        observations = []
        for li, line in enumerate(cap.get("output", "").splitlines(), 1):
            if "vlans allowed and active" in line.casefold():
                in_allowed_section = True
                continue
            if not in_allowed_section:
                continue
            fields = line.split()
            if len(fields) < 2 or fields[0].casefold() != uplink.casefold():
                continue
            vlan_text = fields[-1]
            values = set()
            valid = True
            for segment in vlan_text.split(","):
                match = re.fullmatch(r"(\d+)(?:-(\d+))?", segment)
                if not match:
                    valid = False
                    break
                start, end = int(match.group(1)), int(match.group(2) or match.group(1))
                values.update(range(start, end + 1))
            if valid:
                observations.append((int(expected) in values, _item(ci, li, line)))
        statuses = {contains_expected for contains_expected, _ in observations}
        # A trunk list may legitimately contain many VLANs. Only repeated rows
        # for this same uplink that disagree about the expected VLAN are gated.
        if len(statuses) > 1:
            return f"Repeated allowed-and-active rows for uplink {uplink} disagree about VLAN {expected}.", [item for _, item in observations]
    return None


def _ns03(fixture):
    lab = fixture["lab_map"]
    interface = lab.get("interface")
    acl_name = lab.get("acl_name")
    if not interface or not acl_name:
        return None
    for ci, cap in _command_captures(fixture, f"show ip interface {interface}"):
        directions = {}
        for li, line in enumerate(cap.get("output", "").splitlines(), 1):
            match = re.search(r"\b(inbound|outbound|outgoing) access list is\s+(\S+)", line, re.I)
            if match and match.group(2).casefold() == acl_name.casefold():
                direction = "outbound" if match.group(1).casefold() in {"outbound", "outgoing"} else "inbound"
                directions[direction] = _item(ci, li, line)
        if len(directions) > 1:
            # An ACL can validly be attached both ways. This is ambiguity for
            # this single-direction diagnostic, not a claim of invalid config.
            return f"ACL {acl_name} is shown in both directions on {interface}; direction-specific diagnosis is ambiguous.", list(directions.values())
    return None


def _ns05(fixture, finding):
    """Reject no-route evidence whose explicit prefix differs from expected."""
    prefix = fixture["lab_map"].get("expected_prefix")
    if not prefix:
        return None
    route_captures = _command_captures(fixture, "show ip route")
    unsupported = []
    for citation in finding.evidence:
        ci = citation["capture_index"]
        if ci < 0 or ci >= len(fixture["captures"]):
            continue
        cap = fixture["captures"][ci]
        if not any(index == ci for index, _ in route_captures):
            continue
        line = citation["line"]
        if not re.search(r"not in table|route not found|no route", line, re.I):
            continue
        # A no-route line that names a different prefix contradicts the
        # expected destination, even when the command requested this prefix.
        line_prefixes = re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}\b", line)
        names_different_prefix = bool(line_prefixes) and str(prefix) not in line_prefixes
        if names_different_prefix:
            unsupported.append(citation)
    if unsupported:
        return (f"No-route evidence does not identify expected prefix {prefix}.", unsupported)
    return None


def _ns07(fixture):
    """Detect matching DHCP pools whose available-address counts disagree."""
    subnet = fixture["lab_map"].get("affected_client_subnet")
    if not subnet:
        return None
    try:
        expected = ipaddress.ip_network(subnet, strict=False)
    except ValueError:
        return None

    matching = []
    for ci, cap in _command_captures(fixture, "show ip dhcp pool"):
        lines = cap.get("output", "").splitlines()
        starts = [i for i, line in enumerate(lines)
                  if re.match(r"^\s*Pool\s+.+?\s*:\s*$", line, re.I)] or [0]
        for block_index, start in enumerate(starts):
            end = starts[block_index + 1] if block_index + 1 < len(starts) else len(lines)
            network = None
            available = None
            cited_lines = []
            for li in range(start, end):
                line = lines[li]
                network_match = re.search(
                    r"(?:network|subnet)\s*:?\s*(\d+\.\d+\.\d+\.\d+(?:\s*/\s*\d+)?)", line, re.I
                )
                if network_match:
                    network = network_match.group(1).replace(" ", "")
                    cited_lines.append(_item(ci, li + 1, line))
                available_match = re.search(r"available addresses\s*:?\s*(\d+)", line, re.I)
                if available_match:
                    available = int(available_match.group(1))
                    cited_lines.append(_item(ci, li + 1, line))
            if network:
                try:
                    if ipaddress.ip_network(network, strict=False) == expected:
                        matching.append((available, cited_lines))
                except ValueError:
                    pass

    if len(matching) > 1 and len({available for available, _ in matching}) > 1:
        citations = [item for _, items in matching for item in items]
        return (f"Duplicate pools for subnet {subnet} report conflicting available-address counts.", citations)
    return None


def _ns08(fixture):
    lab = fixture["lab_map"]
    pool = lab.get("matching_pool")
    if not pool:
        return None
    for ci, cap in _command_captures(fixture, "show running-config | section dhcp"):
        in_pool = False
        dns_lines = []
        for li, line in enumerate(cap.get("output", "").splitlines(), 1):
            pool_match = re.match(r"^ip dhcp pool\s+(\S+)", line, re.I)
            if pool_match:
                if in_pool:
                    break
                in_pool = pool_match.group(1).casefold() == pool.casefold()
                continue
            if in_pool and re.match(r"^\s*dns-server\s+", line, re.I):
                dns_lines.append((line, _item(ci, li, line)))
        values = set()
        for line, _ in dns_lines:
            match = re.match(r"^\s*dns-server\s+(.+?)\s*$", line, re.I)
            if match:
                values.update(value.casefold() for value in match.group(1).split())
        # Multiple DHCP DNS servers are valid configuration; mixed values make
        # this single expected-resolver symptom ambiguous, so abstain safely.
        if len(values) > 1:
            return f"Pool {pool} advertises multiple DNS server addresses; the expected-resolver diagnosis is ambiguous.", [item for _, item in dns_lines]
    return None


_GUARDS = {
    "NS-01": (_ns01,),
    "NS-02": (_ns02_access, _ns02_trunk),
    "NS-03": (_ns03,),
    "NS-05": (),
    "NS-07": (_ns07,),
    "NS-08": (_ns08,),
}


def apply_experimental_conflict_guards(fixture, findings):
    """Downgrade narrowly gated findings and return report-level abstention reasons."""
    reasons = []
    by_id = {finding.scenario_id: finding for finding in findings}
    for scenario_id, guards in _GUARDS.items():
        finding = by_id.get(scenario_id)
        if finding is None or finding.state != "supported":
            continue
        matched_guards = ((_ns05(fixture, finding),) if scenario_id == "NS-05"
                          else (guard(fixture) for guard in guards))
        for matched in matched_guards:
            if not matched:
                continue
            reason, citations = matched
            finding.state = "insufficient"
            finding.score = 0
            if scenario_id in {"NS-05", "NS-07"}:
                finding.evidence = [item for item in finding.evidence if item not in citations]
                finding.contradictory.extend(citations)
            else:
                # Keep these as cited observations. Some patterns (notably
                # multiple DNS servers and bidirectional ACL use) can be valid.
                finding.evidence.extend(citations)
            finding.missing.append(reason)
            reasons.append(f"{scenario_id}: {reason}")
            break
    return reasons
