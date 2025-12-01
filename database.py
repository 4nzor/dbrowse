from __future__ import annotations

import json
import os
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import psycopg2
from psycopg2.extensions import connection as PGConnection
import pymysql
from pymysql.connections import Connection as MySQLConnection

CONFIG_DIR = Path.home() / ".config" / "dbrowse"
CONNECTIONS_FILE = CONFIG_DIR / "connections.json"


class DatabaseAdapter(ABC):
    """Абстракция для работы с разными БД."""
    
    @abstractmethod
    def connect(self, cfg: ConnectionConfig) -> Any:
        """Подключиться к БД."""
        pass
    
    @abstractmethod
    def close(self, conn: Any) -> None:
        """Закрыть подключение."""
        pass
    
    @abstractmethod
    def execute(self, conn: Any, query: str, params: Optional[Sequence] = None) -> List[Tuple]:
        """Выполнить запрос и вернуть все строки."""
        pass
    
    @abstractmethod
    def execute_with_description(self, conn: Any, query: str, params: Optional[Sequence] = None) -> Tuple[List[Tuple], List[str]]:
        """Выполнить запрос и вернуть строки и описание колонок."""
        pass
    
    @abstractmethod
    def get_tables_query(self, schema: str = "public") -> str:
        """SQL запрос для получения списка таблиц с размерами."""
        pass
    
    @abstractmethod
    def get_table_details_columns_query(self) -> str:
        """SQL запрос для получения колонок таблицы."""
        pass
    
    @abstractmethod
    def get_table_details_indexes_query(self) -> str:
        """SQL запрос для получения индексов таблицы."""
        pass
    
    @abstractmethod
    def quote_identifier(self, name: str) -> str:
        """Заключить идентификатор в кавычки."""
        pass
    
    @abstractmethod
    def get_default_schema(self) -> str:
        """Получить схему по умолчанию."""
        pass


class PostgreSQLAdapter(DatabaseAdapter):
    def connect(self, cfg: ConnectionConfig) -> PGConnection:
        conn = psycopg2.connect(cfg.dsn())
        conn.autocommit = True
        return conn
    
    def close(self, conn: PGConnection) -> None:
        conn.close()
    
    def execute(self, conn: PGConnection, query: str, params: Optional[Sequence] = None) -> List[Tuple]:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            return list(cur.fetchall())
    
    def execute_with_description(self, conn: PGConnection, query: str, params: Optional[Sequence] = None) -> Tuple[List[Tuple], List[str]]:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            rows = list(cur.fetchall())
            columns = [desc[0] for desc in cur.description] if cur.description else []
            return rows, columns
    
    def get_tables_query(self, schema: str = "public") -> str:
        return """
            SELECT n.nspname AS table_schema,
                   c.relname AS table_name,
                   pg_total_relation_size(c.oid) AS total_size
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r'
              AND n.nspname = %s
            ORDER BY total_size DESC, table_name
        """
    
    def get_table_details_columns_query(self) -> str:
        return """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """
    
    def get_table_details_indexes_query(self) -> str:
        return """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = %s AND tablename = %s
            ORDER BY indexname
        """
    
    def quote_identifier(self, name: str) -> str:
        return f'"{name}"'
    
    def get_default_schema(self) -> str:
        return "public"


class MySQLAdapter(DatabaseAdapter):
    def connect(self, cfg: ConnectionConfig) -> MySQLConnection:
        conn = pymysql.connect(
            host=cfg.host,
            port=cfg.port,
            user=cfg.user,
            password=cfg.password,
            database=cfg.dbname,
            autocommit=True,
        )
        return conn
    
    def close(self, conn: MySQLConnection) -> None:
        conn.close()
    
    def execute(self, conn: MySQLConnection, query: str, params: Optional[Sequence] = None) -> List[Tuple]:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            return list(cur.fetchall())
    
    def execute_with_description(self, conn: MySQLConnection, query: str, params: Optional[Sequence] = None) -> Tuple[List[Tuple], List[str]]:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            rows = list(cur.fetchall())
            columns = [desc[0] for desc in cur.description] if cur.description else []
            return rows, columns
    
    def get_tables_query(self, schema: str = "") -> str:
        # MySQL всегда использует текущую базу данных
        return """
            SELECT table_schema, table_name,
                   COALESCE(data_length + index_length, 0) AS total_size
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_type = 'BASE TABLE'
            ORDER BY total_size DESC, table_name
        """
    
    def get_table_details_columns_query(self) -> str:
        return """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """
    
    def get_table_details_indexes_query(self) -> str:
        # Упрощенный запрос для индексов MySQL
        return """
            SELECT DISTINCT index_name, index_type AS indexdef
            FROM information_schema.statistics
            WHERE table_schema = %s AND table_name = %s
            ORDER BY index_name
        """
    
    def quote_identifier(self, name: str) -> str:
        return f"`{name}`"
    
    def get_default_schema(self) -> str:
        return ""


class SQLiteAdapter(DatabaseAdapter):
    def connect(self, cfg: ConnectionConfig) -> sqlite3.Connection:
        conn = sqlite3.connect(cfg.dbname)
        conn.row_factory = sqlite3.Row
        return conn
    
    def close(self, conn: sqlite3.Connection) -> None:
        conn.close()
    
    def execute(self, conn: sqlite3.Connection, query: str, params: Optional[Sequence] = None) -> List[Tuple]:
        cur = conn.cursor()
        cur.execute(query, params or ())
        rows = cur.fetchall()
        cur.close()
        return [tuple(row) for row in rows]
    
    def execute_with_description(self, conn: sqlite3.Connection, query: str, params: Optional[Sequence] = None) -> Tuple[List[Tuple], List[str]]:
        cur = conn.cursor()
        cur.execute(query, params or ())
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] if cur.description else []
        result = [tuple(row) for row in rows]
        cur.close()
        return result, columns
    
    def get_tables_query(self, schema: str = "") -> str:
        # SQLite не поддерживает размер таблиц напрямую, возвращаем 0
        return """
            SELECT 'main' AS table_schema, name AS table_name, 0 AS total_size
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """
    
    def get_table_details_columns_query(self) -> str:
        return """
            SELECT name AS column_name, type AS data_type
            FROM pragma_table_info(?)
            ORDER BY cid
        """
    
    def get_table_details_indexes_query(self) -> str:
        return """
            SELECT name AS indexname, sql AS indexdef
            FROM sqlite_master
            WHERE type = 'index' AND tbl_name = ?
            ORDER BY name
        """
    
    def quote_identifier(self, name: str) -> str:
        return f'"{name}"'
    
    def get_default_schema(self) -> str:
        return "main"


class MongoDBAdapter(DatabaseAdapter):
    """Адаптер для MongoDB (NoSQL)."""
    
    def connect(self, cfg: ConnectionConfig):
        try:
            from pymongo import MongoClient
        except ImportError:
            raise ImportError("pymongo не установлен. Установите: pip install pymongo")
        
        if cfg.user and cfg.password:
            uri = f"mongodb://{cfg.user}:{cfg.password}@{cfg.host}:{cfg.port}/{cfg.dbname}"
        else:
            uri = f"mongodb://{cfg.host}:{cfg.port}/{cfg.dbname}"
        
        client = MongoClient(uri)
        return client
    
    def close(self, conn) -> None:
        conn.close()
    
    def execute(self, conn, query: str, params: Optional[Sequence] = None) -> List[Tuple]:
        # Для MongoDB query - это JSON строка с фильтром
        # В данном контексте не используется напрямую
        return []
    
    def execute_with_description(self, conn, query: str, params: Optional[Sequence] = None) -> Tuple[List[Tuple], List[str]]:
        # Для MongoDB query - это JSON строка с фильтром
        # В данном контексте не используется напрямую
        return [], []
    
    def get_tables_query(self, schema: str = "") -> str:
        # MongoDB не использует SQL, возвращаем пустую строку
        # Список коллекций получаем через специальный метод
        return ""
    
    def get_table_details_columns_query(self) -> str:
        # MongoDB не использует SQL
        return ""
    
    def get_table_details_indexes_query(self) -> str:
        # MongoDB не использует SQL
        return ""
    
    def quote_identifier(self, name: str) -> str:
        return name
    
    def get_default_schema(self) -> str:
        return ""
    
    def get_collections(self, conn, dbname: str) -> List[Tuple[str, str, int]]:
        """Получить список коллекций MongoDB."""
        try:
            db = conn[dbname]
            collections = []
            for coll_name in db.list_collection_names():
                stats = db.command("collStats", coll_name)
                size = stats.get("size", 0) + stats.get("totalIndexSize", 0)
                collections.append(("", coll_name, int(size)))
            return sorted(collections, key=lambda x: x[2], reverse=True)
        except Exception as e:
            return []
    
    def get_collection_sample(self, conn, dbname: str, collection: str, limit: int = 10, offset: int = 0, filter_query: Optional[str] = None) -> Tuple[List[Tuple], List[str]]:
        """Получить образцы документов из коллекции."""
        try:
            db = conn[dbname]
            coll = db[collection]
            
            # Парсим фильтр если есть
            import json
            filter_dict = {}
            if filter_query and filter_query.strip():
                try:
                    filter_dict = json.loads(filter_query)
                except:
                    # Если не JSON, пытаемся как простой фильтр
                    pass
            
            # Получаем документы
            cursor = coll.find(filter_dict).skip(offset).limit(limit)
            docs = list(cursor)
            
            if not docs:
                return [], []
            
            # Извлекаем все возможные ключи из документов
            all_keys = set()
            for doc in docs:
                all_keys.update(doc.keys())
            
            # Убираем _id из списка колонок для отображения (он всегда есть)
            columns = [k for k in sorted(all_keys) if k != "_id"]
            if "_id" in all_keys:
                columns.insert(0, "_id")
            
            # Преобразуем документы в строки
            rows = []
            for doc in docs:
                row = []
                for col in columns:
                    val = doc.get(col)
                    if val is None:
                        row.append("")
                    elif isinstance(val, (dict, list)):
                        row.append(json.dumps(val, ensure_ascii=False))
                    else:
                        row.append(str(val))
                rows.append(tuple(row))
            
            return rows, columns
        except Exception as e:
            return [], []


class ClickHouseAdapter(DatabaseAdapter):
    """Адаптер для ClickHouse."""
    
    def connect(self, cfg: ConnectionConfig):
        try:
            from clickhouse_driver import Client
        except ImportError:
            raise ImportError("clickhouse-driver не установлен. Установите: pip install clickhouse-driver")
        
        client = Client(
            host=cfg.host,
            port=cfg.port,
            user=cfg.user or "default",
            password=cfg.password or "",
            database=cfg.dbname or "default",
        )
        return client
    
    def close(self, conn) -> None:
        conn.disconnect()
    
    def execute(self, conn, query: str, params: Optional[Sequence] = None) -> List[Tuple]:
        result = conn.execute(query, params or ())
        return [tuple(row) for row in result]
    
    def execute_with_description(self, conn, query: str, params: Optional[Sequence] = None) -> Tuple[List[Tuple], List[str]]:
        result = conn.execute(query, params or ())
        rows = [tuple(row) for row in result]
        
        # Получаем колонки из результата
        columns = []
        if hasattr(result, 'column_names'):
            columns = result.column_names
        elif hasattr(conn, 'last_query'):
            # Пытаемся получить через метаданные
            try:
                # Для ClickHouse можно использовать DESCRIBE или получить из результата
                if rows:
                    # Если есть данные, используем количество колонок
                    columns = [f"col_{i+1}" for i in range(len(rows[0]))]
            except:
                pass
        
        # Если не получили колонки, используем индексы
        if not columns and rows:
            columns = [f"col_{i+1}" for i in range(len(rows[0]))]
        elif not columns:
            columns = []
        
        return rows, columns
    
    def get_tables_query(self, schema: str = "") -> str:
        # ClickHouse использует базы данных вместо схем
        # Используем параметр для database
        return """
            SELECT 
                database AS table_schema,
                name AS table_name,
                total_bytes AS total_size
            FROM system.tables
            WHERE database = %s
            ORDER BY total_size DESC, table_name
        """
    
    def get_table_details_columns_query(self) -> str:
        return """
            SELECT name AS column_name, type AS data_type
            FROM system.columns
            WHERE database = %s AND table = %s
            ORDER BY position
        """
    
    def get_table_details_indexes_query(self) -> str:
        # ClickHouse не имеет традиционных индексов, но есть проекции и материализованные представления
        return """
            SELECT name AS indexname, type AS indexdef
            FROM system.data_skipping_indices
            WHERE database = %s AND table = %s
            ORDER BY name
        """
    
    def quote_identifier(self, name: str) -> str:
        return f"`{name}`"
    
    def get_default_schema(self) -> str:
        return ""


def get_adapter(db_type: str) -> DatabaseAdapter:
    """Получить адаптер для типа БД."""
    if db_type == "postgres":
        return PostgreSQLAdapter()
    elif db_type == "mysql":
        return MySQLAdapter()
    elif db_type == "sqlite":
        return SQLiteAdapter()
    elif db_type == "mongodb":
        return MongoDBAdapter()
    elif db_type == "clickhouse":
        return ClickHouseAdapter()
    else:
        raise ValueError(f"Неподдерживаемый тип БД: {db_type}")


@dataclass
class ConnectionConfig:
    name: str = "default"
    db_type: str = "postgres"  # postgres, mysql, sqlite, mongodb, clickhouse
    host: str = "localhost"
    port: int = 5432
    dbname: str = "postgres"
    user: str = "postgres"
    password: str = ""
    # Для SQLite: dbname используется как путь к файлу
    # Для MongoDB: dbname - имя базы данных

    def dsn(self) -> str:
        if self.db_type == "sqlite":
            return self.dbname
        elif self.db_type == "mongodb":
            if self.user and self.password:
                return f"mongodb://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"
            return f"mongodb://{self.host}:{self.port}/{self.dbname}"
        return f"host={self.host} port={self.port} dbname={self.dbname} user={self.user} password={self.password}"


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_saved_connections() -> Dict[str, ConnectionConfig]:
    ensure_config_dir()
    if not CONNECTIONS_FILE.exists():
        return {}
    try:
        data = json.loads(CONNECTIONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    result: Dict[str, ConnectionConfig] = {}
    for name, cfg in data.items():
        try:
            result[name] = ConnectionConfig(
                name=name,
                db_type=cfg.get("db_type", "postgres"),
                host=cfg.get("host", "localhost"),
                port=int(cfg.get("port", 5432)),
                dbname=cfg.get("dbname", "postgres"),
                user=cfg.get("user", "postgres"),
                password=cfg.get("password", ""),
            )
        except Exception:
            continue
    return result


def save_connection_config(cfg: ConnectionConfig) -> None:
    ensure_config_dir()
    all_cfgs = load_saved_connections()
    all_cfgs[cfg.name] = cfg
    serializable = {
        name: {
            "db_type": c.db_type,
            "host": c.host,
            "port": c.port,
            "dbname": c.dbname,
            "user": c.user,
            "password": c.password,
        }
        for name, c in all_cfgs.items()
    }
    CONNECTIONS_FILE.write_text(json.dumps(serializable, indent=2), encoding="utf-8")


def configure_connection_from_env() -> Optional[ConnectionConfig]:
    dsn_url = os.getenv("DATABASE_URL")
    if not dsn_url:
        return None

    # Парсер URL для разных БД
    try:
        import urllib.parse as up

        parsed = up.urlparse(dsn_url)
        scheme = parsed.scheme.lower()
        
        if scheme in ("postgresql", "postgres"):
            db_type = "postgres"
            default_port = 5432
        elif scheme in ("mysql", "mariadb"):
            db_type = "mysql"
            default_port = 3306
        elif scheme == "sqlite":
            db_type = "sqlite"
            default_port = 0
        elif scheme == "mongodb":
            db_type = "mongodb"
            default_port = 27017
        elif scheme == "clickhouse":
            db_type = "clickhouse"
            default_port = 9000
        else:
            return None

        if db_type == "sqlite":
            user = ""
            password = ""
            host = ""
            port = 0
            dbname = parsed.path.lstrip("/") or ""
        else:
            user = parsed.username or ("postgres" if db_type == "postgres" else ("default" if db_type == "clickhouse" else ""))
            password = parsed.password or ""
            host = parsed.hostname or "localhost"
            port = parsed.port or default_port
            dbname = parsed.path.lstrip("/") or ("postgres" if db_type == "postgres" else ("default" if db_type == "clickhouse" else ""))

        return ConnectionConfig(
            db_type=db_type,
            host=host,
            port=int(port) if port else 0,
            dbname=dbname,
            user=user,
            password=password,
        )
    except Exception:
        return None


def ask_connection_config() -> ConnectionConfig:
    from utils import print_header, input_with_default, IntValidator
    from prompt_toolkit.completion import WordCompleter

    print_header("Настройка подключения к БД")

    cfg_env = configure_connection_from_env()
    if cfg_env:
        print("Обнаружена переменная окружения DATABASE_URL, значения будут использованы по умолчанию.")

    base = cfg_env or ConnectionConfig()

    name = input_with_default("Название подключения", base.name)
    
    db_type_completer = WordCompleter(["postgres", "mysql", "sqlite", "mongodb", "clickhouse"], ignore_case=True)
    db_type = input_with_default("Тип БД (postgres/mysql/sqlite/mongodb/clickhouse)", base.db_type, completer=db_type_completer).lower()
    if db_type not in ("postgres", "mysql", "sqlite", "mongodb", "clickhouse"):
        db_type = "postgres"
    
    if db_type == "sqlite":
        dbname = input_with_default("Путь к файлу БД", base.dbname)
        return ConnectionConfig(
            name=name,
            db_type=db_type,
            host="",
            port=0,
            dbname=dbname,
            user="",
            password="",
        )
    else:
        host = input_with_default("Host", base.host)
        port_str = input_with_default("Port", str(base.port), validator=IntValidator())
        dbname = input_with_default("Database name", base.dbname)
        user = input_with_default("User", base.user)
        password = input_with_default("Password", base.password or "", is_password=True)

        return ConnectionConfig(
            name=name,
            db_type=db_type,
            host=host,
            port=int(port_str),
            dbname=dbname,
            user=user,
            password=password,
        )


def connect(cfg: ConnectionConfig) -> Any:
    from utils import push_status
    
    adapter = get_adapter(cfg.db_type)
    if cfg.db_type == "sqlite":
        push_status(f"Подключение к {cfg.name} ({cfg.dbname})...")
    elif cfg.db_type == "mongodb":
        push_status(f"Подключение к {cfg.name} (mongodb://{cfg.host}:{cfg.port}/{cfg.dbname})...")
    else:
        push_status(f"Подключение к {cfg.name} ({cfg.user}@{cfg.host})...")
    conn = adapter.connect(cfg)
    push_status(f"Успешное подключение к {cfg.name}.")
    return conn

