"""Run one local synthetic fixture and verify every citation before display."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from network_steward import DATA_NOTICE
from network_steward.loader import load_fixture
from network_steward.report import build_report


DEFAULT_FIXTURE = Path("fixtures/NS-01/ns_01_pos_01.json")


def verify_citations(fixture: dict, report) -> None:
    for finding in report.findings:
        for citation in finding.evidence + finding.contradictory:
            capture_index = citation.get("capture_index")
            line_number = citation.get("line_number")
            if not isinstance(capture_index, int) or not 0 <= capture_index < len(fixture["captures"]):
                raise ValueError(f"{finding.scenario_id}: citation capture index is out of range")
            source_lines = fixture["captures"][capture_index]["output"].splitlines()
            if not isinstance(line_number, int) or not 1 <= line_number <= len(source_lines):
                raise ValueError(f"{finding.scenario_id}: citation line number is out of range")
            if citation.get("line") != source_lines[line_number - 1]:
                raise ValueError(f"{finding.scenario_id}: citation text differs from the input line")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run a reproducible Network Steward demo on a local fixture.")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE,
                        help="local JSON fixture path (default: fixtures/NS-01/ns_01_pos_01.json)")
    args = parser.parse_args(argv)
    path = args.fixture if args.fixture.is_absolute() else ROOT / args.fixture
    fixture = load_fixture(path)
    report = build_report(fixture)
    verify_citations(fixture, report)

    supported = [finding for finding in report.findings if finding.state == "supported"]
    print("Network Steward reproducible demo")
    print(f"Input provenance: {fixture['data_notice']}")
    print(f"Input fixture: {path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else '<external local fixture>'}")
    print(f"Fixture ID: {fixture['fixture_id']}")
    print(f"Symptom: {fixture['report']['symptom']}")
    print("Result: " + (", ".join(f"{item.scenario_id} {item.state}" for item in supported)
                          if supported else "no supported candidate"))
    print(f"Abstain: {'yes' if report.abstain else 'no'}")
    for reason in report.abstention_reasons:
        print(f"Abstention reason: {reason}")
    for finding in supported:
        for citation in finding.evidence:
            print(f"Evidence citation: capture {citation['capture_index']} line {citation['line_number']}: {citation['line']}")
        for fact in finding.expected_facts:
            print(f"Why this supports the candidate: {fact}")
        if finding.next_command:
            print(f"Suggested read-only next check (not executed): {finding.next_command}")
    print("Limit: this synthetic snapshot does not establish the current state, when a condition began, or whether it is the only cause.")
    print("Citation check: all report citations point to exact lines in the input fixture.")
    if fixture.get("data_notice") != DATA_NOTICE:
        print("Source note: input provenance is supplied by the fixture; inspect it before relying on the result.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
