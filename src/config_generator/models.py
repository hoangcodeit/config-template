from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ColumnDef:
    column_name: str
    data_type: str
    primary_key: bool = False


@dataclass
class TableConfig:
    table_name: str
    ingestion_type: Literal["DELTA", "TRANSACTION"]
    operation_column: str
    order_by_columns: list[str] = field(default_factory=list)
    exclude_columns: list[str]  = field(default_factory=list)
    primary_keys: list[str]     = field(default_factory=list)
    database_src: str           = ""
    metadata_exclude: list[str] = field(default_factory=list)


@dataclass
class GenerationResult:
    table_name: str
    config: str = "SKIP"   # "OK" | "FAIL" | "SKIP"
    raw: str    = "SKIP"
    curated: str = "SKIP"
    status: str  = "SKIP"  # "OK" | "PARTIAL" | "NOT_IN_CSV" | "NO_CONFIG"
