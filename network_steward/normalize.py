import re


_INTERFACE_NAME = re.compile(
    r"^\s*([A-Za-z][A-Za-z-]*\s*\d+(?:\s*/\s*\d+)*(?:\s*\.\s*\d+)?)\b"
)
_INTERFACE_ALIASES = (
    ("tengigabitethernet", "tengigabitethernet"),
    ("gigabitethernet", "gigabitethernet"),
    ("fastethernet", "fastethernet"),
    ("ethernet", "ethernet"),
    ("te", "tengigabitethernet"),
    ("gi", "gigabitethernet"),
    ("fa", "fastethernet"),
    ("eth", "ethernet"),
)


def normalize_interface_id(interface: str) -> str:
    """Return a case- and whitespace-insensitive canonical Cisco interface ID.

    The short aliases match the forms already accepted by the experimental
    NS-02 port guard (Fa, Gi, Te, Eth). Numeric slot/port and subinterface
    components remain intact, so prefix collisions stay distinct.
    """
    value = re.sub(r"\s+", "", str(interface)).casefold()
    for alias, canonical in _INTERFACE_ALIASES:
        if value.startswith(alias) and value[len(alias):len(alias) + 1].isdigit():
            return canonical + value[len(alias):]
    return value


def interface_id_from_line(line: str) -> str | None:
    """Extract the leading interface identifier from a CLI output row."""
    match = _INTERFACE_NAME.match(line)
    return normalize_interface_id(match.group(1)) if match else None


def line_has_interface(line: str, expected: str) -> bool:
    """Compare a CLI row's complete leading interface ID with the target."""
    observed = interface_id_from_line(line)
    return observed is not None and observed == normalize_interface_id(expected)


def normalize_command(command: str) -> str:
    """Comparison-only command view. The source command/output remain untouched."""
    command = re.sub(r"^[\w.-]+(?:\([^)]*\))?[>#]\s*", "", command.strip())
    return re.sub(r"\s+", " ", command).strip().casefold()


def command_is(command: str, *needles: str) -> bool:
    normalized = normalize_command(command)
    return any(normalize_command(n) in normalized for n in needles)


def lines(captures: list[dict], *needles: str):
    """Yield exact original non-empty lines from captures with source coordinates."""
    for ci, capture in enumerate(captures):
        for li, line in enumerate(capture["output"].splitlines(), 1):
            if any(n.casefold() in line.casefold() for n in needles):
                yield {"capture_index": ci, "line_number": li, "line": line}


def command_captures(captures: list[dict], *needles: str):
    for ci, capture in enumerate(captures):
        if command_is(capture["command"], *needles):
            yield ci, capture
