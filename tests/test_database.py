import os
import sqlite3
import pytest
from database import SQLiteAdapter, ConnectionConfig

@pytest.fixture
def test_db():
    db_path = "test_tmp.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO users (name) VALUES ('Alice'), ('Bob'), ('Charlie')")
    conn.commit()
    conn.close()
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)

def test_sqlite_adapter_tables(test_db):
    adapter = SQLiteAdapter()
    cfg = ConnectionConfig(dbname=test_db, db_type="sqlite")
    conn = adapter.connect(cfg)

    query = adapter.get_tables_query()
    tables = adapter.execute(conn, query)

    assert any(t[1] == "users" for t in tables)
    adapter.close(conn)

def test_sqlite_adapter_stats(test_db):
    adapter = SQLiteAdapter()
    cfg = ConnectionConfig(dbname=test_db, db_type="sqlite")
    conn = adapter.connect(cfg)

    query = adapter.get_column_stats_query("", "users", "name", 10)
    stats = adapter.execute(conn, query)

    assert len(stats) == 3
    # Alice, Bob, Charlie each have 1 count (33.33%)
    assert stats[0][1] == 1
    adapter.close(conn)

def test_connection_config_dsn():
    cfg = ConnectionConfig(name="test", db_type="sqlite", dbname="test.db")
    assert cfg.dsn() == "test.db"

    cfg_pg = ConnectionConfig(name="pg", db_type="postgres", host="localhost", port=5432, dbname="mydb", user="user", password="pwd")
    assert "host=localhost" in cfg_pg.dsn()
    assert "dbname=mydb" in cfg_pg.dsn()
