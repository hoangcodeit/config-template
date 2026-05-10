"""Shared pytest fixtures."""
import textwrap
from pathlib import Path

import pytest

from src.config_generator.models import TableConfig

# ---------------------------------------------------------------------------
# Minimal template YAML content (mirrors the real templates)
# ---------------------------------------------------------------------------

_CONFIG_TEMPLATE = textwrap.dedent("""\
    version: 1.0
    name: ''
    description: ''
    metadata:
      business_owner: ''
      technical_owner: ''
      contacts:
        business: []
        technical: []
    input:
      load_type: hive
      file_source:
        file_path: ''
        file_format: csv
        options:
          delimiter: ','
          header: true
          encoding: utf-8
          infer_schema: true
      hive_source:
        host:
        port: 9083
        database: ''
        tablename: ''
        username: hive_user
        password: ${METASTORE_PASSWORD}
        scheme: postgresql+psycopg2
    output:
      catalog: ''
      database: ''
      table: ''
      partition_by: []
    schema:
      raw: ''
      curated: ''
      mode: strict
      enforcement: block
    processing:
      ingestion_type: DELTA
      primary_keys: []
      dedup_columns: []
      order_by_columns: []
      operation_column: ''
      exclude_columns: []
      cdc:
        soft_delete: true
        delete_column: null
""")

_SCHEMA_TEMPLATE = textwrap.dedent("""\
    version: 1.0
    name: ''
    columns:
      - name: ''
        type: ''
        nullable: true
        description: ''
""")


@pytest.fixture()
def templates_dir(tmp_path: Path) -> Path:
    tdir = tmp_path / "templates"
    tdir.mkdir()
    (tdir / "config_template.yml").write_text(_CONFIG_TEMPLATE, encoding="utf-8")
    (tdir / "raw_template.yml").write_text(_SCHEMA_TEMPLATE, encoding="utf-8")
    (tdir / "curated_template.yml").write_text(_SCHEMA_TEMPLATE, encoding="utf-8")
    return tdir


@pytest.fixture()
def table_structure_csv(tmp_path: Path) -> Path:
    path = tmp_path / "table_structure.csv"
    path.write_text(
        "column_name,data_type,table_name,primary_key\n"
        "id,bigint,orders,Y\n"
        "status,string,orders,\n"
        "__op,string,orders,\n"
        "__scn,bigint,orders,\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture()
def table_rules_csv(tmp_path: Path) -> Path:
    path = tmp_path / "table_rules.csv"
    path.write_text(
        "table_name,primary_key,order_by_columns,operation_column,"
        "exclude_columns,database_src,ingestion_type,metadata_exclude\n"
        'orders,"[""id""]","[""created_at""]",__op,"[""__scn""]",mydb,DELTA,""\n',
        encoding="utf-8",
    )
    return path


@pytest.fixture()
def delta_config() -> TableConfig:
    return TableConfig(
        table_name="orders",
        ingestion_type="DELTA",
        operation_column="__op",
        order_by_columns=["created_at"],
        exclude_columns=["__scn"],
        primary_keys=["id"],
        database_src="mydb",
        metadata_exclude=[],
    )


@pytest.fixture()
def transaction_config() -> TableConfig:
    return TableConfig(
        table_name="payments",
        ingestion_type="TRANSACTION",
        operation_column="__op",
        order_by_columns=["payment_date"],
        exclude_columns=["__scn"],
        primary_keys=["payment_id"],
        database_src="mydb",
        metadata_exclude=[],
    )
