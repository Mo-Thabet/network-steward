# Network Steward prototype

Network Steward is a local, rule-based prototype for eight narrow network diagnostic scenarios. It reads labeled synthetic Cisco-style fixture JSON, prints candidate states with source-line citations, and suggests read-only checks. It does not connect to devices, execute commands, establish root cause, or claim production accuracy.

## Requirements

- Python 3.10 or later.
- Python standard library only; no third-party packages.
- Run commands from this directory.

## Run the demo

```powershell
python -B examples/reproducible_demo.py
```

The demo reads `fixtures/NS-01/ns_01_pos_01.json`, a synthetic fixture that was not captured from IOS or a simulator. It checks citations against the input lines before printing the result.

## Run a fixture or all fixtures

```powershell
python -B -m network_steward.cli fixtures/NS-01/ns_01_pos_01.json
python -B -m network_steward.cli fixtures --json
```

## Run the staged tests

```powershell
python -B -m unittest discover -s tests -v
```

The staged tests are a curated, self-contained synthetic suite. They are not equivalent to the full project suite and do not include historical campaign or Packet Tracer evidence tests.

See [docs/quickstart.md](docs/quickstart.md) and [docs/architecture.md](docs/architecture.md). No license has been added; see [license_decision_required.md](license_decision_required.md) before redistribution.
