# Staged test results

Environment: existing Python 3.12.10; standard library only. No dependencies were installed or downloaded.

Commands run from the staging directory:

```powershell
python -B examples/reproducible_demo.py
python -B -m network_steward.cli fixtures/NS-01/ns_01_pos_01.json
python -B -m network_steward.cli fixtures --json
python -B -m unittest discover -s tests -v
```

Results:

- Demo: exit 0. It printed `NS-01 supported`, `Abstain: no`, the exact source citation `capture 0 line 2`, the evidence explanation, a suggested read-only command marked not executed, and a synthetic-snapshot limitation. All report citations matched exact fixture lines.
- Single-fixture CLI: exit 0; supported scenario output was generated from the named synthetic JSON fixture.
- Directory JSON CLI: exit 0; processed the staged manifest and emitted a JSON report for the staged fixture set.
- Staged suite: exit 0, **19 tests passed**. The suite includes fixture schema and result checks, source-line citation checks, a synthetic 14-case separately authored set, 9 evidence-removal and 9 conflict-injection mutations, ACL-direction cases, two self-contained NS-05/NS-07 regressions, and demo smoke coverage.

This is the staged suite only. The previous readiness report recorded 48 tests in the full project suite; that suite was not rerun during staging. These 19 tests are not equivalent to the full suite, omit tests requiring historical evaluation datasets or Packet Tracer materials, and do not establish independent validation, real-device accuracy, or production performance.

