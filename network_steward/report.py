from . import DATA_NOTICE
from .models import Report
from .rules import evaluate


def build_report(fixture: dict) -> Report:
    findings, abstain, reasons = evaluate(fixture)
    return Report(fixture["fixture_id"], fixture["report"]["symptom"], findings, abstain, reasons,
                  fixture.get("data_notice", DATA_NOTICE))


def render_text(report: Report) -> str:
    rows = [report.data_notice, f"Fixture: {report.fixture_id}", f"Reported symptom: {report.symptom}",
            f"Abstain: {'yes' if report.abstain else 'no'}"]
    for reason in report.abstention_reasons:
        rows.append(f"Abstention reason: {reason}")
    rows.append("Candidate findings (ranked by explicit rule matches):")
    for f in report.findings:
        rows.append(f"- {f.scenario_id}: {f.state} (rule score {f.score})")
        for expected in f.expected_facts:
            rows.append(f"  Expected lab fact: {expected}")
        for ev in f.evidence:
            rows.append(f"  Evidence [capture {ev['capture_index']} line {ev['line_number']}]: {ev['line']}")
        for ev in f.contradictory:
            rows.append(f"  Contradictory evidence [capture {ev['capture_index']} line {ev['line_number']}]: {ev['line']}")
        for missing in f.missing:
            rows.append(f"  Missing: {missing}")
        if f.next_command:
            rows.append(f"  Safe next read-only command: {f.next_command}")
    if report.data_notice == DATA_NOTICE:
        rows.append("Scope limit: synthetic fixture only; no live-device validation or root-cause inference beyond these eight rules.")
    elif "Packet Tracer simulated output" in report.data_notice:
        rows.append("Scope limit: Packet Tracer simulation output only; no physical-device validation or root-cause inference beyond these eight rules.")
    else:
        rows.append("Scope limit: local text input; source provenance is stated by the input dataset.")
    return "\n".join(rows) + "\n"
