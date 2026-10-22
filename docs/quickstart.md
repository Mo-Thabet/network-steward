# Network Steward quickstart

Network Steward is a local Python prototype for a small set of evidence-backed network diagnostics. It reads fixture JSON and prints candidate states; it does not connect to a network or execute the suggested commands.

## Requirements

- Python 3.10 or later.
- Standard library only; no third-party dependency installation is required.
- Run commands from the project root.

## Reproducible example

```powershell
python examples/reproducible_demo.py
```

The default input is `fixtures/NS-01/ns_01_pos_01.json`, a **synthetic Cisco-style fixture**, not IOS output or Packet Tracer output. The script checks that every evidence citation refers to the exact input capture line before displaying the result. Expected output includes `NS-01 supported`, `Abstain: no`, a citation to capture 0 line 2, the rule's mapped-interface fact, and the suggested read-only check `show interfaces GigabitEthernet1/0/12`. The command is not run by the script.

To use the standard CLI instead:

```powershell
python -m network_steward.cli fixtures/NS-01/ns_01_pos_01.json
```

To emit JSON:

```powershell
python -m network_steward.cli fixtures/NS-01/ns_01_pos_01.json --json
```

The CLI accepts one local fixture JSON file or a directory with `manifest.json`. It does not open network connections. To check the demo command and project tests:

```powershell
python -B -m unittest discover -s tests -v
```

## Reading a result

`supported` means a rule matched its coded text preconditions in the supplied captures. `contradicted` means that rule found an observation inconsistent with the described condition. `insufficient` means the rule could not establish either result from the available text or an ambiguity guard reduced confidence. `Abstain: yes` means the engine does not present the evidence as a single selected diagnosis. A suggested next check is a read-only command string for an engineer to consider; Network Steward does not execute it.

See [architecture.md](architecture.md) for the input flow, rule scope, citation behavior, conflicts, and evaluation limits.
