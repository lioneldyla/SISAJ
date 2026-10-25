from pathlib import Path
import pytest
from scripts.backup_schema import inventory,check_tables

def test_every_declared_table_is_in_backup_schema():
    scripts,tables=inventory(Path(__file__).resolve().parents[1])
    assert {'import_sources','user_data_profiles','transfer_archives','registry_source_rows','sessions'}<=tables
    assert len(tables)==25
    assert len(scripts)==6
    check_tables(tables,tables)

def test_unknown_and_empty_sources_fail_closed():
    with pytest.raises(ValueError):check_tables({'unexpected'},{'users'})
    with pytest.raises(ValueError):check_tables(set(),{'users'})

def test_previous_schema_is_supported_without_fabricating_rows():
    _,tables=inventory(Path(__file__).resolve().parents[1])
    check_tables(tables-{'import_sources'},tables)
