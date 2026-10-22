"""Separate hand-authored synthetic cases; these are not real-world validation."""

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from network_steward import DATA_NOTICE
from network_steward.loader import load_manifest
from network_steward.report import build_report


def case(case_id, scenario_id, kind, lab_map, captures, gold_state=None, abstain=None):
    return {
        "fixture_id": "HOLDOUT-" + case_id,
        "synthetic": True,
        "data_notice": DATA_NOTICE,
        "scenario_id": scenario_id,
        "case_kind": kind,
        "injected_fault": "Separate synthetic test-set expectation; synthetic evidence only.",
        "report": {"symptom": "Synthetic holdout case " + case_id, "device": lab_map.get("device")},
        "lab_map": lab_map,
        "captures": captures,
        "gold": {"scenario_id": scenario_id, "state": gold_state, "abstain": abstain},
    }


# Values, captures, and combinations below were authored separately from the
# 19 manifest fixtures. The cases intentionally include distractors and gaps.
HOLDOUT = [
    case("RENAMED-01", "NS-01", "positive", {
        "device": "SW-FLOOR7-B", "expected_endpoint_interface": "TenGigabitEthernet2/0/31",
    }, [{"device": "SW-FLOOR7-B", "command": "sw-floor7-b# SHOW IP INTERFACE BRIEF", "output":
         "Interface              IP-Address      OK? Method Status                Protocol\n"
         "TenGigabitEthernet2/0/13 unassigned YES unset administratively down down\n"
         "TenGigabitEthernet2/0/31 unassigned YES unset administratively down down"}], "supported", False),
    case("RENAMED-02", "NS-02", "positive", {
        "variant": "access_vlan", "expected_client_vlan": 317, "access_port": "FastEthernet4/0/7",
    }, [{"device": "SW-ANNEX-C", "command": "show interfaces FastEthernet4/0/7 switchport", "output":
         "Name: Fa4/0/7\nOperational Mode: static access\nAccess Mode VLAN: 22 (staff)\n"
         "Name: Fa4/0/8\nAccess Mode VLAN: 317 (guest)"}], "supported", False),
    case("RENAMED-03", "NS-03", "positive", {
        "source": "192.0.2.77", "destination": "198.51.100.201", "protocol": "tcp", "port": 8443,
        "interface": "TenGigabitEthernet0/2", "direction": "outbound", "acl_name": "APP-EGRESS-7",
    }, [
        {"device": "RTR-DC-WEST", "command": "show ip interface TenGigabitEthernet0/2", "output":
         "TenGigabitEthernet0/2 is up, line protocol is up\n  Outbound access list is APP-EGRESS-7"},
        {"device": "RTR-DC-WEST", "command": "show access-lists APP-EGRESS-7", "output":
         "Extended IP access list APP-EGRESS-7\n  5 deny tcp 192.0.2.77 198.51.100.201 eq 8443\n"
         "  10 deny tcp 192.0.2.78 198.51.100.201 eq 8443\n  20 permit ip any any"},
    ], "supported", False),
    case("RENAMED-04", "NS-04", "positive", {
        "peer_address": "203.0.113.222", "local_interface": "TenGigabitEthernet1/1",
        "peer_interface": "TenGigabitEthernet0/9", "expected_area": "12",
    }, [
        {"device": "R-WEST", "command": "show ip ospf neighbor", "output":
         "Neighbor ID Pri State Address Interface\n203.0.113.89 1 FULL/DR 192.0.2.90 Te1/1"},
        {"device": "R-WEST", "command": "show ip ospf interface TenGigabitEthernet1/1", "output":
         "TenGigabitEthernet1/1 is up\n Internet Address 192.0.2.1/30, Area 12, Attached via Network Statement"},
        {"device": "R-EAST", "command": "show ip ospf interface TenGigabitEthernet0/9", "output":
         "TenGigabitEthernet0/9 is up\n Internet Address 192.0.2.2/30, Area 19, Attached via Network Statement"},
    ], "supported", False),
    case("ROUTE-ABSENT-05", "NS-05", "positive", {
        "expected_prefix": "198.51.100.128/25", "router": "RTR-TRANSIT-6", "default_route_intended_to_cover": False,
    }, [{"device": "RTR-TRANSIT-6", "command": "show ip route", "output":
         "Codes: C - connected, S - static\n% Network not in table"}], "supported", False),
    case("PARTIAL-06", "NS-06", "insufficient", {
        "client_vlan_interface": "Vlan317", "client_subnet": "192.0.2.64/26",
        "dhcp_server_remote": True, "relay_expected": True,
    }, [{"device": "RTR-CAMPUS-9", "command": "show running-config interface Vlan317", "output":
         "interface Vlan317\n description Annex clients\n no shutdown"}], "insufficient", True),
    case("IRRELEVANT-07", "NS-07", "insufficient", {
        "affected_client_subnet": "192.0.2.128/25",
    }, [{"device": "RTR-DHCP-2", "command": "show ip dhcp pool", "output":
         "Pool STAFF :\n Network 192.0.2.0 /24\n 0 available addresses\n"
         "Pool IOT :\n Network 198.51.100.0 /24\n 0 available addresses"}], "insufficient", True),
    case("PARTIAL-08", "NS-08", "insufficient", {
        "affected_client_subnet": "198.51.100.64/26", "matching_pool": "ANNEX-USERS",
        "expected_dns": "192.0.2.53", "name_resolution_specific": True,
    }, [{"device": "RTR-DHCP-3", "command": "show running-config | section dhcp", "output":
         "ip dhcp pool ANNEX-USERS\n network 198.51.100.64 255.255.255.192\n default-router 198.51.100.65"}], "insufficient", True),
    case("CONTRADICT-01", "NS-01", "contradictory", {
        "device": "SW-LAB-8", "expected_endpoint_interface": "GigabitEthernet3/0/42",
    }, [{"device": "SW-LAB-8", "command": "show ip interface brief", "output":
         "GigabitEthernet3/0/41 unassigned YES unset administratively down down\n"
         "GigabitEthernet3/0/42 unassigned YES unset up up"}], "contradicted", True),
    case("WRONG-DIRECTION-03", "NS-03", "contradictory", {
        "source": "192.0.2.180", "destination": "198.51.100.9", "protocol": "tcp", "port": 9443,
        "interface": "GigabitEthernet8/1", "direction": "inbound", "acl_name": "WEB-GUARD",
    }, [
        {"device": "RTR-EDGE-X", "command": "show ip interface GigabitEthernet8/1", "output":
         "GigabitEthernet8/1 is up\n Outbound access list is WEB-GUARD"},
        {"device": "RTR-EDGE-X", "command": "show access-lists WEB-GUARD", "output":
         "Extended IP access list WEB-GUARD\n  15 deny tcp 192.0.2.180 198.51.100.9 eq 9443"},
    ], "contradicted", True),
    case("CONTRADICT-05", "NS-05", "contradictory", {
        "expected_prefix": "203.0.113.64/26", "router": "RTR-BORDER-7", "default_route_intended_to_cover": False,
    }, [{"device": "RTR-BORDER-7", "command": "show ip route 203.0.113.64/26", "output":
         "Routing entry for 203.0.113.64/26\n Known via \"ospf 40\", distance 110, metric 30"}], "contradicted", True),
    case("AMBIGUOUS-01", "NS-01", "ambiguous", {
        "device": "SW-CORE-8", "expected_endpoint_interface": "GigabitEthernet1/0/5",
        "client_vlan_interface": "Vlan55", "client_subnet": "192.0.2.0/24",
        "dhcp_server_remote": True, "relay_expected": True,
    }, [
        {"device": "SW-CORE-8", "command": "show ip interface brief", "output":
         "GigabitEthernet1/0/5 unassigned YES unset administratively down down"},
        {"device": "RTR-CORE-8", "command": "show running-config interface Vlan55", "output":
         "interface Vlan55\n ip address 192.0.2.1 255.255.255.0\n no shutdown"},
    ], "supported", True),
    case("UNKNOWN-01", None, "unknown", {}, [{"device": "RTR-UNKNOWN-1", "command": "show version", "output":
         "Synthetic platform output; no scenario-specific evidence."}], None, True),
    case("TRUNK-PARTIAL-02", "NS-02", "insufficient", {
        "variant": "trunk_allowed_vlan", "expected_client_vlan": 411, "uplink": "Port-channel27",
    }, [{"device": "SW-DIST-27", "command": "show interfaces trunk", "output":
         "Port        Mode Encapsulation Status Native vlan\nPort-channel27 on 802.1q trunking 1\n"
         "Port        Vlans allowed and active in management domain"}], "insufficient", True),
]


class SeparateSyntheticCaseTests(unittest.TestCase):
    def test_evidence_ambiguity_abstains_without_label_annotations(self):
        fixture = copy.deepcopy(next(item for item in HOLDOUT if item["fixture_id"] == "HOLDOUT-AMBIGUOUS-01"))
        for field in ("case_kind", "gold", "expected", "injected_fault", "synthetic"):
            fixture.pop(field, None)

        report = build_report(fixture)

        supported = [finding.scenario_id for finding in report.findings if finding.state == "supported"]
        self.assertEqual(supported, ["NS-01", "NS-06"])
        self.assertTrue(report.abstain)
        self.assertIn("Multiple scenario rules match; a single-cause conclusion would be unsafe.",
                      report.abstention_reasons)
        self.assertFalse(any("fixture is marked ambiguous" in reason for reason in report.abstention_reasons))

    def test_separate_synthetic_case_outcomes_and_citations(self):
        self.assertEqual(len({item["fixture_id"] for item in HOLDOUT}), len(HOLDOUT))
        self.assertTrue(all(item["synthetic"] and item["data_notice"] == DATA_NOTICE for item in HOLDOUT))
        correct = 0
        mismatches = []
        for item in HOLDOUT:
            with self.subTest(case=item["fixture_id"]):
                report = build_report(item)
                gold = item["gold"]
                candidate = next((f for f in report.findings if f.scenario_id == gold["scenario_id"]), None)
                actual_state = candidate.state if candidate else None
                matched = actual_state == gold["state"] and report.abstain == gold["abstain"]
                correct += int(matched)
                if not matched:
                    mismatches.append(f"{item['fixture_id']}: state {actual_state!r}, abstain {report.abstain}; "
                                      f"expected {gold['state']!r}, abstain {gold['abstain']}")
                for finding in report.findings:
                    for citation in finding.evidence + finding.contradictory:
                        source = item["captures"][citation["capture_index"]]["output"].splitlines()[citation["line_number"] - 1]
                        self.assertEqual(citation["line"], source)
        _, authored = load_manifest(ROOT / "fixtures")
        baseline_correct = 0
        for fixture in authored:
            report = build_report(fixture)
            expected_states = fixture["expected"].get("candidate_states", {})
            candidate = next((f for f in report.findings if f.scenario_id == fixture["scenario_id"]), None)
            state_ok = (candidate.state if candidate else None) == expected_states.get(fixture["scenario_id"])
            baseline_correct += int(state_ok and report.abstain == fixture["expected"]["abstain"])
        print(f"Authored-fixture baseline exact outcome: {baseline_correct}/{len(authored)} "
              f"({baseline_correct / len(authored):.0%})")
        print(f"Separate synthetic case-set exact outcome: {correct}/{len(HOLDOUT)} ({correct / len(HOLDOUT):.0%})")
        for mismatch in mismatches:
            print("Holdout mismatch: " + mismatch)
        self.assertEqual(correct, len(HOLDOUT), "\n".join(mismatches))


if __name__ == "__main__":
    unittest.main()

