from dataclasses import dataclass, field
from typing import Any


@dataclass
class Finding:
    scenario_id: str
    state: str
    score: int = 0
    evidence: list[dict[str, Any]] = field(default_factory=list)
    contradictory: list[dict[str, Any]] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    expected_facts: list[str] = field(default_factory=list)
    next_command: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id, "state": self.state, "score": self.score,
            "evidence": self.evidence, "contradictory_evidence": self.contradictory,
            "missing": self.missing, "expected_facts": self.expected_facts,
            "next_command": self.next_command,
        }


@dataclass
class Report:
    fixture_id: str
    symptom: str
    findings: list[Finding]
    abstain: bool
    abstention_reasons: list[str]
    data_notice: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "data_notice": self.data_notice, "fixture_id": self.fixture_id,
            "symptom": self.symptom, "abstain": self.abstain,
            "abstention_reasons": self.abstention_reasons,
            "candidates": [f.as_dict() for f in self.findings],
        }
