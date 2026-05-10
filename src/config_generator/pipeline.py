from pathlib import Path

from .constants import METADATA_EXCLUDE
from .generators import generate_config, generate_curated, generate_raw
from .models import ColumnDef, GenerationResult, TableConfig
from .readers import get_table_config


def run(
    tables: list[str],
    table_columns: dict[str, list[ColumnDef]],
    table_rules: dict[str, TableConfig],
    output_dir: Path,
    templates_dir: Path,
) -> list[GenerationResult]:
    """
    Core pipeline: generate 3 YAML files for each table.

    Returns a list of :class:`GenerationResult` — one per requested table.
    Does not print anything; callers are responsible for reporting.
    """
    results: list[GenerationResult] = []

    for table_name in tables:
        if table_name not in table_columns:
            results.append(GenerationResult(table_name=table_name, status="NOT_IN_CSV"))
            continue

        config = get_table_config(table_name, table_rules)
        if config is None:
            results.append(GenerationResult(table_name=table_name, status="NO_CONFIG"))
            continue

        columns = table_columns[table_name]

        effective_exclude = set(METADATA_EXCLUDE) | set(config.metadata_exclude)

        pk_from_csv = [c.column_name for c in columns if c.primary_key]
        primary_keys = pk_from_csv if pk_from_csv else config.primary_keys

        out_dir = output_dir / table_name
        out_dir.mkdir(parents=True, exist_ok=True)

        cfg_ok = generate_config(table_name, config, primary_keys, columns, effective_exclude, out_dir, templates_dir)
        raw_ok = generate_raw(table_name, columns, effective_exclude, out_dir, templates_dir)
        cur_ok = generate_curated(table_name, columns, config, effective_exclude, out_dir, templates_dir)

        status = "OK" if all([cfg_ok, raw_ok, cur_ok]) else "PARTIAL"
        results.append(
            GenerationResult(
                table_name=table_name,
                config="OK" if cfg_ok else "FAIL",
                raw="OK" if raw_ok else "FAIL",
                curated="OK" if cur_ok else "FAIL",
                status=status,
            )
        )

    return results
