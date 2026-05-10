import csv
import json
from pathlib import Path

from .constants import INGESTION_CONFIGS
from .models import ColumnDef, TableConfig


def read_table_structure(path: Path) -> dict[str, list[ColumnDef]]:
    """
    Returns {table_name: [ColumnDef, ...]} from table_structure.csv.
    The optional ``primary_key`` column marks a column as PK when the value is "Y".
    """
    tables: dict[str, list[ColumnDef]] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            row = {k.strip(): v.strip() for k, v in raw.items() if k}
            table = row.get("table_name", "")
            if not table:
                continue
            tables.setdefault(table, []).append(
                ColumnDef(
                    column_name=row.get("column_name", ""),
                    data_type=row.get("data_type", "string"),
                    primary_key=row.get("primary_key", "").upper() == "Y",
                )
            )
    return tables


def read_table_rules(path: Path) -> dict[str, TableConfig]:
    """
    Returns {table_name: TableConfig} from table_rules.csv.

    Array fields (primary_key, order_by_columns, exclude_columns, metadata_exclude)
    must be JSON-encoded in the CSV, e.g. ``"[""col_a"",""col_b""]"``.
    """
    rules: dict[str, TableConfig] = {}
    if not path.exists():
        return rules
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            row = {k.strip(): v.strip() for k, v in raw.items() if k}
            table = row.get("table_name", "")
            if not table:
                continue
            rules[table] = TableConfig(
                table_name=table,
                ingestion_type=row.get("ingestion_type", "DELTA"),  # type: ignore[arg-type]
                operation_column=row.get("operation_column", "__op"),
                order_by_columns=_parse_list(row.get("order_by_columns", "")),
                exclude_columns=_parse_list(row.get("exclude_columns", "")),
                primary_keys=_parse_list(row.get("primary_key", "")),
                database_src=row.get("database_src", ""),
                metadata_exclude=_parse_list(row.get("metadata_exclude", "")),
            )
    return rules


def get_table_config(table_name: str, table_rules: dict[str, TableConfig]) -> TableConfig | None:
    """table_rules (from CSV) takes priority; falls back to INGESTION_CONFIGS dict."""
    if table_name in table_rules:
        return table_rules[table_name]
    raw = INGESTION_CONFIGS.get(table_name)
    if raw:
        return TableConfig(
            table_name=table_name,
            ingestion_type=raw.get("ingestion_type", "DELTA"),  # type: ignore[arg-type]
            operation_column=raw.get("operation_column", "__op"),
            order_by_columns=list(raw.get("order_by_columns", [])),
            exclude_columns=list(raw.get("exclude_columns", [])),
            primary_keys=list(raw.get("primary_keys", [])),
            database_src=raw.get("database_src", ""),
            metadata_exclude=list(raw.get("metadata_exclude", [])),
        )
    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_list(value: str) -> list[str]:
    """Parse a JSON-array string like ``'["a","b"]'`` into a Python list."""
    value = value.strip()
    if not value:
        return []
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else [str(result)]
    except (json.JSONDecodeError, ValueError):
        inner = value.strip("[]")
        return [v.strip().strip('"').strip("'") for v in inner.split(",") if v.strip()]
