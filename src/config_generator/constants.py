from pathlib import Path

PROJECT_ROOT  = Path(__file__).parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
FILES_DIR     = PROJECT_ROOT / "files"
OUTPUT_DIR    = PROJECT_ROOT / "output"

METADATA_EXCLUDE: list[str] = [
    "__op", "__koptime", "__scn", "__optime",
    "__ktopic", "__kpart", "__koffset", "__ktime",
    "__table", "__sha", "ds",
]

# Fallback for tables not present in table_rules.csv
INGESTION_CONFIGS: dict[str, dict] = {
    "way4_owsacs_branch": {
        "ingestion_type": "DELTA",
        "operation_column": "__op",
        "order_by_columns": ["__scn", "__optime", "__koffset"],
        "exclude_columns": ["__scn", "__optime", "__offset", "__op"],
        "primary_keys": [],
        "database_src": "",
        "metadata_exclude": [],
    },
    # Add more tables here as needed
}

DELTA_EXTRA_COLUMNS: list[dict] = [
    {"name": "rec_effective_from",    "type": "date",    "nullable": False, "description": "When record becomes effective"},
    {"name": "rec_effective_to",      "type": "date",    "nullable": False, "description": "When record expires"},
    {"name": "rec_current_indicator", "type": "integer", "nullable": False, "description": "1 if current"},
    {"name": "rec_is_deleted",        "type": "boolean", "nullable": False, "description": "Soft delete flag"},
    {"name": "rec_load_dt",           "type": "date",    "nullable": False, "description": "Load date"},
    {"name": "rec_hash",              "type": "string",  "nullable": False, "description": "Hash for change detection"},
]

TRANSACTION_EXTRA_COLUMNS: list[dict] = [
    {"name": "rec_load_dt", "type": "date", "nullable": False, "description": "Load date"},
]
