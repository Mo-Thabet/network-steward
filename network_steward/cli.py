import argparse
import json
import sys
from pathlib import Path

from .loader import FixtureError, load_fixture, load_manifest
from .report import build_report, render_text


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate local synthetic Network Steward fixtures only.")
    parser.add_argument("path", help="path to one fixture JSON file or a directory containing manifest.json")
    parser.add_argument("--json", action="store_true", help="emit deterministic JSON reports")
    args = parser.parse_args(argv)
    path = Path(args.path)
    try:
        if path.is_dir():
            _, fixtures = load_manifest(path)
        else:
            fixtures = [load_fixture(path)]
        reports = [build_report(f) for f in fixtures]
    except FixtureError as exc:
        parser.error(str(exc))
    if args.json:
        payload = [r.as_dict() for r in reports]
        print(json.dumps(payload[0] if len(payload) == 1 else payload, indent=2, ensure_ascii=False))
    else:
        print("\n".join(render_text(r).rstrip() for r in reports))
    return 0


if __name__ == "__main__":
    sys.exit(main())
