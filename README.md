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

## 60-Second Demo

> **Scope:** Both examples use synthetic fixtures. Network Steward is a narrow rule-based prototype, not a general Cisco IOS parser or live network monitor. A rule score is not a probability, and a supported finding does not prove a real-world root cause.

### 1. Supported example: administratively down switch port

```bash
python -B examples/reproducible_demo.py
```

Look for `NS-01 supported` and `Abstain: no`. The evidence citation points to capture 0, line 2; compare that cited source line with the fixture to see the mapped switch port reported as administratively down. The output also explains why the rule supports this candidate and suggests `show interfaces GigabitEthernet1/0/12` as a read-only next check. The suggested command is displayed only; it is not executed.

### 2. Insufficient evidence: no captures

```bash
python -B -m network_steward.cli fixtures/ABSTAIN/abstain_missing_01.json
```

This fixture has no command captures. Look for `Abstain: yes` and the NS-02 finding marked `insufficient`; the CLI identifies the missing switchport output and suggests `show vlan brief`. It also lists the other scenarios as insufficient because this fixture provides no evidence for them. The abstention reflects the lack of captures in this fixture, not proof that the reported problem is absent.

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

**License:** No license has been added. Public availability does not grant permission to reuse or redistribute this project. See the [licensing note](license_decision_required.md). For usage, see [docs/quickstart.md](docs/quickstart.md) and [docs/architecture.md](docs/architecture.md).
