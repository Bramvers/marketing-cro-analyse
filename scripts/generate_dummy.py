"""Generate dummy CSVs for the Auto funnel into data/dummy/ and validate them.

Usage:  python scripts/generate_dummy.py [--seed N] [--out DIR]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cro.dummy import SEED, write_all  # noqa: E402
from cro.sources import CsvSource  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--out", type=Path, default=PROJECT_ROOT / "data" / "dummy")
    args = parser.parse_args()

    ok = True
    for table, path in write_all(args.out, seed=args.seed).items():
        report = CsvSource(table, path).load_validated().report
        status = "OK" if report.is_valid else "FOUT"
        print(f"{status:4} {path.relative_to(PROJECT_ROOT) if path.is_relative_to(PROJECT_ROOT) else path}"
              f"  ({report.n_rows} rijen, {len(report.errors)} fouten, {len(report.warnings)} waarschuwingen)")
        for issue in report.issues:
            print(f"     - [{issue.severity}] {issue.message}")
        ok &= report.is_valid
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
