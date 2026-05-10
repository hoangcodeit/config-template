"""Tests for src.config_generator.generators"""
from pathlib import Path

from ruamel.yaml import YAML

from src.config_generator.constants import DELTA_EXTRA_COLUMNS, METADATA_EXCLUDE
from src.config_generator.generators import generate_config, generate_curated, generate_raw
from src.config_generator.models import ColumnDef, TableConfig


def _load(path: Path) -> dict:
    return YAML().load(path)


def _col_names(data: dict) -> list[str]:
    return [c["name"] for c in data["columns"]]


# ---------------------------------------------------------------------------
# generate_config
# ---------------------------------------------------------------------------

_SAMPLE_COLUMNS = [
    ColumnDef("id", "bigint"),
    ColumnDef("status", "string"),
    ColumnDef("__scn", "bigint"),
    ColumnDef("__op", "string"),
]


def _gen_config(tmp_path, templates_dir, config, columns=None, exclude_set=None, primary_keys=None):
    cols = columns if columns is not None else _SAMPLE_COLUMNS
    exc  = exclude_set if exclude_set is not None else set()
    pks  = primary_keys if primary_keys is not None else ["id"]
    return generate_config(config.table_name, config, pks, cols, exc, tmp_path, templates_dir)


class TestGenerateConfig:
    def test_creates_file(self, tmp_path, templates_dir, delta_config):
        _gen_config(tmp_path, templates_dir, delta_config)
        assert (tmp_path / "orders_config.yml").exists()

    def test_name_field(self, tmp_path, templates_dir, delta_config):
        _gen_config(tmp_path, templates_dir, delta_config)
        assert _load(tmp_path / "orders_config.yml")["name"] == "orders"

    def test_hive_tablename(self, tmp_path, templates_dir, delta_config):
        _gen_config(tmp_path, templates_dir, delta_config)
        assert _load(tmp_path / "orders_config.yml")["input"]["hive_source"]["tablename"] == "orders"

    def test_output_database(self, tmp_path, templates_dir, delta_config):
        _gen_config(tmp_path, templates_dir, delta_config)
        assert _load(tmp_path / "orders_config.yml")["output"]["database"] == "mydb"

    def test_schema_references(self, tmp_path, templates_dir, delta_config):
        _gen_config(tmp_path, templates_dir, delta_config)
        data = _load(tmp_path / "orders_config.yml")
        assert data["schema"]["raw"] == "raw_orders.yml"
        assert data["schema"]["curated"] == "curated_orders.yml"

    def test_processing_fields(self, tmp_path, templates_dir, delta_config):
        _gen_config(tmp_path, templates_dir, delta_config)
        proc = _load(tmp_path / "orders_config.yml")["processing"]
        assert proc["ingestion_type"] == "DELTA"
        assert proc["primary_keys"] == ["id"]
        assert proc["order_by_columns"] == ["created_at"]
        assert proc["operation_column"] == "__op"
        assert proc["exclude_columns"] == ["__scn"]

    def test_dedup_columns_excludes_metadata_and_exclude_cols(self, tmp_path, templates_dir, delta_config):
        # delta_config.exclude_columns = ["__scn"], exclude_set = {"__op"}
        columns = [
            ColumnDef("id", "bigint"),
            ColumnDef("status", "string"),
            ColumnDef("__scn", "bigint"),   # in exclude_columns
            ColumnDef("__op", "string"),    # in exclude_set
        ]
        _gen_config(tmp_path, templates_dir, delta_config, columns=columns, exclude_set={"__op"})
        proc = _load(tmp_path / "orders_config.yml")["processing"]
        assert proc["dedup_columns"] == ["id", "status"]

    def test_dedup_columns_empty_when_all_excluded(self, tmp_path, templates_dir, delta_config):
        columns = [ColumnDef("__scn", "bigint")]   # only column is in exclude_columns
        _gen_config(tmp_path, templates_dir, delta_config, columns=columns)
        proc = _load(tmp_path / "orders_config.yml")["processing"]
        assert proc["dedup_columns"] == []

    def test_returns_true_on_success(self, tmp_path, templates_dir, delta_config):
        assert _gen_config(tmp_path, templates_dir, delta_config) is True


# ---------------------------------------------------------------------------
# generate_raw
# ---------------------------------------------------------------------------

class TestGenerateRaw:
    def test_creates_file(self, tmp_path, templates_dir):
        columns = [ColumnDef("id", "bigint")]
        generate_raw("orders", columns, set(), tmp_path, templates_dir)
        assert (tmp_path / "raw_orders.yml").exists()

    def test_name_field(self, tmp_path, templates_dir):
        generate_raw("orders", [ColumnDef("id", "bigint")], set(), tmp_path, templates_dir)
        assert _load(tmp_path / "raw_orders.yml")["name"] == "raw_orders"

    def test_excludes_metadata_columns(self, tmp_path, templates_dir):
        columns = [
            ColumnDef("id", "bigint"),
            ColumnDef("__op", "string"),
            ColumnDef("__scn", "bigint"),
            ColumnDef("status", "string"),
        ]
        generate_raw("orders", columns, set(METADATA_EXCLUDE), tmp_path, templates_dir)
        names = _col_names(_load(tmp_path / "raw_orders.yml"))
        assert "id" in names
        assert "status" in names
        assert "__op" not in names
        assert "__scn" not in names

    def test_all_columns_included_when_no_exclude(self, tmp_path, templates_dir):
        columns = [ColumnDef("a", "string"), ColumnDef("b", "integer")]
        generate_raw("t", columns, set(), tmp_path, templates_dir)
        names = _col_names(_load(tmp_path / "raw_t.yml"))
        assert names == ["a", "b"]

    def test_returns_true_on_success(self, tmp_path, templates_dir):
        assert generate_raw("t", [ColumnDef("id", "bigint")], set(), tmp_path, templates_dir) is True


# ---------------------------------------------------------------------------
# generate_curated
# ---------------------------------------------------------------------------

class TestGenerateCurated:
    def test_creates_file(self, tmp_path, templates_dir, delta_config):
        generate_curated("orders", [ColumnDef("id", "bigint")], delta_config, set(), tmp_path, templates_dir)
        assert (tmp_path / "curated_orders.yml").exists()

    def test_name_field(self, tmp_path, templates_dir, delta_config):
        generate_curated("orders", [ColumnDef("id", "bigint")], delta_config, set(), tmp_path, templates_dir)
        assert _load(tmp_path / "curated_orders.yml")["name"] == "curated_orders"

    def test_delta_appends_6_audit_columns(self, tmp_path, templates_dir, delta_config):
        generate_curated("orders", [ColumnDef("id", "bigint")], delta_config, set(), tmp_path, templates_dir)
        names = _col_names(_load(tmp_path / "curated_orders.yml"))
        for extra in DELTA_EXTRA_COLUMNS:
            assert extra["name"] in names

    def test_transaction_appends_only_rec_load_dt(self, tmp_path, templates_dir, transaction_config):
        generate_curated("payments", [ColumnDef("id", "bigint")], transaction_config, set(), tmp_path, templates_dir)
        names = _col_names(_load(tmp_path / "curated_payments.yml"))
        assert "rec_load_dt" in names
        assert "rec_hash" not in names
        assert "rec_effective_from" not in names

    def test_excludes_metadata_and_exclude_columns(self, tmp_path, templates_dir, delta_config):
        columns = [
            ColumnDef("id", "bigint"),
            ColumnDef("status", "string"),
            ColumnDef("__scn", "bigint"),   # in exclude_columns
            ColumnDef("__koptime", "string"),  # in metadata_exclude
        ]
        exclude_set = {"__koptime"}
        generate_curated("orders", columns, delta_config, exclude_set, tmp_path, templates_dir)
        names = _col_names(_load(tmp_path / "curated_orders.yml"))
        assert "id" in names
        assert "status" in names
        assert "__scn" not in names
        assert "__koptime" not in names

    def test_operation_column_kept_despite_being_in_exclude_set(self, tmp_path, templates_dir, delta_config):
        # __op is both in METADATA_EXCLUDE and is the operation_column — must be kept
        columns = [ColumnDef("id", "bigint"), ColumnDef("__op", "string")]
        exclude_set = set(METADATA_EXCLUDE)  # contains "__op"
        generate_curated("orders", columns, delta_config, exclude_set, tmp_path, templates_dir)
        names = _col_names(_load(tmp_path / "curated_orders.yml"))
        assert "__op" in names

    def test_operation_column_kept_despite_being_in_exclude_columns(self, tmp_path, templates_dir):
        config = TableConfig(
            table_name="t",
            ingestion_type="DELTA",
            operation_column="__op",
            exclude_columns=["__op"],  # explicitly listed — should still be kept
        )
        columns = [ColumnDef("id", "bigint"), ColumnDef("__op", "string")]
        generate_curated("t", columns, config, set(), tmp_path, templates_dir)
        names = _col_names(_load(tmp_path / "curated_t.yml"))
        assert "__op" in names

    def test_transaction_adds_op_column_when_not_in_source(self, tmp_path, templates_dir, transaction_config):
        columns = [ColumnDef("id", "bigint"), ColumnDef("amount", "decimal")]
        generate_curated("payments", columns, transaction_config, set(), tmp_path, templates_dir)
        names = _col_names(_load(tmp_path / "curated_payments.yml"))
        assert "__op" in names

    def test_delta_adds_op_column_when_not_in_source(self, tmp_path, templates_dir, delta_config):
        columns = [ColumnDef("id", "bigint"), ColumnDef("status", "string")]
        generate_curated("orders", columns, delta_config, set(), tmp_path, templates_dir)
        names = _col_names(_load(tmp_path / "curated_orders.yml"))
        assert "__op" in names

    def test_does_not_duplicate_op_column_when_already_present(self, tmp_path, templates_dir, delta_config):
        columns = [ColumnDef("id", "bigint"), ColumnDef("__op", "string")]
        generate_curated("orders", columns, delta_config, set(), tmp_path, templates_dir)
        names = _col_names(_load(tmp_path / "curated_orders.yml"))
        assert names.count("__op") == 1

    def test_returns_true_on_success(self, tmp_path, templates_dir, delta_config):
        result = generate_curated("orders", [ColumnDef("id", "bigint")], delta_config, set(), tmp_path, templates_dir)
        assert result is True
