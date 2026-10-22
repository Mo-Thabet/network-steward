import unittest
from network_steward.report import build_report

NOTICE = "Synthetic Cisco-style fixture data; not captured from IOS or a simulator."


def fixture(scenario, lab_map, command, output):
    return {
        "fixture_id": "PUBLIC-SYNTHETIC-REGRESSION",
        "synthetic": True,
        "data_notice": NOTICE,
        "scenario_id": scenario,
        "case_kind": "positive",
        "injected_fault": "Synthetic test condition.",
        "report": {"symptom": "Synthetic test symptom."},
        "lab_map": lab_map,
        "captures": [{"device": "R1", "command": command, "output": output}],
        "expected": {},
    }


class PublicConflictRegressionTests(unittest.TestCase):
    def test_different_prefix_no_route_does_not_support_target(self):
        case = fixture("NS-05", {
            "expected_prefix": "198.51.100.0/24", "router": "R1",
            "default_route_intended_to_cover": False,
        }, "show ip route 198.51.100.0/24",
            "% Network not in table for 203.0.113.0/24")
        report = build_report(case)
        finding = next(item for item in report.findings if item.scenario_id == "NS-05")
        self.assertEqual(finding.state, "insufficient")
        self.assertEqual(finding.evidence, [])
        self.assertEqual([item["line"] for item in finding.contradictory],
                         ["% Network not in table for 203.0.113.0/24"])
        self.assertTrue(report.abstain)

    def test_conflicting_matching_pool_counts_cause_abstention(self):
        case = fixture("NS-07", {"affected_client_subnet": "192.0.2.0/24"},
            "show ip dhcp pool",
            "Pool CLIENTS-A :\n Network: 192.0.2.0/24\n Available addresses: 0\n"
            "Pool CLIENTS-B :\n Network: 192.0.2.0/24\n Available addresses: 4")
        report = build_report(case)
        finding = next(item for item in report.findings if item.scenario_id == "NS-07")
        self.assertEqual(finding.state, "insufficient")
        self.assertEqual(finding.evidence, [])
        self.assertTrue(finding.contradictory)
        self.assertTrue(report.abstain)


if __name__ == "__main__":
    unittest.main()
