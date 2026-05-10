# Data Pipeline Config Generator

Reads a CSV table catalogue and YAML templates, then generates three configuration
files per table into `output/{table_name}/`.

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

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Generate configs for every table in table_structure.csv
python main.py

# Generate configs for one table only
python main.py --table way4_owsacs_branch
```

### Output per table

| File | Description |
|---|---|
| `output/{table}/` `{table}_config.yml` | Pipeline config (source, target, processing rules) |
| `output/{table}/raw_{table}.yml` | Raw schema — all columns minus metadata columns |
| `output/{table}/curated_{table}.yml` | Curated schema — filtered + SCD/audit columns appended |

## Adding a new table

### Option A — via `table_rules.csv` (recommended)

Add a row to `files/table_rules.csv`:

```
table_name,primary_key,order_by_columns,operation_column,exclude_columns,database_src,ingestion_type,metadata_exclude
my_table,"[""id""]","[""updated_at""]",__op,"[""__scn"",""__op""]",my_db,DELTA,""
```

> **CSV quoting rule**: array fields must be double-quoted, with inner double-quotes
> doubled. Example: `["a","b"]` in a CSV cell becomes `"[""a"",""b""]"`.
> Excel handles this automatically when you *Save As → CSV*.

### Option B — via `INGESTION_CONFIGS` in `src/config_generator/constants.py`

```python
INGESTION_CONFIGS = {
    "my_table": {
        "ingestion_type": "DELTA",          # "DELTA" | "TRANSACTION"
        "operation_column": "__op",
        "order_by_columns": ["__scn", "__optime"],
        "exclude_columns":  ["__scn", "__optime", "__op"],
        "primary_keys":     ["id"],
        "database_src":     "my_db",
        "metadata_exclude": [],
    },
}
```

Then add its columns to `files/table_structure.csv`:

```
column_name,data_type,table_name,primary_key
id,bigint,my_table,Y
name,string,my_table,
```

## CSV schemas

### `files/table_structure.csv`

| Column | Required | Description |
|---|---|---|
| `column_name` | yes | Column name |
| `data_type` | yes | Hive/Spark type (`string`, `bigint`, `timestamp`, …) |
| `table_name` | yes | Table this column belongs to |
| `primary_key` | no | Set to `Y` to mark as primary key |

### `files/table_rules.csv`

| Column | Description |
|---|---|
| `table_name` | Table identifier |
| `primary_key` | JSON array of PK column names, e.g. `"[""id""]"` |
| `order_by_columns` | JSON array — used for deduplication ordering |
| `operation_column` | CDC operation column (usually `__op`) |
| `exclude_columns` | JSON array — columns stripped from curated schema |
| `database_src` | Target database / schema name |
| `ingestion_type` | `DELTA` or `TRANSACTION` |
| `metadata_exclude` | JSON array — additional per-table metadata columns to strip |

## Ingestion types

| Type | Extra audit columns appended to curated schema |
|---|---|
| `DELTA` | `rec_effective_from`, `rec_effective_to`, `rec_current_indicator`, `rec_is_deleted`, `rec_load_dt`, `rec_hash` |
| `TRANSACTION` | `rec_load_dt` |

## Running tests

```bash
pytest                        # all tests
pytest -v                     # verbose
pytest --cov=src --cov-report=term-missing   # with coverage
```
