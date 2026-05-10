# Data Pipeline Config Generator

Reads a CSV table catalogue and YAML templates, then generates three configuration
files per table into `output/{table_name}/`.

---

## Project structure

```
config_template/
├── src/
│   └── config_generator/
│       ├── __init__.py       # public API: run()
│       ├── constants.py      # METADATA_EXCLUDE, INGESTION_CONFIGS, paths
│       ├── models.py         # ColumnDef, TableConfig, GenerationResult
│       ├── readers.py        # CSV parsing
│       ├── yaml_utils.py     # ruamel.yaml helpers
│       ├── generators.py     # per-file generation logic
│       └── pipeline.py       # orchestrates generators
├── tests/
│   ├── conftest.py           # shared fixtures
│   ├── test_readers.py
│   └── test_generators.py
├── templates/
│   ├── config_template.yml
│   ├── raw_template.yml
│   └── curated_template.yml
├── files/
│   ├── table_structure.csv   # column catalogue
│   └── table_rules.csv       # per-table ingestion settings
├── output/                   # generated files (git-ignored)
├── main.py
└── requirements.txt
```

---

## Setup

```bash
pip install -r requirements.txt
```

---

## Usage

```bash
# Generate configs for every table in table_structure.csv
python main.py

# Generate configs for one table only
python main.py --table table_sample
```

---

## Output per table

For each table, three files are written to `output/{table_name}/`:

| File | Description |
|---|---|
| `{table}_config.yml` | Pipeline config — source, target, processing rules |
| `raw_{table}.yml` | Raw schema — all columns minus metadata columns |
| `curated_{table}.yml` | Curated schema — filtered columns + SCD/audit columns |

### Column rules per schema file

| Schema | Columns included |
|---|---|
| **raw** | All columns − `METADATA_EXCLUDE` − per-table `metadata_exclude` |
| **curated** | Same as raw, also − `exclude_columns`, always + `__op`, + audit tail |
| **dedup_columns** (in config) | All columns − `METADATA_EXCLUDE` − `exclude_columns` |

### Audit columns appended to curated schema

| `ingestion_type` | Columns appended |
|---|---|
| `DELTA` | `rec_effective_from`, `rec_effective_to`, `rec_current_indicator`, `rec_is_deleted`, `rec_load_dt`, `rec_hash` |
| `TRANSACTION` | `rec_load_dt` |

Both types always include `__op` (operation column) in the curated schema.

---

## Input files

### `files/table_structure.csv`

One row per column. Supports optional `primary_key` column.

| Column | Required | Description |
|---|---|---|
| `column_name` | yes | Column name |
| `data_type` | yes | Hive/Spark type (`string`, `bigint`, `timestamp`, …) |
| `table_name` | yes | Table this column belongs to |
| `primary_key` | no | `Y` to mark as primary key |

Example:
```
column_name,data_type,table_name,primary_key
id,bigint,my_table,Y
status,string,my_table,
created_at,timestamp,my_table,
```

### `files/table_rules.csv`

One row per table with ingestion settings.

| Column | Description |
|---|---|
| `table_name` | Table identifier |
| `primary_key` | JSON array of PK column names |
| `order_by_columns` | JSON array — ordering for deduplication |
| `operation_column` | CDC operation column (usually `__op`) |
| `exclude_columns` | JSON array — columns stripped from curated schema |
| `database_src` | Target database / schema name |
| `ingestion_type` | `DELTA` or `TRANSACTION` |
| `metadata_exclude` | JSON array — additional per-table metadata columns to strip |

Example:
```
table_name,primary_key,order_by_columns,operation_column,exclude_columns,database_src,ingestion_type,metadata_exclude
my_table,"[""id""]","[""updated_at""]",__op,"[""__scn"",""__op""]",my_db,DELTA,""
```

> **CSV quoting rule**: array fields must be double-quoted, with inner double-quotes
> doubled. `["a","b"]` becomes `"[""a"",""b""]"` in the CSV cell.
> Excel handles this automatically when you *Save As → CSV*.

---

## Adding a new table

### Option A — via `table_rules.csv` (recommended)

1. Add columns to `files/table_structure.csv`
2. Add a config row to `files/table_rules.csv`
3. Run `python main.py --table <table_name>`

### Option B — via `INGESTION_CONFIGS` in `src/config_generator/constants.py`

Use this as a fallback when a table is not in `table_rules.csv`:

```python
INGESTION_CONFIGS = {
    "my_table": {
        "ingestion_type": "DELTA",          # "DELTA" | "TRANSACTION"
        "operation_column": "__op",
        "order_by_columns": ["updated_at"],
        "exclude_columns":  ["__scn", "__op"],
        "primary_keys":     ["id"],
        "database_src":     "my_db",
        "metadata_exclude": [],
    },
}
```

---

## Running tests

```bash
pytest                                       # all tests
pytest -v                                    # verbose output
pytest --cov=src --cov-report=term-missing   # with coverage report
```
