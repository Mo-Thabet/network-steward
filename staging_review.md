# Public staging review

## Decision

The GitHub repository is currently public. This review covers the staged tree, which is runnable with the Python standard library and contains no historical campaign directory, Packet Tracer project/transcript, machine-specific preservation record, or local environment output. Rights-holder confirmation and an approved license remain unresolved; public availability does not establish a license grant or reuse permission.

## Candidate audit and classification

| Candidate category | Decision | Review notes |
|---|---|---|
| Required runtime source | Included: eight `network_steward/` modules. | `__init__.py`, `cli.py`, `loader.py`, `models.py`, `normalize.py`, `rules.py`, `experimental_conflicts.py`, and `report.py` form the fixture-to-report path. Standard-library imports only. |
| Public documentation | Included: staged `README.md`, `docs/quickstart.md`, `docs/architecture.md`. | The root README was written for this stage, rather than copied with its long historical campaign narrative. Claims are limited to source-supported behavior and synthetic examples. |
| Safe synthetic example | Included: `examples/reproducible_demo.py` and the 19 JSON fixtures plus `fixtures/manifest.json`. | Every fixture is labeled synthetic. The demo checks citation coordinates and exact source-line text. No IOS capture or simulator output is represented as synthetic data. |
| Self-contained test | Included: six test modules under `tests/`. | They use staged source and staged synthetic fixtures or inline synthetic cases. Two campaign-bound NS-05/NS-07 checks were replaced with standalone synthetic regression inputs. |
| Historical evaluation artifact | Excluded. | All historical campaign directories, reports, manifests, frozen evaluation cases, and local replay outputs are excluded. |
| Packet Tracer or other external evidence | Excluded. | Packet Tracer loader/CLI modules, `.pkt` projects, manually transcribed evidence cases, screenshots, and run logs are not in this stage. No live-device evidence is included. |
| Generated or machine-specific artifact | Excluded. | Python cache files were removed before manifest creation. No local path, preservation sidecar, environment state, or run log is staged. |
| Uncertain licensing or ownership | Pending approval for every staged file. | No license/notice or documented grant was found. The available records do not establish redistribution rights for all copied code, docs, tests, demo, and fixtures. `license_decision_required.md` records the decision required; no license text was added. |

### Included file purposes

| Staged path | Purpose |
|---|---|
| `README.md` | Main entry point, prerequisites, exact demo/CLI/test commands, scope, and license-status link. |
| `license_decision_required.md` | Records that rights-holder and license approval are required; is not a license grant. |
| `staging_review.md` | This candidate classification, file inventory, exclusions, and release blockers. |
| `test_results.md` | Exact staged commands, observed results, test count, and scope limitations. |
| `staging_manifest.sha256` | SHA-256 index of every other staged file; this sidecar does not hash itself. Each digest covers the exact Git-tree bytes for that path (UTF-8 text with LF line endings; no other normalization). Entries cover every tracked file except this sidecar, including `license_decision_required.md`. |
| `docs/quickstart.md` | Python requirement, synthetic demo and CLI usage, and result interpretation. |
| `docs/architecture.md` | Confirmed synthetic input pipeline, rules, citations, conflict handling, abstention, evaluation boundary, and limitations. |
| `examples/reproducible_demo.py` | One-command synthetic NS-01 example with citation validation. |
| `fixtures/manifest.json` | Index of the 19 staged synthetic fixtures. |
| `fixtures/ABSTAIN/abstain_missing_01.json` | Synthetic missing-evidence abstention fixture. |
| `fixtures/ABSTAIN/abstain_unknown_01.json` | Synthetic unknown-scenario abstention fixture. |
| `fixtures/NS-01/ns_01_nm_01.json` | Synthetic NS-01 near-miss fixture. |
| `fixtures/NS-01/ns_01_pos_01.json` | Synthetic NS-01 positive fixture used by the demo. |
| `fixtures/NS-02/ns_02_nm_01.json` | Synthetic NS-02 near-miss fixture. |
| `fixtures/NS-02/ns_02_pos_a.json` | Synthetic NS-02 access-VLAN positive fixture. |
| `fixtures/NS-02/ns_02_pos_b.json` | Synthetic NS-02 trunk-VLAN positive fixture. |
| `fixtures/NS-03/ns_03_nm_01.json` | Synthetic NS-03 near-miss fixture. |
| `fixtures/NS-03/ns_03_pos_01.json` | Synthetic NS-03 positive fixture. |
| `fixtures/NS-04/ns_04_nm_01.json` | Synthetic NS-04 near-miss fixture. |
| `fixtures/NS-04/ns_04_pos_01.json` | Synthetic NS-04 positive fixture. |
| `fixtures/NS-05/ns_05_nm_01.json` | Synthetic NS-05 near-miss fixture. |
| `fixtures/NS-05/ns_05_pos_01.json` | Synthetic NS-05 positive fixture. |
| `fixtures/NS-06/ns_06_nm_01.json` | Synthetic NS-06 near-miss fixture. |
| `fixtures/NS-06/ns_06_pos_01.json` | Synthetic NS-06 positive fixture. |
| `fixtures/NS-07/ns_07_nm_01.json` | Synthetic NS-07 near-miss fixture. |
| `fixtures/NS-07/ns_07_pos_01.json` | Synthetic NS-07 positive fixture. |
| `fixtures/NS-08/ns_08_nm_01.json` | Synthetic NS-08 near-miss fixture. |
| `fixtures/NS-08/ns_08_pos_01.json` | Synthetic NS-08 positive fixture. |
| `network_steward/__init__.py` | Package marker and synthetic data notice. |
| `network_steward/cli.py` | Local JSON fixture file/directory command-line entry point. |
| `network_steward/experimental_conflicts.py` | Narrow ambiguity checks applied to selected otherwise-supported findings. |
| `network_steward/loader.py` | Synthetic fixture and manifest parsing/validation. |
| `network_steward/models.py` | Finding and report data structures. |
| `network_steward/normalize.py` | Command/interface normalization and source-line extraction helpers. |
| `network_steward/report.py` | Builds findings and renders text/JSON reports. |
| `network_steward/rules.py` | NS-01 through NS-08 text-matching rules. |
| `tests/test_adversarial.py` | Nine synthetic decisive-evidence removals and nine synthetic conflict injections. |
| `tests/test_holdout.py` | Separate synthetic case assertions and citation checks; not real-world validation. |
| `tests/test_ns03_outgoing_acl_direction.py` | Inline synthetic ACL direction and ambiguity cases. |
| `tests/test_prototype.py` | Fixture schema, all-fixture outcomes, citations, abstention, and next-command checks; campaign-dependent methods omitted. |
| `tests/test_public_conflict_regressions.py` | Standalone synthetic NS-05 mismatched-prefix and NS-07 conflicting-pool regression checks. |
| `tests/test_reproducible_demo.py` | Smoke test for the documented demo command. |

## Excluded test dependencies

The following original tests were not staged because their inputs are in historical evaluations or external evidence trees:

- `test_ns01_interface_matching.py`: reads `data/packet_tracer/NS-01/case.json`.
- `test_ns03_ios_host_acl_regression.py`: reads a manually transcribed Packet Tracer evidence case.
- `test_packet_tracer_evaluation.py`: imports an evaluation runner and its campaign inputs.
- `test_packet_tracer_evidence_only.py`: reads evidence/case files under `evaluation/` and `data/packet_tracer/`.
- `test_packet_tracer_ingest.py`: reads a Packet Tracer evidence fixture.
- `test_route_no_route_regression.py`: reads a frozen v4 evaluation case.
- Two NS-05/NS-07 methods from `test_prototype.py`: read frozen v3 evaluation cases; their target behaviors are tested with new inline synthetic cases in this stage.

The full historical 48-test suite was not claimed as equivalent. The stage's 19 tests provide a smaller, reproducible synthetic test bundle.

## License and dependency review

No project license, copyright/ownership statement, third-party notice, or dependency/build manifest was found by the candidate-file scan. Staged runtime imports use Python standard-library modules; the documented requirement is Python 3.10 or later, with no third-party packages. No dependency file was added because there are no third-party runtime dependencies to declare. A rights holder must confirm authority over every staged file and choose/approve the license before redistribution.

## Safety and independence checks

A text scan of all 42 staged files found zero matches for checked absolute Windows user paths, credential-assignment patterns, email addresses, or the checked personal username marker. This is a heuristic scan, not a full security audit. All staged fixtures are explicitly synthetic; no real personal or customer network data was identified in the included fixture set. The stage contains no `.pkt` or manual Packet Tracer evidence.

The demo, CLI, and tests were run from the staging directory alone. The staged source/tests contain no references to historical `evaluation/` campaign paths or Packet Tracer data paths. The demo's supported result is a synthetic rule match, not a live diagnosis. The separate 14-case test set and mutation checks are synthetic regression tests and do not establish independent validation or production accuracy.

## Remaining public-release blockers

1. Rights-holder confirmation and an approved license, with any required notices.
2. A final human review of the exact staged tree and any applicable third-party ownership/attribution obligations.
3. Determine and document any further publication or redistribution steps after resolving rights and licensing.

## Preservation

Staging was performed by copying selected files into this new directory. The initial preservation check found no source, historical report, frozen dataset, Packet Tracer file, or existing hash record had changed. After staging, `python -B evaluation/network_steward_release_candidate_2026-10-20_01/verify_preservation.py` reported 54 checked files, zero mismatches, and `historical_files_unchanged: true`. This documentation-only correction updates the README and this review; the staging manifest records their refreshed hashes. No implementation, test, test-result, or fixture files changed.

