"""Regression tests for IOS `Outgoing access list` attachment wording."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from network_steward.report import build_report


def fixture(direction="inbound", attachment=None):
    attachment = attachment or f" {direction.title()} access list is EDGE-IN"
    return {
        "fixture_id": "NS03-OUTGOING-REGRESSION", "synthetic": True,
        "data_notice": "Synthetic Cisco-style fixture data; not captured from IOS or a simulator.",
        "scenario_id": "NS-03", "case_kind": "positive", "injected_fault": "synthetic ACL condition",
        "report": {"symptom": "synthetic failed flow", "device": "R1"},
        "lab_map": {"source": "10.24.8.19", "destination": "172.20.40.9", "protocol": "tcp",
                    "port": "9443", "interface": "GigabitEthernet0/0", "direction": direction,
                    "acl_name": "EDGE-IN"},
        "captures": [
            {"device": "R1", "command": "show ip interface GigabitEthernet0/0", "output": attachment},
            {"device": "R1", "command": "show access-lists EDGE-IN",
             "output": " 40 deny tcp host 10.24.8.19 host 172.20.40.9 eq 9443"},
        ],
        "expected": {},
    }


class OutgoingAclDirectionTests(unittest.TestCase):
    def test_outgoing_alias_supports_outbound_flow_mapping(self):
        report = build_report(fixture("outbound", " Outgoing access list is EDGE-IN"))
        finding = next(item for item in report.findings if item.scenario_id == "NS-03")
        self.assertEqual(finding.state, "supported")
        self.assertIn(" Outgoing access list is EDGE-IN", [x["line"] for x in finding.evidence])

    def test_inbound_and_outgoing_same_acl_trigger_ambiguity_guard(self):
        report = build_report(fixture("inbound", " Inbound access list is EDGE-IN\n Outgoing access list is EDGE-IN"))
        finding = next(item for item in report.findings if item.scenario_id == "NS-03")
        self.assertEqual(finding.state, "insufficient")
        self.assertTrue(report.abstain)

    def test_outgoing_different_acl_does_not_trigger_same_acl_guard(self):
        report = build_report(fixture("inbound", " Inbound access list is EDGE-IN\n Outgoing access list is OTHER-ACL"))
        finding = next(item for item in report.findings if item.scenario_id == "NS-03")
        self.assertEqual(finding.state, "supported")
        self.assertFalse(report.abstain)


if __name__ == "__main__":
    unittest.main()
