"""Synthetic mutation checks for evidence sensitivity and conflict abstention."""

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
sys.path.insert(0, str(ROOT))

from network_steward import DATA_NOTICE
from network_steward.loader import load_manifest
from network_steward.report import build_report


def _target(report, scenario_id):
    return next(f for f in report.findings if f.scenario_id == scenario_id)


def _without_cited_evidence(fixture, finding):
    """Delete all exact source lines cited as support for this candidate."""
    altered = copy.deepcopy(fixture)
    citations = {(item["capture_index"], item["line_number"]) for item in finding.evidence}
    for ci, capture in enumerate(altered["captures"]):
        kept = [line for li, line in enumerate(capture["output"].splitlines(), 1)
                if (ci, li) not in citations]
        capture["output"] = "\n".join(kept)
    altered["fixture_id"] = "MUTATION-REMOVE-" + fixture["fixture_id"]
    altered["case_kind"] = "insufficient"
    altered["injected_fault"] = "Synthetic mutation: all cited support lines were removed."
    return altered


def _append(fixture, capture_index, *lines):
    altered = copy.deepcopy(fixture)
    capture = altered["captures"][capture_index]
    capture["output"] += "\n" + "\n".join(lines)
    altered["fixture_id"] = "MUTATION-CONFLICT-" + fixture["fixture_id"]
    altered["case_kind"] = "contradictory"
    altered["injected_fault"] = "Synthetic mutation: plausible conflicting evidence was appended."
    return altered


def _insert_into_pool(fixture, capture_index, pool, line):
    """Insert a synthetic directive inside one named DHCP pool block."""
    altered = copy.deepcopy(fixture)
    capture = altered["captures"][capture_index]
    lines = capture["output"].splitlines()
    pool_header = f"ip dhcp pool {pool}".casefold()
    start = next(i for i, value in enumerate(lines) if value.casefold() == pool_header)
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("ip dhcp pool ")), len(lines))
    lines.insert(end, line)
    capture["output"] = "\n".join(lines)
    altered["fixture_id"] = "MUTATION-CONFLICT-" + fixture["fixture_id"]
    altered["case_kind"] = "contradictory"
    altered["injected_fault"] = "Synthetic mutation: conflicting DNS was added within the matching DHCP pool."
    return altered


def _conflict_mutations(by_id):
    """One plausible contradictory observation per scenario, including NS-02 access and trunk."""
    return [
        ("NS-01-ADMIN-UP", by_id["NS-01-POS-01"], "NS-01",
         _append(by_id["NS-01-POS-01"], 0,
                 "GigabitEthernet1/0/12  unassigned      YES unset  up                    up")),
        ("NS-02-ACCESS-EXPECTED-VLAN", by_id["NS-02-POS-A"], "NS-02",
         _append(by_id["NS-02-POS-A"], 0, "Access Mode VLAN: 20 (CLIENT-20)")),
        ("NS-02-TRUNK-EXPECTED-VLAN", by_id["NS-02-POS-B"], "NS-02",
         _append(by_id["NS-02-POS-B"], 0, "GigabitEthernet0/24      10,20,30")),
        ("NS-03-OPPOSITE-ACL-DIRECTION", by_id["NS-03-POS-01"], "NS-03",
         _append(by_id["NS-03-POS-01"], 0, "  Outbound access list is EDGE-IN")),
        ("NS-04-EXPECTED-PEER-FULL", by_id["NS-04-POS-01"], "NS-04",
         _append(by_id["NS-04-POS-01"], 0,
                 "203.0.113.2       1 FULL/DR         192.0.2.2       Gi0/1")),
        ("NS-05-ROUTE-PRESENT", by_id["NS-05-POS-01"], "NS-05",
         _append(by_id["NS-05-POS-01"], 0,
                 "Routing entry for 198.51.100.0/24", "Known via \"ospf 10\"")),
        ("NS-06-HELPER-PRESENT", by_id["NS-06-POS-01"], "NS-06",
         _append(by_id["NS-06-POS-01"], 0, " ip helper-address 192.0.2.10")),
        ("NS-07-POOL-HAS-SPACE", by_id["NS-07-POS-01"], "NS-07",
         _append(by_id["NS-07-POS-01"], 0, " Available addresses: 1")),
        ("NS-08-EXPECTED-DNS-ALSO-PRESENT", by_id["NS-08-POS-01"], "NS-08",
         _insert_into_pool(by_id["NS-08-POS-01"], 0, "CLIENTS-20", " dns-server 203.0.113.53")),
    ]


class AdversarialMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, fixtures = load_manifest(FIXTURES)
        cls.by_id = {fixture["fixture_id"]: fixture for fixture in fixtures}

    def test_decisive_evidence_removal_and_conflict_injection(self):
        removals = []
        # Exercise both intentionally separate NS-02 variants.
        for fid in ("NS-01-POS-01", "NS-02-POS-A", "NS-02-POS-B", "NS-03-POS-01",
                    "NS-04-POS-01", "NS-05-POS-01", "NS-06-POS-01",
                    "NS-07-POS-01", "NS-08-POS-01"):
            original = self.by_id[fid]
            baseline = build_report(original)
            sid = original["scenario_id"]
            removed = _without_cited_evidence(original, _target(baseline, sid))
            removals.append((removed, sid))

        cases = []
        for fixture, sid in removals:
            self.assertTrue(fixture["synthetic"] and fixture["data_notice"] == DATA_NOTICE)
            report = build_report(fixture)
            self.assertEqual(report.data_notice, DATA_NOTICE)
            candidate = _target(report, sid)
            cases.append((fixture["fixture_id"], candidate.state, report.abstain,
                          candidate.state != "supported" and report.abstain))

        conflicts = []
        for label, original, sid, fixture in _conflict_mutations(self.by_id):
            self.assertTrue(fixture["synthetic"] and fixture["data_notice"] == DATA_NOTICE)
            report = build_report(fixture)
            self.assertEqual(report.data_notice, DATA_NOTICE)
            candidate = _target(report, sid)
            conflicts.append((label, fixture, report, candidate.state,
                              candidate.state != "supported" and report.abstain))

        # Citation coordinates must still point to exact source lines after mutations.
        for fixture, report in [(f, build_report(f)) for f, _ in removals] + [
                (fixture, report) for _, fixture, report, _, _ in conflicts]:
            for finding in report.findings:
                for citation in finding.evidence + finding.contradictory:
                    source = fixture["captures"][citation["capture_index"]]["output"].splitlines()[citation["line_number"] - 1]
                    self.assertEqual(citation["line"], source)

        # Simple carry-forward baseline: keep the original supported diagnosis
        # and non-abstention for every mutated positive case without re-reading evidence.
        baseline_total = len(removals) + len(conflicts)
        baseline_safe = 0
        removal_safe = sum(item[3] for item in cases)
        conflict_safe = sum(item[4] for item in conflicts)
        mismatches = [f"{label}: {state}, abstain={abstain}" for label, state, abstain, ok in cases if not ok]
        mismatches += [f"{label}: {state}, abstain=False" for label, _, _, state, ok in conflicts if not ok]
        print(f"Synthetic decisive-evidence removals handled safely: {removal_safe}/{len(cases)}")
        print(f"Synthetic contradiction injections handled safely: {conflict_safe}/{len(conflicts)}")
        print(f"Synthetic simple carry-forward baseline safe outcomes: {baseline_safe}/{baseline_total}")
        for mismatch in mismatches:
            print("Adversarial mismatch: " + mismatch)
        self.assertEqual(len(cases), 9)
        self.assertEqual(len(conflicts), 9)
        self.assertEqual(removal_safe, 9, "Evidence removal must continue to trigger safe abstention.")
        self.assertEqual(conflict_safe, 9, "Every injected conflict must avoid a supported, non-abstaining diagnosis.")
        for label, _, report, state, safe in conflicts:
            with self.subTest(conflict=label):
                self.assertTrue(safe)
                self.assertTrue(report.abstain)
                self.assertNotEqual(state, "supported")
        for label, _, report, state, _ in conflicts:
            if label in {"NS-01-ADMIN-UP", "NS-02-ACCESS-EXPECTED-VLAN",
                         "NS-02-TRUNK-EXPECTED-VLAN", "NS-03-OPPOSITE-ACL-DIRECTION",
                         "NS-08-EXPECTED-DNS-ALSO-PRESENT"}:
                with self.subTest(experimental_guard=label):
                    self.assertEqual(state, "insufficient")
                    self.assertTrue(report.abstention_reasons)


if __name__ == "__main__":
    unittest.main()
