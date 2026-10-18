from importlib import import_module

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from src.database import metadata


@pytest.mark.parametrize("supabase",[False,True])
def test_frozen_revision_matches_models_and_compiles_postgres(monkeypatch,supabase):
    revision = import_module("migrations.versions.0001_central")
    frozen = sa.MetaData()
    statements = []

    class Connection:
        dialect = postgresql.dialect()

        def scalar(self, statement):
            return supabase if "auth.uid()" in str(statement) else "gis"

    def create_table(name,*columns,**kwargs):
        sa.Table(name,frozen,*columns,**kwargs)

    monkeypatch.setattr(revision.op,"get_bind",lambda:Connection())
    monkeypatch.setattr(revision.op,"create_table",create_table)
    monkeypatch.setattr(revision.op,"create_index",lambda *args,**kwargs:None)
    monkeypatch.setattr(revision.op,"execute",lambda statement:statements.append(str(statement)))
    revision.upgrade()
    assert set(frozen.tables) == set(metadata.tables)
    for name,table in frozen.tables.items():
        assert list(table.columns.keys()) == list(metadata.tables[name].columns.keys())
        ddl = str(CreateTable(table).compile(dialect=postgresql.dialect()))
        assert "CREATE TABLE vial." in ddl
        if name == "vial.jobs":
            assert "JSONB" in ddl and "FOREIGN KEY(trip_id, owner_id)" in ddl
    assert any("GENERATED ALWAYS AS" in statement and "Point,4326" in statement for statement in statements)
    assert any("USING GIST" in statement for statement in statements)
    assert sum("ENABLE ROW LEVEL SECURITY" in statement for statement in statements) == 4
    assert sum("CREATE POLICY" in statement for statement in statements) == (4 if supabase else 0)
