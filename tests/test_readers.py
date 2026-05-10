"""Tests for src.config_generator.readers"""
import pytest

from src.config_generator.models import TableConfig
from src.config_generator.readers import (
    _parse_list,
    get_table_config,
    read_table_rules,
    read_table_structure,
)


# ---------------------------------------------------------------------------
# _parse_list
# ---------------------------------------------------------------------------

class TestParseList:
    def test_json_array(self):
        assert _parse_list('["a","b"]') == ["a", "b"]

    def test_json_array_with_spaces(self):
        assert _parse_list('["__scn", "__optime"]') == ["__scn", "__optime"]

    def test_empty_string(self):
        assert _parse_list("") == []

    def test_single_value(self):
        assert _parse_list('["id"]') == ["id"]

    def test_fallback_bare_list(self):
        # Non-JSON but bracket-wrapped
        assert _parse_list("[col_a,col_b]") == ["col_a", "col_b"]


# ---------------------------------------------------------------------------
# read_table_structure
# ---------------------------------------------------------------------------

class TestReadTableStructure:
    def test_returns_columns_for_table(self, table_structure_csv):
        result = read_table_structure(table_structure_csv)
        assert "orders" in result
        assert len(result["orders"]) == 4

    def test_primary_key_flag(self, table_structure_csv):
        result = read_table_structure(table_structure_csv)
        pk_cols = [c for c in result["orders"] if c.primary_key]
        assert len(pk_cols) == 1
        assert pk_cols[0].column_name == "id"

    def test_non_pk_columns_are_false(self, table_structure_csv):
        result = read_table_structure(table_structure_csv)
        non_pk = [c for c in result["orders"] if not c.primary_key]
        assert all(c.primary_key is False for c in non_pk)

    def test_data_types_preserved(self, table_structure_csv):
        result = read_table_structure(table_structure_csv)
        col_map = {c.column_name: c.data_type for c in result["orders"]}
        assert col_map["id"] == "bigint"
        assert col_map["status"] == "string"


# ---------------------------------------------------------------------------
# read_table_rules
# ---------------------------------------------------------------------------

class TestReadTableRules:
    def test_returns_config_for_table(self, table_rules_csv):
        result = read_table_rules(table_rules_csv)
        assert "orders" in result

    def test_ingestion_type(self, table_rules_csv):
        result = read_table_rules(table_rules_csv)
        assert result["orders"].ingestion_type == "DELTA"

    def test_operation_column(self, table_rules_csv):
        result = read_table_rules(table_rules_csv)
        assert result["orders"].operation_column == "__op"

    def test_primary_keys_parsed(self, table_rules_csv):
        result = read_table_rules(table_rules_csv)
        assert result["orders"].primary_keys == ["id"]

    def test_order_by_columns_parsed(self, table_rules_csv):
        result = read_table_rules(table_rules_csv)
        assert result["orders"].order_by_columns == ["created_at"]

    def test_exclude_columns_parsed(self, table_rules_csv):
        result = read_table_rules(table_rules_csv)
        assert result["orders"].exclude_columns == ["__scn"]

    def test_database_src(self, table_rules_csv):
        result = read_table_rules(table_rules_csv)
        assert result["orders"].database_src == "mydb"

    def test_missing_file_returns_empty(self, tmp_path):
        result = read_table_rules(tmp_path / "nonexistent.csv")
        assert result == {}


# ---------------------------------------------------------------------------
# get_table_config
# ---------------------------------------------------------------------------

class TestGetTableConfig:
    def test_returns_from_rules_when_present(self, delta_config):
        rules = {"orders": delta_config}
        assert get_table_config("orders", rules) is delta_config

    def test_fallback_to_ingestion_configs(self):
        from src.config_generator.constants import INGESTION_CONFIGS
        if not INGESTION_CONFIGS:
            pytest.skip("INGESTION_CONFIGS is empty")
        table_name = next(iter(INGESTION_CONFIGS))
        result = get_table_config(table_name, {})
        assert result is not None
        assert result.ingestion_type == INGESTION_CONFIGS[table_name]["ingestion_type"]

    def test_returns_none_for_unknown_table(self):
        assert get_table_config("does_not_exist", {}) is None

    def test_rules_take_priority_over_ingestion_configs(self, delta_config):
        from src.config_generator.constants import INGESTION_CONFIGS
        if not INGESTION_CONFIGS:
            pytest.skip("INGESTION_CONFIGS is empty")
        table_name = next(iter(INGESTION_CONFIGS))
        # Inject a custom config under the same name
        override = TableConfig(
            table_name=table_name,
            ingestion_type="TRANSACTION",
            operation_column="__op",
        )
        result = get_table_config(table_name, {table_name: override})
        assert result is override
        assert result.ingestion_type == "TRANSACTION"
