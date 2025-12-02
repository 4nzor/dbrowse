import re
import time
from typing import Dict, List, Optional, Tuple, Union

import sqlite3
import termtables as tt
from prompt_toolkit import Application
from prompt_toolkit.application import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.mouse_events import MouseButton, MouseEventType
from prompt_toolkit.styles import Style
from pygments.lexers.sql import SqlLexer
from psycopg2.extensions import connection as PGConnection
from pymysql.connections import Connection as MySQLConnection

from database import (
    ConnectionConfig,
    DatabaseAdapter,
    connect,
    get_adapter,
    load_saved_connections,
)
from utils import format_size, push_status, status_messages

# Import update checker lazily to avoid blocking startup
try:
    from update_checker import check_for_updates, CURRENT_VERSION
except ImportError:
    # Fallback if update_checker is not available
    CURRENT_VERSION = "0.1.0"
    def check_for_updates():
        return False, None

style = Style.from_dict(
    {
        "title": "bold underline",
        "menu": "bold",
        "error": "fg:red bold",
        "success": "fg:green bold",
        "hint": "fg:#888888",
        "large-table": "fg:red",
        "medium-table": "fg:yellow",
    }
)


class ClickableTextControl(FormattedTextControl):
    """
    Extension of FormattedTextControl that allows attaching a mouse handler.
    """

    def __init__(self, *args, on_click=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._on_click = on_click

    def mouse_handler(self, mouse_event):
        if self._on_click:
            return self._on_click(mouse_event)
        return super().mouse_handler(mouse_event)


def browse_connections_ui_once() -> str:
    """
    Full-screen mode:
    - left column: saved connections (databases) + ADD button at bottom
    - middle: tables of selected database
    - right: first 10 rows of selected table
    Controls:
    - Mouse: click on database or table; click ADD opens add form
    - Tab: switch active column
    - ↑/↓: navigate items in active column
    - Enter: load tables (in left column) or data (in middle)
    - q: exit (return to main)
    Returns:
    - "quit"  — just exit
    - "add"   — open form to add new connection
    """

    saved = load_saved_connections()
    conn_names = list(saved.keys())
    connections: List[ConnectionConfig] = [saved[name] for name in conn_names]

    tables: List[Tuple[str, str, int]] = []  # (schema, table, size bytes)
    table_details: Dict[Tuple[str, str], Dict[str, List[str]]] = {}
    table_line_map: List[Optional[int]] = []
    rows: List[Tuple] = []
    columns: List[str] = []

    selected_conn_idx = 0 if connections else -1
    selected_table_idx = 0 if tables else -1
    active_column = 1  # по умолчанию работаем со списком таблиц

    # Пагинация списков
    TABLE_WINDOW_DEFAULT = 20
    table_offset = 0  # смещение списка таблиц
    last_table_click: Optional[Tuple[str, str]] = None
    last_click_time = 0.0

    rows_scroll_offset = 0  # SQL OFFSET для пагинации
    rows_per_page = 10  # количество строк на странице (SQL LIMIT)
    total_rows_count = 0  # общее количество строк (для отображения)
    current_where_clause = ""  # текущий WHERE фильтр
    table_where_clauses: Dict[Tuple[str, str], str] = {}  # WHERE для каждой таблицы
    current_order_by_clause = ""  # текущий ORDER BY
    table_order_by_clauses: Dict[Tuple[str, str], str] = {}  # ORDER BY для каждой таблицы

    # Buffer для ввода WHERE и ORDER BY
    where_buffer = Buffer()
    order_by_buffer = Buffer()
    
    # Поиск по таблицам
    table_search_filter = ""
    table_search_buffer = Buffer()
    all_tables: List[Tuple[str, str, int]] = []  # Все таблицы без фильтра

    # SQL Editor state
    sql_editor_mode = False  # True when SQL editor is open
    sql_editor_buffer = Buffer()
    sql_query_history: List[str] = []  # History of executed queries
    sql_history_index = -1  # Current position in history (-1 = new query)
    sql_query_results: Optional[Tuple[List[Tuple], List[str]]] = None  # (rows, columns)
    sql_query_error: Optional[str] = None
    sql_execution_time: Optional[float] = None

    active_conn: Optional[Union[PGConnection, MySQLConnection, sqlite3.Connection]] = None
    active_conn_idx: int = -1
    active_adapter: Optional[DatabaseAdapter] = None

    def set_active_connection(idx: int) -> bool:
        nonlocal active_conn, active_conn_idx, active_adapter
        if idx < 0 or idx >= len(connections):
            return False
        if active_conn is not None and active_conn_idx == idx:
            return True
        if active_conn is not None and active_adapter is not None:
            try:
                active_adapter.close(active_conn)
            except Exception:
                pass
            active_conn = None
            active_conn_idx = -1
            active_adapter = None
        cfg = connections[idx]
        try:
            active_adapter = get_adapter(cfg.db_type)
            active_conn = connect(cfg)
            active_conn_idx = idx
            return True
        except Exception as e:
            push_status(f"Connection error: {e}")
            active_conn = None
            active_conn_idx = -1
            active_adapter = None
            return False

    def get_table_window_size() -> int:
        try:
            rows = get_app().output.get_size().rows
            return max(5, rows - 6)
        except Exception:
            return TABLE_WINDOW_DEFAULT

    def load_tables_for_connection() -> None:
        nonlocal tables, selected_table_idx, rows, columns, table_offset
        if selected_conn_idx < 0 or selected_conn_idx >= len(connections):
            tables = []
            selected_table_idx = -1
            rows = []
            columns = []
            return
        if not set_active_connection(selected_conn_idx):
            tables = []
            selected_table_idx = -1
            rows = []
            columns = []
            return
        if active_adapter is None or active_conn is None:
            tables = []
            selected_table_idx = -1
            rows = []
            columns = []
            return
        
        cfg = connections[selected_conn_idx]
        
        if cfg.db_type == "mongodb":
            # MongoDB использует коллекции вместо таблиц
            from database import MongoDBAdapter
            if isinstance(active_adapter, MongoDBAdapter):
                res = active_adapter.get_collections(active_conn, cfg.dbname)
            else:
                res = []
        else:
            default_schema = active_adapter.get_default_schema()
            query = active_adapter.get_tables_query(default_schema)
            
            if cfg.db_type == "postgres":
                res = active_adapter.execute(active_conn, query, (default_schema,))
            elif cfg.db_type == "mysql":
                # MySQL использует DATABASE() в запросе, параметры не нужны
                res = active_adapter.execute(active_conn, query)
            elif cfg.db_type == "clickhouse":
                # ClickHouse использует имя базы данных как параметр
                res = active_adapter.execute(active_conn, query, (cfg.dbname,))
            else:  # sqlite
                res = active_adapter.execute(active_conn, query)
        
        all_tables = [(schema, name, int(size or 0)) for (schema, name, size) in res]
        # Применяем фильтр поиска
        if table_search_filter:
            tables = [t for t in all_tables if table_search_filter.lower() in (t[0] + "." + t[1] if t[0] else t[1]).lower()]
        else:
            tables = all_tables
        selected_table_idx = 0 if tables else -1
        rows = []
        columns = []
        table_offset = 0
        table_details.clear()

    def load_table_details(schema: str, table: str) -> None:
        """
        Загружаем список колонок и индексов для таблицы/коллекции.
        """
        if active_conn is None or active_adapter is None:
            return
        key = (schema, table)
        if key in table_details:
            return
        cols: List[str] = []
        idxs: List[str] = []
        
        cfg = connections[active_conn_idx]
        
        if cfg.db_type == "mongodb":
            # Для MongoDB получаем образец документа для определения структуры
            from database import MongoDBAdapter
            if isinstance(active_adapter, MongoDBAdapter):
                sample_rows, sample_cols = active_adapter.get_collection_sample(active_conn, cfg.dbname, table, limit=1)
                cols = [f"{col} (dynamic)" for col in sample_cols]
                # MongoDB индексы можно получить через list_indexes
                try:
                    db = active_conn[cfg.dbname]
                    coll = db[table]
                    indexes = coll.list_indexes()
                    idxs = [f"{idx['name']}: {str(idx.get('key', {}))}" for idx in indexes]
                except:
                    idxs = []
        else:
            cols_query = active_adapter.get_table_details_columns_query()
            idxs_query = active_adapter.get_table_details_indexes_query()
            
            if cfg.db_type == "sqlite":
                cols_res = active_adapter.execute(active_conn, cols_query, (table,))
                idxs_res = active_adapter.execute(active_conn, idxs_query, (table,))
            elif cfg.db_type == "clickhouse":
                # ClickHouse использует database и table
                cols_res = active_adapter.execute(active_conn, cols_query, (cfg.dbname, table))
                idxs_res = active_adapter.execute(active_conn, idxs_query, (cfg.dbname, table))
            else:
                cols_res = active_adapter.execute(active_conn, cols_query, (schema, table))
                idxs_res = active_adapter.execute(active_conn, idxs_query, (schema, table))
            
            cols = [f"{name} ({dtype})" for (name, dtype) in cols_res]
            idxs = [f"{name}: {defn}" for (name, defn) in idxs_res]

        table_details[key] = {"columns": cols, "indexes": idxs}

    def execute_sql_query(query: str) -> None:
        """Execute SQL query and store results."""
        nonlocal sql_query_results, sql_query_error, sql_execution_time, sql_query_history, sql_history_index
        
        if active_conn is None or active_adapter is None:
            sql_query_error = "No database connection"
            sql_query_results = None
            return
        
        if not query.strip():
            sql_query_error = "Empty query"
            sql_query_results = None
            return
        
        import time as time_module
        start_time = time_module.time()
        
        try:
            # Execute query
            rows, columns = active_adapter.execute_with_description(active_conn, query)
            sql_execution_time = time_module.time() - start_time
            sql_query_results = (rows, columns)
            sql_query_error = None
            
            # Add to history (avoid duplicates)
            query_clean = query.strip()
            if query_clean and (not sql_query_history or sql_query_history[-1] != query_clean):
                sql_query_history.append(query_clean)
                # Keep only last 50 queries
                if len(sql_query_history) > 50:
                    sql_query_history.pop(0)
            
            push_status(f"Query executed successfully in {sql_execution_time:.3f}s, {len(rows)} rows")
        except Exception as e:
            sql_execution_time = time_module.time() - start_time
            sql_query_error = str(e)
            sql_query_results = None
            push_status(f"Query error: {e}")

    def load_rows_for_table(where_clause: Optional[str] = None, reset_offset: bool = True) -> None:
        nonlocal rows, columns, rows_scroll_offset, current_where_clause, total_rows_count
        if (
            active_conn is None
            or active_adapter is None
            or selected_table_idx < 0
            or selected_table_idx >= len(tables)
        ):
            rows = []
            columns = []
            total_rows_count = 0
            return
        
        import time as time_module
        start_time = time_module.time()
        
        schema, table, _size = tables[selected_table_idx]
        key = (schema, table)
        
        if where_clause is not None:
            current_where_clause = where_clause
            table_where_clauses[key] = where_clause
            where_buffer.text = where_clause
        else:
            # Восстанавливаем WHERE для этой таблицы, если есть
            current_where_clause = table_where_clauses.get(key, "")
            where_buffer.text = current_where_clause
        
        # Восстанавливаем ORDER BY для этой таблицы, если есть
        current_order_by_clause = table_order_by_clauses.get(key, "")
        order_by_buffer.text = current_order_by_clause
        
        if reset_offset:
            rows_scroll_offset = 0
        
        cfg = connections[active_conn_idx]
        
        if cfg.db_type == "mongodb":
            # MongoDB использует специальные методы
            from database import MongoDBAdapter
            if isinstance(active_adapter, MongoDBAdapter):
                # Для MongoDB фильтр - это JSON строка
                filter_query = current_where_clause if current_where_clause.strip() else None
                
                # Получаем общее количество документов
                try:
                    db = active_conn[cfg.dbname]
                    coll = db[table]
                    if filter_query:
                        import json
                        try:
                            filter_dict = json.loads(filter_query)
                            total_rows_count = coll.count_documents(filter_dict)
                        except:
                            total_rows_count = coll.count_documents({})
                    else:
                        total_rows_count = coll.count_documents({})
                except:
                    total_rows_count = 0
                
                # Получаем образцы документов
                # Для MongoDB ORDER BY не поддерживается напрямую, но можно использовать sort в запросе
                # Пока оставляем без сортировки, можно добавить позже
                rows, columns = active_adapter.get_collection_sample(
                    active_conn, cfg.dbname, table, 
                    limit=rows_per_page, 
                    offset=rows_scroll_offset,
                    filter_query=filter_query
                )
                order_info = f", sort: {current_order_by_clause}" if current_order_by_clause.strip() else ""
                push_status(f"MongoDB: collection {table}, filter: {filter_query or '{}'}{order_info}")
                elapsed = time_module.time() - start_time
                push_status(f"Query executed in {elapsed:.3f}s")
            else:
                rows, columns = [], []
                total_rows_count = 0
        else:
            schema_quoted = active_adapter.quote_identifier(schema) if schema else ""
            table_quoted = active_adapter.quote_identifier(table)
            
            # Сначала получаем общее количество строк
            if schema and cfg.db_type not in ("sqlite", "clickhouse"):
                count_query = f"SELECT COUNT(*) FROM {schema_quoted}.{table_quoted}"
            elif cfg.db_type == "clickhouse":
                count_query = f"SELECT COUNT(*) FROM {table_quoted}"
            else:
                count_query = f"SELECT COUNT(*) FROM {table_quoted}"
            if current_where_clause.strip():
                count_query += f" WHERE {current_where_clause}"
            
            count_res = active_adapter.execute(active_conn, count_query)
            total_rows_count = count_res[0][0] if count_res else 0
            
            # Затем загружаем только нужную страницу с LIMIT и OFFSET
            if schema and cfg.db_type not in ("sqlite", "clickhouse"):
                base_query = f"SELECT * FROM {schema_quoted}.{table_quoted}"
            elif cfg.db_type == "clickhouse":
                base_query = f"SELECT * FROM {table_quoted}"
            else:
                base_query = f"SELECT * FROM {table_quoted}"
            if current_where_clause.strip():
                base_query += f" WHERE {current_where_clause}"
            if current_order_by_clause.strip():
                base_query += f" ORDER BY {current_order_by_clause}"
            
            # SQLite использует LIMIT и OFFSET, MySQL тоже, PostgreSQL тоже, ClickHouse тоже
            base_query += f" LIMIT {rows_per_page} OFFSET {rows_scroll_offset}"
            
            # Выводим SQL запрос в статус
            push_status(f"SQL: {base_query}")
            rows, columns = active_adapter.execute_with_description(active_conn, base_query)
            elapsed = time_module.time() - start_time
            push_status(f"Query executed in {elapsed:.3f}s")

    # если есть хотя бы одно подключение – сразу грузим его таблицы
    if connections:
        set_active_connection(selected_conn_idx)
        load_tables_for_connection()

    def render_connections() -> List[Tuple[str, str]]:
        result: List[Tuple[str, str]] = [("class:title", "Connections\n")]
        for i, cfg in enumerate(connections):
            prefix = "➤ " if i == selected_conn_idx else "  "
            label = f"{cfg.name} ({cfg.dbname})"
            style_name = "reverse" if (active_column == 0 and i == selected_conn_idx) else ""
            result.append((style_name, f"{prefix}{label}\n"))
        # ADD button
        result.append(("class:menu", "\n[ ADD ]\n"))
        return result

    def render_tables() -> List[Tuple[str, str]]:
        nonlocal table_offset, table_line_map
        cfg = connections[selected_conn_idx] if selected_conn_idx >= 0 else None
        title = "Collections\n" if cfg and cfg.db_type == "mongodb" else "Tables\n"
        result: List[Tuple[str, str]] = [("class:title", title)]
        table_line_map = [None]
        
        # Search filter is already applied in load_tables_for_connection
        
        if not tables:
            result.append(("", "  (no tables)\n"))
            table_line_map.append(None)
            return result

        window_size = get_table_window_size()
        max_offset = max(0, len(tables) - window_size)
        if table_offset > max_offset:
            table_offset = max_offset
        start = table_offset
        end = min(len(tables), start + window_size)

        for i in range(start, end):
            schema, name, size_bytes = tables[i]
            prefix = "➤ " if i == selected_table_idx else "  "
            # Для MongoDB schema пустой, показываем только имя коллекции
            if schema:
                label = f"{schema}.{name} ({format_size(size_bytes)})"
            else:
                label = f"{name} ({format_size(size_bytes)})"
            
            # Цветовая индикация размера: большие таблицы выделяем
            style_name = "reverse" if (active_column == 1 and i == selected_table_idx) else ""
            if size_bytes > 100 * 1024 * 1024:  # > 100MB
                size_style = "class:large-table" if not style_name else "reverse class:large-table"
            elif size_bytes > 10 * 1024 * 1024:  # > 10MB
                size_style = "class:medium-table" if not style_name else "reverse class:medium-table"
            else:
                size_style = style_name
            
            result.append((size_style, f"{prefix}{label}\n"))
            table_line_map.append(i)

            # Table details (columns and indexes) below it, if loaded
            details = table_details.get((schema, name))
            if details:
                cols = details.get("columns") or []
                idxs = details.get("indexes") or []
                if cols:
                    result.append(("", "      Columns:\n"))
                    table_line_map.append(i)
                    for col in cols:
                        result.append(("", f"        - {col}\n"))
                        table_line_map.append(i)
                if idxs:
                    result.append(("", "      Indexes:\n"))
                    table_line_map.append(i)
                    for idx in idxs:
                        result.append(("", f"        - {idx}\n"))
                        table_line_map.append(i)

        return result

    def render_rows() -> List[Tuple[str, str]]:
        result: List[Tuple[str, str]] = []
        
        # Header with pagination info, arrows and CSV button
        start_row = rows_scroll_offset + 1
        end_row = min(rows_scroll_offset + len(rows), total_rows_count)
        page_info = f"Rows {start_row}-{end_row} of {total_rows_count}" if total_rows_count > 0 else "No data"
        
        # Pagination arrows (clickable)
        # ◀ - previous page (decreases offset)
        # ▶ - next page (increases offset)
        can_prev = rows_scroll_offset > 0
        can_next = rows_scroll_offset + rows_per_page < total_rows_count
        
        result.append(("class:title", f"Data ({page_info})  "))
        # Left arrow ◀ - previous page
        if can_prev:
            result.append(("class:menu", "◀"))
        else:
            result.append(("", " "))
        result.append(("", " "))
        # Right arrow ▶ - next page
        if can_next:
            result.append(("class:menu", "▶"))
        else:
            result.append(("", " "))
        result.append(("", "  "))
        # Кнопки экспорта
        result.append(("class:menu", "[ CSV ]"))
        result.append(("", " "))
        result.append(("class:menu", "[ JSON ]"))
        result.append(("", "\n"))
        
        if not rows:
            result.append(("", "  (no data)\n"))
            return result
        
        # rows уже содержит только текущую страницу (10 строк)
        visible_rows = rows

        headers = list(columns)
        if not headers and visible_rows:
            first = visible_rows[0]
            if isinstance(first, (list, tuple)):
                headers = [f"col_{i+1}" for i in range(len(first))]
            else:
                headers = ["value"]

        if not headers:
            result.append(("", "  (no columns)\n"))
            return result

        num_cols = len(headers)
        max_cell_width = 30  # Максимальная ширина ячейки
        table_data: List[List[str]] = []
        
        def clean_cell(value: any) -> str:
            """Clean cell from HTML and limit size."""
            # Конвертируем в строку
            cell_str = str(value) if value is not None else ""
            # Удаляем HTML теги
            cell_str = re.sub(r'<[^>]+>', '', cell_str)
            # Заменяем множественные пробелы на один
            cell_str = re.sub(r'\s+', ' ', cell_str)
            # Удаляем переносы строк
            cell_str = cell_str.replace("\n", " ").replace("\r", "")
            # Ограничиваем размер
            if len(cell_str) > max_cell_width:
                cell_str = cell_str[:max_cell_width - 3] + "..."
            return cell_str.strip()
        
        for row in visible_rows:
            if isinstance(row, (list, tuple)):
                cells = [clean_cell(v) for v in row]
            elif isinstance(row, dict):
                cells = [clean_cell(row.get(h, "")) for h in headers]
            else:
                cells = [clean_cell(row)]

            if len(cells) < num_cols:
                cells.extend([""] * (num_cols - len(cells)))
            elif len(cells) > num_cols:
                cells = cells[:num_cols]

            table_data.append(cells)

        # Проверяем что есть данные перед вызовом termtables
        if not table_data:
            result.append(("", "  (no data to display)\n"))
            return result

        # Ограничиваем ширину заголовков тоже
        headers_clean = [h[:max_cell_width] + "..." if len(h) > max_cell_width else h for h in headers]
        
        table_str = tt.to_string(
            table_data,
            header=headers_clean,
            style=tt.styles.thin_thick,
        )
        for line in table_str.splitlines():
            result.append(("", line + "\n"))
        
        # Показываем статистику таблицы внизу
        if total_rows_count > 0:
            result.append(("", "\n"))
            result.append(("class:hint", f"📊 Total rows: {total_rows_count:,}\n"))
        
        return result

    def render_sql_editor() -> List[Tuple[str, str]]:
        """Render SQL editor header."""
        result: List[Tuple[str, str]] = []
        result.append(("class:title", "SQL Editor (Ctrl+E to open, Esc to close, Ctrl+Enter/F5 to execute)\n"))
        if active_conn is None or active_adapter is None:
            result.append(("class:error", "  No database connection\n"))
        else:
            cfg = connections[active_conn_idx] if active_conn_idx >= 0 else None
            if cfg:
                result.append(("class:hint", f"  Connected to: {cfg.name} ({cfg.dbname})\n"))
        return result

    def render_sql_results() -> List[Tuple[str, str]]:
        """Render SQL query results."""
        result: List[Tuple[str, str]] = []
        
        if sql_query_error:
            result.append(("class:error", f"Error: {sql_query_error}\n"))
            if sql_execution_time:
                result.append(("class:hint", f"Execution time: {sql_execution_time:.3f}s\n"))
            return result
        
        if sql_query_results is None:
            result.append(("class:hint", "  No query executed yet. Press Ctrl+Enter to execute.\n"))
            return result
        
        rows, columns = sql_query_results
        
        if not rows:
            result.append(("class:hint", "  Query returned no rows\n"))
            if sql_execution_time:
                result.append(("class:hint", f"Execution time: {sql_execution_time:.3f}s\n"))
            return result
        
        # Show execution time and row count
        result.append(("class:title", f"Results ({len(rows)} rows"))
        if sql_execution_time:
            result.append(("class:hint", f" in {sql_execution_time:.3f}s"))
        result.append(("", "\n"))
        
        # Prepare table data
        max_cell_width = 30
        table_data = []
        headers = columns[:20]  # Limit columns
        num_cols = len(headers)
        
        for row in rows[:100]:  # Limit rows for display
            cells = []
            for i, val in enumerate(row[:num_cols]):
                cell_str = str(val) if val is not None else "NULL"
                # Clean HTML
                cell_str = re.sub(r"<[^>]+>", "", cell_str)
                cell_str = re.sub(r"\s+", " ", cell_str).strip()
                # Truncate
                if len(cell_str) > max_cell_width:
                    cell_str = cell_str[:max_cell_width] + "..."
                cells.append(cell_str)
            
            if len(cells) < num_cols:
                cells.extend([""] * (num_cols - len(cells)))
            
            table_data.append(cells)
        
        if not table_data:
            result.append(("", "  (no data to display)\n"))
            return result
        
        # Limit header width
        headers_clean = [h[:max_cell_width] + "..." if len(h) > max_cell_width else h for h in headers]
        
        try:
            table_str = tt.to_string(
                table_data,
                header=headers_clean,
                style=tt.styles.thin_thick,
            )
            for line in table_str.splitlines():
                result.append(("", line + "\n"))
        except Exception as e:
            result.append(("class:error", f"  Error rendering table: {e}\n"))
        
        if len(rows) > 100:
            result.append(("class:hint", f"\n  ... showing first 100 of {len(rows)} rows\n"))
        
        return result

    def render_status() -> List[Tuple[str, str]]:
        result: List[Tuple[str, str]] = [("class:title", "Status\n")]
        
        # Check for updates (non-blocking, cached)
        if not hasattr(render_status, '_update_checked'):
            render_status._update_checked = True
            render_status._has_update = False
            render_status._latest_version = None
            
            # Check in background (simple check, won't block)
            try:
                has_update, latest = check_for_updates()
                render_status._has_update = has_update
                render_status._latest_version = latest
            except Exception:
                pass  # Silently fail if check fails
        
        # Show update notification if available
        if getattr(render_status, '_has_update', False) and getattr(render_status, '_latest_version', None):
            latest = render_status._latest_version
            result.append(("class:hint", f"  ⚠️  Update available: v{latest} (current: v{CURRENT_VERSION})\n"))
            result.append(("class:hint", f"  Run 'dbrowse --update' to update\n"))
        
        if not status_messages:
            if not getattr(render_status, '_has_update', False):
                result.append(("", "  no messages\n"))
            return result
        for msg in status_messages[-5:]:
            result.append(("", f"  {msg}\n"))
        return result

    kb = KeyBindings()

    @kb.add("q")
    def _(event) -> None:
        nonlocal sql_editor_mode
        if sql_editor_mode:
            sql_editor_mode = False
            event.app.layout = Layout(HSplit([root_container, status_window]))
            event.app.invalidate()
        else:
            event.app.exit(result="quit")
    
    @kb.add("c-e")
    def _(event) -> None:
        """Open SQL editor."""
        nonlocal sql_editor_mode, sql_history_index
        sql_editor_mode = True
        sql_history_index = -1
        event.app.layout = Layout(HSplit([sql_editor_container, status_window]))
        event.app.layout.focus(sql_editor_window)
        event.app.invalidate()

    @kb.add("tab")
    def _(event) -> None:
        nonlocal active_column, sql_editor_mode
        
        # Don't handle tab in SQL editor mode
        if sql_editor_mode:
            return
        
        # Проверяем текущий фокус через has_focus
        has_order_by = event.app.layout.has_focus(order_by_buffer_window)
        has_where = event.app.layout.has_focus(where_buffer_window)
        has_table_search = event.app.layout.has_focus(table_search_window)
        has_tables = event.app.layout.has_focus(middle_tables_window)
        has_left = event.app.layout.has_focus(left_window)
        
        # Если мы в колонке данных (active_column == 2)
        if active_column == 2:
            # Если фокус на ORDER BY - переключаемся на WHERE
            if has_order_by:
                event.app.layout.focus(where_buffer_window)
                event.app.invalidate()
                return
            # Если фокус на WHERE - переключаемся на следующую колонку (подключения)
            elif has_where:
                active_column = 0
                event.app.layout.focus(left_window)
                event.app.invalidate()
                return
            # Если фокус нигде или на данных - начинаем с ORDER BY
            else:
                event.app.layout.focus(order_by_buffer_window)
                event.app.invalidate()
                return
        
        # Если мы в колонке таблиц (active_column == 1)
        if active_column == 1:
            # Если фокус на поле поиска - переключаемся на список таблиц
            if has_table_search:
                event.app.layout.focus(middle_tables_window)
                event.app.invalidate()
                return
            # Если фокус на списке таблиц - переключаемся на следующую колонку (данные)
            elif has_tables:
                active_column = 2
                event.app.layout.focus(order_by_buffer_window)
                event.app.invalidate()
                return
            # Иначе (фокус нигде) - переключаемся на следующую колонку (данные)
            else:
                active_column = 2
                event.app.layout.focus(order_by_buffer_window)
                event.app.invalidate()
                return
        
        # Если мы в колонке подключений (active_column == 0)
        if active_column == 0:
            # Переключаемся на колонку таблиц, начинаем с поля поиска
            active_column = 1
            event.app.layout.focus(table_search_window)
            event.app.invalidate()
            return

    @kb.add("up")
    def _(event) -> None:
        """Handle up arrow - SQL history or table navigation."""
        nonlocal selected_conn_idx, selected_table_idx, table_offset, sql_history_index, sql_editor_mode
        
        # SQL editor history navigation
        if sql_editor_mode:
            if sql_editor_buffer.has_focus():
                if sql_query_history:
                    if sql_history_index < 0:
                        # Save current query before navigating
                        current = sql_editor_buffer.text.strip()
                        if current and (not sql_query_history or sql_query_history[-1] != current):
                            sql_query_history.append(current)
                    sql_history_index = min(len(sql_query_history) - 1, sql_history_index + 1)
                    if sql_history_index >= 0:
                        sql_editor_buffer.text = sql_query_history[-(sql_history_index + 1)]
                    event.app.invalidate()
                return
        
        # Если фокус на WHERE - переключаемся на ORDER BY
        try:
            if event.app.layout.has_focus(where_buffer_window):
                event.app.layout.focus(order_by_buffer_window)
                event.app.invalidate()
                return
            # Если фокус на полях ввода - не обрабатываем стрелки для навигации
            if event.app.layout.has_focus(order_by_buffer_window) or event.app.layout.has_focus(table_search_window):
                return
        except (ValueError, AttributeError):
            pass  # Windows not in layout
        if active_column == 0 and connections:
            selected_conn_idx = max(0, selected_conn_idx - 1)
        elif active_column == 1 and tables:
            selected_table_idx = max(0, selected_table_idx - 1)
            if selected_table_idx < table_offset:
                table_offset = selected_table_idx
        event.app.invalidate()

    # Down handler moved above - check sql_editor_mode first
    def handle_down_original(event) -> None:
        nonlocal selected_conn_idx, selected_table_idx, table_offset
        # Если фокус на ORDER BY - переключаемся на WHERE
        try:
            if event.app.layout.has_focus(order_by_buffer_window):
                event.app.layout.focus(where_buffer_window)
                event.app.invalidate()
                return
            # Если фокус на полях ввода - не обрабатываем стрелки для навигации
            if event.app.layout.has_focus(where_buffer_window) or event.app.layout.has_focus(table_search_window):
                return
        except (ValueError, AttributeError):
            pass  # Windows not in layout
        if active_column == 0 and connections:
            selected_conn_idx = min(len(connections) - 1, selected_conn_idx + 1)
        elif active_column == 1 and tables:
            selected_table_idx = min(len(tables) - 1, selected_table_idx + 1)
            window_size = get_table_window_size()
            if selected_table_idx >= table_offset + window_size:
                table_offset = max(0, selected_table_idx - window_size + 1)
        event.app.invalidate()

    @kb.add("c-p")
    def _(event) -> None:
        nonlocal rows_scroll_offset
        if rows_scroll_offset > 0:
            rows_scroll_offset = max(0, rows_scroll_offset - rows_per_page)
            load_rows_for_table(reset_offset=False)
            event.app.invalidate()

    @kb.add("c-n")
    def _(event) -> None:
        nonlocal rows_scroll_offset
        # Проверяем что есть следующая страница
        if total_rows_count > 0 and rows_scroll_offset + rows_per_page < total_rows_count:
            rows_scroll_offset += rows_per_page
            load_rows_for_table(reset_offset=False)
            event.app.invalidate()

    @kb.add("enter")
    def _(event) -> None:
        nonlocal current_where_clause, current_order_by_clause, sql_editor_mode
        
        # Don't handle enter in SQL editor mode (except for executing query)
        if sql_editor_mode:
            return
        
        # Проверяем, не находится ли фокус на Buffer
        try:
            if event.app.layout.has_focus(where_buffer_window):
                # Применить WHERE фильтр
                new_where = where_buffer.text.strip()
                schema, table, _size = tables[selected_table_idx] if tables and selected_table_idx >= 0 else (None, None, 0)
                if schema and table:
                    key = (schema, table)
                    table_where_clauses[key] = new_where
                current_where_clause = new_where
                load_rows_for_table(new_where)
                event.app.invalidate()
                return
            elif event.app.layout.has_focus(order_by_buffer_window):
                # Применить ORDER BY
                new_order_by = order_by_buffer.text.strip()
                schema, table, _size = tables[selected_table_idx] if tables and selected_table_idx >= 0 else (None, None, 0)
                if schema and table:
                    key = (schema, table)
                    table_order_by_clauses[key] = new_order_by
                current_order_by_clause = new_order_by
                load_rows_for_table()
                event.app.invalidate()
                return
            elif event.app.layout.has_focus(table_search_window):
                # Применить поиск
                nonlocal table_search_filter
                table_search_filter = table_search_buffer.text.strip()
                load_tables_for_connection()
                try:
                    event.app.layout.focus(middle_tables_window)
                except (ValueError, AttributeError):
                    pass
                event.app.invalidate()
                return
        except (ValueError, AttributeError):
            pass  # Windows not in layout
        
        if active_column == 0:
            load_tables_for_connection()
            event.app.invalidate()
        elif active_column == 1:
            # При Enter в колонке таблиц переключаемся на колонку данных
            active_column = 2
            load_rows_for_table()
            try:
                event.app.layout.focus(order_by_buffer_window)
            except (ValueError, AttributeError):
                pass
            event.app.invalidate()

    @kb.add("escape")
    def _(event) -> None:
        nonlocal current_where_clause, current_order_by_clause, sql_editor_mode
        
        # Close SQL editor on Esc
        if sql_editor_mode:
            sql_editor_mode = False
            event.app.layout = Layout(HSplit([root_container, status_window]))
            event.app.invalidate()
            return
        
        try:
            if event.app.layout.has_focus(where_buffer_window):
                # Очистить WHERE
                schema, table, _size = tables[selected_table_idx] if tables and selected_table_idx >= 0 else (None, None, 0)
                if schema and table:
                    key = (schema, table)
                    table_where_clauses[key] = ""
                current_where_clause = ""
                where_buffer.text = ""
                load_rows_for_table()
                event.app.invalidate()
                return
                return
            elif event.app.layout.has_focus(order_by_buffer_window):
                # Очистить ORDER BY
                schema, table, _size = tables[selected_table_idx] if tables and selected_table_idx >= 0 else (None, None, 0)
                if schema and table:
                    key = (schema, table)
                    table_order_by_clauses[key] = ""
                current_order_by_clause = ""
                order_by_buffer.text = ""
                load_rows_for_table()
                event.app.invalidate()
                return
            elif event.app.layout.has_focus(table_search_window):
                # Очистить поиск
                table_search_filter = ""
                table_search_buffer.text = ""
                load_tables_for_connection()
                event.app.invalidate()
                return
        except (ValueError, AttributeError):
            pass  # Windows not in layout
        
        if active_column == 2:
            # Очистить оба поля
            schema, table, _size = tables[selected_table_idx] if tables and selected_table_idx >= 0 else (None, None, 0)
            if schema and table:
                key = (schema, table)
                table_where_clauses[key] = ""
                table_order_by_clauses[key] = ""
            current_where_clause = ""
            current_order_by_clause = ""
            where_buffer.text = ""
            order_by_buffer.text = ""
            load_rows_for_table()
            event.app.invalidate()

    @kb.add("f")
    def _(event) -> None:
        """Фокус на поле поиска таблиц."""
        nonlocal active_column, sql_editor_mode
        if sql_editor_mode:
            return  # Don't handle in SQL editor mode
        if active_column == 1:
            try:
                event.app.layout.focus(table_search_window)
            except ValueError:
                pass  # Window not in layout
            event.app.invalidate()
    
    @kb.add("c-f")
    def _(event) -> None:
        """Очистить поиск по таблицам."""
        nonlocal table_search_filter
        if active_column == 1:
            table_search_filter = ""
            table_search_buffer.text = ""
            load_tables_for_connection()
            push_status("Search cleared")
            event.app.invalidate()
    
    @kb.add("c-m")
    def _(event) -> None:
        """Execute SQL query in editor (Ctrl+Enter or Ctrl+M)."""
        nonlocal sql_editor_mode
        if sql_editor_mode:
            query = sql_editor_buffer.text
            execute_sql_query(query)
            event.app.invalidate()
    
    @kb.add("f5")
    def _(event) -> None:
        """Execute SQL query in editor (F5)."""
        nonlocal sql_editor_mode
        if sql_editor_mode:
            query = sql_editor_buffer.text
            execute_sql_query(query)
            event.app.invalidate()
    

    def connections_mouse_handler(mouse_event) -> None:
        nonlocal selected_conn_idx
        app = get_app()
        if mouse_event.event_type == MouseEventType.SCROLL_UP:
            if connections:
                selected_conn_idx = max(0, selected_conn_idx - 1)
                load_tables_for_connection()
                app.invalidate()
            return
        if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            if connections:
                selected_conn_idx = min(len(connections) - 1, selected_conn_idx + 1)
                load_tables_for_connection()
                app.invalidate()
            return
        if mouse_event.event_type != MouseEventType.MOUSE_UP:
            return
        y = mouse_event.position.y
        # y = 0   -> заголовок "Базы"
        # y = 1..len(connections) -> конкретная база
        # последняя строка -> кнопка ADD
        if y == 0:
            return
        if 1 <= y <= len(connections):
            selected_conn_idx = y - 1
            load_tables_for_connection()
            app.invalidate()
        else:
            # предполагаем, что это клик по ADD
            app.exit(result="add")

    def tables_mouse_handler(mouse_event) -> None:
        nonlocal selected_table_idx, table_offset, last_table_click, last_click_time, active_column
        app = get_app()

        if mouse_event.event_type == MouseEventType.SCROLL_UP:
            if tables:
                selected_table_idx = max(0, selected_table_idx - 1)
                if selected_table_idx < table_offset:
                    table_offset = selected_table_idx
                load_rows_for_table()
                app.invalidate()
            return

        if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            if tables:
                selected_table_idx = min(len(tables) - 1, selected_table_idx + 1)
                window_size = get_table_window_size()
                if selected_table_idx >= table_offset + window_size:
                    table_offset = max(0, selected_table_idx - window_size + 1)
                load_rows_for_table()
                app.invalidate()
            return

        if mouse_event.event_type != MouseEventType.MOUSE_UP:
            return

        y = mouse_event.position.y
        if y < 0 or y >= len(table_line_map):
            return
        mapped_idx = table_line_map[y]
        if mapped_idx is None or mapped_idx >= len(tables):
            return

        selected_table_idx = mapped_idx
        schema, table, _size = tables[selected_table_idx]

        now = time.time()
        key = (schema, table)
        is_double = last_table_click == key and (now - last_click_time) < 0.4
        last_table_click = key
        last_click_time = now

        if mouse_event.button == MouseButton.LEFT and is_double:
            if key in table_details:
                del table_details[key]
            else:
                load_table_details(schema, table)

        # При клике на таблицу переключаемся на колонку данных и устанавливаем фокус на ORDER BY
        active_column = 2
        load_rows_for_table()
        app.layout.focus(order_by_buffer_window)
        app.invalidate()

    left_window = Window(
        ClickableTextControl(render_connections, on_click=connections_mouse_handler),
        wrap_lines=False,
        width=26,
    )
    
    # Поле поиска таблиц
    table_search_window = Window(
        BufferControl(table_search_buffer),
        height=3,
        style="class:menu" if active_column == 1 else "",
        get_line_prefix=lambda line_number, wrap_count: [("class:menu", "🔍 Search: ")] if line_number == 0 else [("", "")],
    )
    
    # Поиск применяется при нажатии Enter, не автоматически
    
    middle_tables_window = Window(
        ClickableTextControl(render_tables, on_click=tables_mouse_handler),
        wrap_lines=False,
        width=40,
    )
    
    middle_window = HSplit([
        table_search_window,
        middle_tables_window,
    ])
    # Поле ввода ORDER BY - видимое и интерактивное
    order_by_buffer_window = Window(
        BufferControl(order_by_buffer),
        height=3,
        style="class:menu" if active_column == 2 else "",
        get_line_prefix=lambda line_number, wrap_count: [("class:menu", "ORDER BY: ")] if line_number == 0 else [("", "")],
    )
    
    # Поле ввода WHERE - видимое и интерактивное
    where_buffer_window = Window(
        BufferControl(where_buffer),
        height=3,
        style="class:menu" if active_column == 2 else "",
        get_line_prefix=lambda line_number, wrap_count: [("class:menu", "WHERE: ")] if line_number == 0 else [("", "")],
    )
    
    def export_to_csv() -> None:
        """Export current data to CSV file."""
        if not rows or not columns:
            push_status("No data to export")
            return
        
        schema, table, _size = tables[selected_table_idx] if tables and selected_table_idx >= 0 else ("", "", 0)
        cfg = connections[active_conn_idx]
        
        # Генерируем имя файла
        table_name = table or "data"
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{cfg.name}_{table_name}_{timestamp}.csv"
        
        try:
            import csv
            
            def clean_for_csv(value: any) -> str:
                """Clean value for CSV."""
                if value is None:
                    return ""
                cell_str = str(value)
                # Удаляем HTML теги
                cell_str = re.sub(r'<[^>]+>', '', cell_str)
                # Удаляем переносы строк
                cell_str = cell_str.replace("\n", " ").replace("\r", "")
                return cell_str
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Записываем заголовки
                writer.writerow(columns)
                # Записываем данные
                for row in rows:
                    cleaned_row = [clean_for_csv(v) for v in row]
                    writer.writerow(cleaned_row)
            push_status(f"Exported to {filename}")
        except Exception as e:
            push_status(f"Export error: {e}")
    
    def export_to_json() -> None:
        """Export current data to JSON file."""
        if not rows or not columns:
            push_status("No data to export")
            return
        
        schema, table, _size = tables[selected_table_idx] if tables and selected_table_idx >= 0 else ("", "", 0)
        cfg = connections[active_conn_idx]
        
        # Генерируем имя файла
        table_name = table or "data"
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{cfg.name}_{table_name}_{timestamp}.json"
        
        try:
            import json
            from datetime import date, datetime, time as dt_time
            from decimal import Decimal
            
            class JSONEncoder(json.JSONEncoder):
                """Кастомный encoder для обработки дат и других типов."""
                def default(self, obj):
                    if isinstance(obj, (date, datetime)):
                        return obj.isoformat()
                    elif isinstance(obj, dt_time):
                        return obj.isoformat()
                    elif isinstance(obj, Decimal):
                        return float(obj)
                    elif isinstance(obj, bytes):
                        return obj.decode('utf-8', errors='replace')
                    elif hasattr(obj, '__dict__'):
                        return str(obj)
                    return super().default(obj)
            
            data = []
            for row in rows:
                row_dict = {}
                for col, val in zip(columns, row):
                    # Конвертируем значения для JSON
                    if val is None:
                        row_dict[col] = None
                    elif isinstance(val, (date, datetime, dt_time, Decimal, bytes)):
                        row_dict[col] = JSONEncoder().default(val)
                    else:
                        row_dict[col] = val
                data.append(row_dict)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, cls=JSONEncoder)
            push_status(f"Exported to {filename}")
        except Exception as e:
            push_status(f"Export error: {e}")
    
    def copy_cell_value(row_idx: int, col_idx: int) -> None:
        """Copy cell value to clipboard."""
        try:
            import subprocess
            import sys
            
            if row_idx < len(rows) and col_idx < len(columns):
                value = str(rows[row_idx][col_idx])
                
                # Пытаемся скопировать в буфер обмена
                try:
                    if sys.platform == "darwin":  # macOS
                        subprocess.run(["pbcopy"], input=value.encode('utf-8'), check=True, timeout=1)
                    elif sys.platform == "linux":  # Linux
                        subprocess.run(["xclip", "-selection", "clipboard"], input=value.encode('utf-8'), check=True, timeout=1)
                    elif sys.platform == "win32":  # Windows
                        subprocess.run(["clip"], input=value.encode('utf-8'), check=True, timeout=1)
                    else:
                        # Fallback: просто показываем значение
                        push_status(f"Value: {value[:50]}")
                        return
                    
                    push_status(f"✓ Copied: {value[:50]}{'...' if len(value) > 50 else ''}")
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    # If command not found, just show the value
                    push_status(f"Value: {value[:100]}")
        except Exception as e:
            push_status(f"Copy error: {e}")
    
    # Данные с обработчиком мыши для стрелок пагинации и кнопки CSV
    def rows_mouse_handler(mouse_event) -> None:
        nonlocal rows_scroll_offset
        app = get_app()
        if mouse_event.event_type != MouseEventType.MOUSE_UP:
            return
        
        # Обработка клика по ячейке данных (не заголовок)
        # termtables добавляет разделители, поэтому нужно учесть это
        if mouse_event.position.y > 2 and rows:  # y=0 заголовок, y=1 разделитель, y=2 первая строка
            try:
                # Определяем строку: вычитаем заголовок, разделитель и учитываем что каждая строка данных занимает 1 строку
                clicked_row = mouse_event.position.y - 3  # -3 для заголовка, разделителя и первой строки
                if 0 <= clicked_row < len(rows):
                    # Упрощенно: копируем первую колонку (можно улучшить для определения колонки по x)
                    copy_cell_value(clicked_row, 0)
                    app.invalidate()
                    return
            except:
                pass
        
        # Проверяем клик по заголовку (строка 0)
        if mouse_event.position.y == 0:
            x = mouse_event.position.x
            # Вычисляем примерную позицию стрелок и кнопки CSV
            start_row = rows_scroll_offset + 1
            end_row = min(rows_scroll_offset + len(rows), total_rows_count)
            page_info = f"Строки {start_row}-{end_row} из {total_rows_count}" if total_rows_count > 0 else "Нет данных"
            title_text = f"Данные ({page_info})  "
            title_len = len(title_text)
            
            # Позиции элементов:
            # Левая стрелка ◀ - позиция title_len
            # Правая стрелка ▶ - позиция title_len + 3
            # Кнопка [ CSV ] - позиция title_len + 6
            # Кнопка [ JSON ] - позиция title_len + 14
            
            # Проверяем клик по кнопке JSON
            if title_len + 14 <= x <= title_len + 22:
                export_to_json()
                app.invalidate()
                return
            
            # Проверяем клик по кнопке CSV
            if title_len + 6 <= x <= title_len + 14:
                export_to_csv()
                app.invalidate()
                return
            
            # Проверяем клик по правой стрелке (▶) - следующая страница
            if title_len + 3 <= x < title_len + 6:
                if total_rows_count > 0 and rows_scroll_offset + rows_per_page < total_rows_count:
                    rows_scroll_offset += rows_per_page
                    load_rows_for_table(reset_offset=False)
                    app.invalidate()
                    return
            
            # Проверяем клик по левой стрелке (◀) - предыдущая страница
            if title_len <= x < title_len + 3:
                if rows_scroll_offset > 0:
                    rows_scroll_offset = max(0, rows_scroll_offset - rows_per_page)
                    load_rows_for_table(reset_offset=False)
                    app.invalidate()
                    return
    
    right_data_window = Window(
        ClickableTextControl(render_rows, on_click=rows_mouse_handler),
        wrap_lines=False,
    )
    
    right_window = HSplit([
        order_by_buffer_window,
        where_buffer_window,
        right_data_window,
    ])

    # SQL Editor windows (created before use)
    sql_editor_header_window = Window(
        FormattedTextControl(render_sql_editor),
        height=3,
    )
    sql_editor_window = Window(
        BufferControl(
            sql_editor_buffer,
            lexer=PygmentsLexer(SqlLexer),
        ),
        wrap_lines=False,
    )
    sql_results_window = Window(
        FormattedTextControl(render_sql_results),
        wrap_lines=False,
    )
    
    sql_editor_container = HSplit([
        sql_editor_header_window,
        sql_editor_window,
        sql_results_window,
    ])

    root_container = VSplit(
        [
            left_window,
            middle_window,
            right_window,
        ],
        padding=1,
    )

    status_window = Window(
        FormattedTextControl(render_status),
        height=6,
        wrap_lines=True,
    )
    
    app = Application(
        layout=Layout(HSplit([root_container, status_window])),
        key_bindings=kb,
        full_screen=True,
        style=style,
        mouse_support=True,
    )
    try:
        result = app.run()
    finally:
        if active_conn is not None and active_adapter is not None:
            try:
                active_adapter.close(active_conn)
            except Exception:
                pass
        active_conn = None
        active_conn_idx = -1
        active_adapter = None
    return result or "quit"

