# Network Steward architecture and scope

## Input and parsing

This staged prototype accepts the synthetic JSON fixture format used in `fixtures/`. A fixture includes a provenance marker, case and scenario identifiers, a symptom, operational `lab_map` context, captured command text, and expected labels used by tests. At runtime the rules use report context, the lab map, and captures; they do not use expected labels to choose diagnoses.

`loader.py` validates required structure, types, supported scenario identifiers, case kinds, and the explicit synthetic-data notice. `normalize.py` normalizes command and interface forms for matching while preserving original capture text. It does not parse arbitrary Cisco output or fully validate that every scenario-specific context field is present.

## Rules and citations

`rules.py` implements narrow text matching for NS-01 through NS-08. `experimental_conflicts.py` applies additional ambiguity guards to selected otherwise-supported results. Matching patterns are limited to formats represented by the authored fixtures.

Findings can be `supported`, `contradicted`, or `insufficient`. Evidence and contradictory evidence include a zero-based capture index, one-based line number, and exact original line. The rule descriptions and limitations are detailed in this package's quickstart and source.

## Conflicts and abstention

Selected same-capture conflicts can downgrade an otherwise-supported finding to `insufficient`. The engine abstains when no candidate is supported, multiple candidates are supported, the scenario is unmapped, or an ambiguity guard fires. These behaviors do not prove a fault is absent or that a configuration is invalid; they describe only the supplied text and coded expectations.

## Evaluation included here

The package contains synthetic fixtures, a citation-checking demo, and curated tests for fixture validation, expected fixture outcomes, exact citations, synthetic evidence removal and conflict mutations, separately authored synthetic case examples, and a small ACL direction regression. Run the staged suite with `python -B -m unittest discover -s tests -v`.

This staging package intentionally omits historical campaigns, Packet Tracer transcripts/projects, and the separate Packet Tracer evidence loader. The staged tests are not the full historical project suite and their results are not independent validation.

## Limits

Network Steward is not a general Cisco IOS parser. It does not contact equipment, execute suggested commands, validate topology or device syntax, prove current state or event timing, establish sole root cause, or measure production accuracy. All included fixture inputs are synthetic examples; no live-device validation is included.

