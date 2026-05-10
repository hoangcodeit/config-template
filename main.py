#!/usr/bin/env python3
"""
Entry point for the data pipeline config generator.

Usage
-----
    python main.py                        # process all tables in table_structure.csv
    python main.py --table <table_name>   # process a single table
    python main.py --help
"""

import argparse
import sys
from pathlib import Path

from src.config_generator import run
from src.config_generator.constants import FILES_DIR, OUTPUT_DIR, TEMPLATES_DIR
from src.config_generator.readers import read_table_rules, read_table_structure


def _print_summary(results) -> None:
    W = 32
    sep = "=" * (W + 42)
    print(f"\n{sep}")
    print(f"{'table_name':<{W}} {'config':<8} {'raw':<8} {'curated':<10} status")
    print("-" * (W + 42))
    for r in results:
        print(f"{r.table_name:<{W}} {r.config:<8} {r.raw:<8} {r.curated:<10} {r.status}")
    print(sep)
    ok = sum(1 for r in results if r.status == "OK")
    print(f"\nDone. {ok}/{len(results)} table(s) generated successfully.")
    print(f"Output : {OUTPUT_DIR}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate YAML pipeline config files from templates and CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python main.py\n"
            "  python main.py --table table_sample\n"
        ),
    )
    parser.add_argument("--table", metavar="TABLE_NAME", help="Process a single table only")
    args = parser.parse_args()

    structure_path = FILES_DIR / "table_structure.csv"
    rules_path     = FILES_DIR / "table_rules.csv"

    if not structure_path.exists():
        print(f"ERROR: {structure_path} not found.", file=sys.stderr)
        return 1

    table_columns = read_table_structure(structure_path)
    table_rules   = read_table_rules(rules_path)

    if args.table:
        tables = [args.table]
    else:
        tables = sorted(table_columns.keys())

    results = run(
        tables=tables,
        table_columns=table_columns,
        table_rules=table_rules,
        output_dir=OUTPUT_DIR,
        templates_dir=TEMPLATES_DIR,
    )

    for r in results:
        if r.status == "NOT_IN_CSV":
            print(f"WARNING: '{r.table_name}' not found in table_structure.csv — skipping.")
        elif r.status == "NO_CONFIG":
            print(f"WARNING: No ingestion config for '{r.table_name}' — skipping.")
        else:
            print(f"Processing: {r.table_name}")

    _print_summary(results)
    return 0 if all(r.status in {"OK", "NOT_IN_CSV", "NO_CONFIG"} for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
