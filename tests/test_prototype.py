import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
sys.path.insert(0, str(ROOT))

from network_steward import DATA_NOTICE
from network_steward.loader import FixtureError, load_fixture, load_manifest, validate_fixture
from network_steward.normalize import normalize_command
from network_steward.report import build_report, render_text


class FixtureLoadingTests(unittest.TestCase):
    def test_manifest_loads_all_19_unique_fixtures_and_each_is_synthetic(self):
        manifest, fixtures = load_manifest(FIXTURES)
        self.assertEqual(manifest["fixture_count"], 19)
        self.assertEqual(len(fixtures), 19)
        self.assertEqual(len({f["fixture_id"] for f in fixtures}), 19)
        self.assertTrue(all(f["synthetic"] is True and f["data_notice"] == DATA_NOTICE for f in fixtures))

    def test_bad_synthetic_marker_scenario_and_capture_are_rejected(self):
        good = load_fixture(FIXTURES / "NS-01" / "ns_01_pos_01.json")
        for mutate in (
            lambda f: f.update(synthetic=False),
            lambda f: f.update(scenario_id="NS-09"),
            lambda f: f.update(captures=[{"device": "x", "command": "show x"}]),
        ):
            altered = copy.deepcopy(good)
            mutate(altered)
            with self.assertRaises(FixtureError):
                validate_fixture(altered, "test-fixture")

    def test_command_normalization_handles_prompt_case_and_spacing(self):
        self.assertEqual(normalize_command("RTR-1#  SHOW   IP Route 192.0.2.0/24 "), "show ip route 192.0.2.0/24")


class RuleAndEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.fixtures = load_manifest(FIXTURES)
        cls.by_id = {f["fixture_id"]: f for f in cls.fixtures}

    def test_all_fixture_expected_states_abstention_and_next_command(self):
        for fixture in self.fixtures:
            with self.subTest(fixture=fixture["fixture_id"]):
                report = build_report(fixture)
                candidate = next(f for f in report.findings if f.scenario_id == fixture["scenario_id"]) if fixture["scenario_id"] else None
                expected = fixture["expected"]
                if candidate:
                    self.assertEqual(candidate.state, expected["candidate_states"][candidate.scenario_id])
                    self.assertEqual(candidate.next_command, expected["next_command"])
                    for selector in expected.get("evidence", []):
                        cited = [e["line"] for e in candidate.evidence]
                        self.assertTrue(any(selector["line_contains"] in line for line in cited), selector)
                self.assertEqual(report.abstain, expected["abstain"])

    def test_every_evidence_citation_is_an_exact_original_capture_line(self):
        for fixture in self.fixtures:
            with self.subTest(fixture=fixture["fixture_id"]):
                report = build_report(fixture)
                for finding in report.findings:
                    for citation in finding.evidence + finding.contradictory:
                        source = fixture["captures"][citation["capture_index"]]["output"].splitlines()[citation["line_number"] - 1]
                        self.assertEqual(citation["line"], source)
                text = render_text(report)
                self.assertIn(DATA_NOTICE, text)

    def test_both_ns02_positive_variants_match_only_ns02(self):
        for fid in ("NS-02-POS-A", "NS-02-POS-B"):
            report = build_report(self.by_id[fid])
            supported = [f.scenario_id for f in report.findings if f.state == "supported"]
            self.assertEqual(supported, ["NS-02"])

    def test_ns07_selects_exhausted_matching_pool_among_multiple_pools(self):
        fixture = copy.deepcopy(self.by_id["NS-07-POS-01"])
        fixture["captures"][0]["output"] = (
            "Pool VOICE :\n Network: 198.51.100.0/24\n Available addresses: 25\n"
            "Pool CLIENTS-20 :\n Network: 192.0.2.0/24\n Available addresses: 0"
        )
        report = build_report(fixture)
        candidate = next(f for f in report.findings if f.scenario_id == "NS-07")
        self.assertEqual(candidate.state, "supported")
        self.assertFalse(report.abstain)
        self.assertEqual([item["line"] for item in candidate.evidence],
                         [" Network: 192.0.2.0/24", " Available addresses: 0"])

    def test_one_supported_candidate_ranks_first_and_two_matches_abstain(self):
        fixture = copy.deepcopy(self.by_id["NS-01-POS-01"])
        one = build_report(fixture)
        self.assertEqual(one.findings[0].scenario_id, "NS-01")
        self.assertFalse(one.abstain)

        fixture["lab_map"].update({"client_vlan_interface": "Vlan20", "client_subnet": "192.0.2.0/24",
                                   "dhcp_server_remote": True, "relay_expected": True})
        fixture["captures"].append({"device": "RTR-DIST-01", "command": "show running-config interface Vlan20",
                                    "output": "interface Vlan20\n ip address 192.0.2.1 255.255.255.0\n no shutdown"})
        two = build_report(fixture)
        self.assertEqual([f.scenario_id for f in two.findings if f.state == "supported"], ["NS-01", "NS-06"])
        self.assertTrue(two.abstain)

    def test_missing_and_unknown_controls_abstain(self):
        for fid in ("ABSTAIN-MISSING-01", "ABSTAIN-UNKNOWN-01"):
            report = build_report(self.by_id[fid])
            self.assertTrue(report.abstain)
            self.assertTrue(any(reason for reason in report.abstention_reasons))
        self.assertEqual(self.by_id["ABSTAIN-UNKNOWN-01"]["scenario_id"], None)

    def test_ns02_variant_specific_next_commands_are_read_only(self):
        for fid, expected in (("NS-02-POS-A", "show vlan brief"), ("NS-02-POS-B", "show interfaces trunk")):
            finding = next(f for f in build_report(self.by_id[fid]).findings if f.scenario_id == "NS-02")
            self.assertEqual(finding.next_command, expected)
        for fixture in self.fixtures:
            for finding in build_report(fixture).findings:
                if finding.next_command:
                    self.assertTrue(finding.next_command.casefold().startswith("show "))


if __name__ == "__main__":
    unittest.main()
