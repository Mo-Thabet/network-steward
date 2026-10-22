import json
from pathlib import Path
from typing import Any

from . import DATA_NOTICE

SCENARIOS = {f"NS-{n:02d}" for n in range(1, 9)}
KINDS = {"positive", "near_miss", "insufficient", "contradictory", "ambiguous", "unknown"}
REQUIRED = {"fixture_id", "synthetic", "data_notice", "scenario_id", "case_kind", "injected_fault", "report", "lab_map", "captures", "expected"}


class FixtureError(ValueError):
    pass


def validate_fixture(data: Any, source: str = "<memory>") -> dict[str, Any]:
    def fail(reason: str) -> None:
        raise FixtureError(f"{source}: {reason}")

    if not isinstance(data, dict):
        fail("fixture must be a JSON object")
    absent = sorted(REQUIRED - data.keys())
    if absent:
        fail("missing required fields: " + ", ".join(absent))
    if not isinstance(data["fixture_id"], str) or not data["fixture_id"].strip():
        fail("fixture_id must be a non-empty string")
    if data["synthetic"] is not True or data["data_notice"] != DATA_NOTICE:
        fail("synthetic must be true and data_notice must use the exact synthetic-data notice")
    if data["scenario_id"] is not None and data["scenario_id"] not in SCENARIOS:
        fail("scenario_id must be NS-01 through NS-08 or null")
    if data["case_kind"] not in KINDS:
        fail("case_kind is not recognized")
    if not isinstance(data["report"], dict) or not isinstance(data["report"].get("symptom"), str):
        fail("report must contain a symptom string")
    if not isinstance(data["lab_map"], dict) or not isinstance(data["captures"], list):
        fail("lab_map must be an object and captures must be a list")
    for i, cap in enumerate(data["captures"]):
        if not isinstance(cap, dict) or not all(isinstance(cap.get(k), str) for k in ("device", "command", "output")):
            fail(f"captures[{i}] must contain string device, command, and output")
    if not isinstance(data["expected"], dict):
        fail("expected must be an object")
    return data


def load_fixture(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FixtureError(f"{path}: cannot load JSON fixture: {exc}") from exc
    return validate_fixture(data, str(path))


def load_manifest(directory: str | Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    directory = Path(directory)
    path = directory / "manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FixtureError(f"{path}: cannot load manifest: {exc}") from exc
    if manifest.get("synthetic") is not True or manifest.get("data_notice") != DATA_NOTICE:
        raise FixtureError(f"{path}: manifest must carry the exact synthetic-data notice")
    fixtures = []
    ids = set()
    for item in manifest.get("fixtures", []):
        rel = item.get("path")
        if not isinstance(rel, str):
            raise FixtureError(f"{path}: each fixture entry needs a path")
        fixture = load_fixture(directory / rel)
        if fixture["fixture_id"] in ids:
            raise FixtureError(f"{path}: duplicate fixture ID {fixture['fixture_id']}")
        ids.add(fixture["fixture_id"])
        fixtures.append(fixture)
    if not fixtures:
        raise FixtureError(f"{path}: no fixtures listed")
    return manifest, fixtures
