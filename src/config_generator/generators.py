from pathlib import Path

from ruamel.yaml.comments import CommentedSeq

from .constants import DELTA_EXTRA_COLUMNS, TRANSACTION_EXTRA_COLUMNS
from .models import ColumnDef, TableConfig
from .yaml_utils import load_template, make_column_entry, make_flow_list, save_yaml


def generate_config(
    table_name: str,
    config: TableConfig,
    primary_keys: list[str],
    columns: list[ColumnDef],
    exclude_set: set[str],
    out_dir: Path,
    templates_dir: Path,
) -> bool:
    """Write ``{table_name}_config.yml`` from config_template.yml."""
    try:
        data = load_template("config_template.yml", templates_dir)

        data["name"] = table_name
        data["input"]["hive_source"]["tablename"] = table_name
        data["output"]["table"]    = table_name
        data["output"]["database"] = config.database_src
        data["schema"]["raw"]      = f"raw_{table_name}.yml"
        data["schema"]["curated"]  = f"curated_{table_name}.yml"

        exclude_cols = set(config.exclude_columns)
        dedup_cols = [
            c.column_name for c in columns
            if c.column_name not in exclude_set
            and c.column_name not in exclude_cols
        ]

        proc = data["processing"]
        proc["ingestion_type"]   = config.ingestion_type
        proc["primary_keys"]     = make_flow_list(primary_keys)
        proc["dedup_columns"]    = make_flow_list(dedup_cols)
        proc["order_by_columns"] = make_flow_list(config.order_by_columns)
        proc["operation_column"] = config.operation_column
        proc["exclude_columns"]  = make_flow_list(config.exclude_columns)

        save_yaml(data, out_dir / f"{table_name}_config.yml")
        return True
    except Exception as exc:
        print(f"  [ERROR] config  — {exc}")
        return False


def generate_raw(
    table_name: str,
    columns: list[ColumnDef],
    exclude_set: set[str],
    out_dir: Path,
    templates_dir: Path,
) -> bool:
    """Write ``raw_{table_name}.yml`` — all columns except those in exclude_set."""
    try:
        data = load_template("raw_template.yml", templates_dir)
        data["name"] = f"raw_{table_name}"

        col_seq = CommentedSeq()
        for col in columns:
            if col.column_name not in exclude_set:
                col_seq.append(make_column_entry(col.column_name, col.data_type))
        data["columns"] = col_seq

        save_yaml(data, out_dir / f"raw_{table_name}.yml")
        return True
    except Exception as exc:
        print(f"  [ERROR] raw     — {exc}")
        return False


def generate_curated(
    table_name: str,
    columns: list[ColumnDef],
    config: TableConfig,
    exclude_set: set[str],
    out_dir: Path,
    templates_dir: Path,
) -> bool:
    """
    Write ``curated_{table_name}.yml``.

    Filtering rules (applied in order):
    1. Remove columns in ``exclude_set`` (METADATA_EXCLUDE + per-table overrides),
       *unless* the column is the ``operation_column``.
    2. Remove columns in ``config.exclude_columns``,
       *unless* the column is the ``operation_column``.
    3. Append SCD/audit columns based on ``ingestion_type``.
    """
    try:
        data = load_template("curated_template.yml", templates_dir)
        data["name"] = f"curated_{table_name}"

        op_col       = config.operation_column
        exclude_cols = set(config.exclude_columns)

        col_seq = CommentedSeq()
        added: set[str] = set()
        for col in columns:
            cname = col.column_name
            if cname in exclude_set and cname != op_col:
                continue
            if cname in exclude_cols and cname != op_col:
                continue
            col_seq.append(make_column_entry(cname, col.data_type))
            added.add(cname)

        # Always carry the operation column regardless of ingestion type
        if op_col and op_col not in added:
            col_seq.append(make_column_entry(op_col, "string"))

        extras = DELTA_EXTRA_COLUMNS if config.ingestion_type == "DELTA" else TRANSACTION_EXTRA_COLUMNS
        for extra in extras:
            col_seq.append(
                make_column_entry(
                    extra["name"],
                    extra["type"],
                    nullable=extra["nullable"],
                    description=extra["description"],
                )
            )
        data["columns"] = col_seq

        save_yaml(data, out_dir / f"curated_{table_name}.yml")
        return True
    except Exception as exc:
        print(f"  [ERROR] curated — {exc}")
        return False
