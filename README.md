# dbrowse

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**dbrowse** is a terminal-based database management utility (TUI) for Python, providing a lightweight alternative to GUI database tools like pgAdmin. It supports multiple database types and offers an intuitive interface for browsing databases, tables, and data.

## Features

- 🗄️ **Multi-database support**: PostgreSQL, MySQL/MariaDB, SQLite, MongoDB, and ClickHouse
- 📊 **Interactive TUI**: Full-screen terminal interface with mouse and keyboard navigation
- 🔍 **Quick search**: Filter tables and data with WHERE clauses
- 📤 **Data export**: Export query results to CSV or JSON
- 💾 **Connection management**: Save and reuse database connections
- ⚡ **Fast pagination**: Efficient data loading with SQL LIMIT/OFFSET
- 🎨 **Visual indicators**: Color-coded table sizes and query execution times

## Supported Databases

- **PostgreSQL** — Relational database
- **MySQL/MariaDB** — Relational database
- **SQLite** — Embedded database
- **MongoDB** — NoSQL document database
- **ClickHouse** — Column-oriented analytical database

## Installation

### Prerequisites

- Python 3.8 or higher
- pip

### Setup

1. Clone the repository:

```bash
git clone https://gitlab.com/yourusername/dbrowse.git
cd dbrowse
```

2. Create a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Quick Start

```bash
python main.py
```

The application will open a full-screen TUI with three columns:
- **Left column**: List of saved database connections
- **Middle column**: Tables/collections in the selected database
- **Right column**: Data from the selected table

### Adding a Database Connection

1. Click the **ADD** button in the left column
2. Enter connection details:
   - Connection name
   - Database type (PostgreSQL, MySQL, SQLite, MongoDB, ClickHouse)
   - Host, port, database name
   - Username and password (if required)

Connections are saved to `~/.config/dbrowse/connections.json` for future use.

### Environment Variables

You can also set a connection via the `DATABASE_URL` environment variable:

```bash
# PostgreSQL
export DATABASE_URL="postgresql://user:password@localhost:5432/postgres"

# MySQL
export DATABASE_URL="mysql://user:password@localhost:3306/mydb"

# SQLite
export DATABASE_URL="sqlite:///path/to/database.db"

# MongoDB
export DATABASE_URL="mongodb://user:password@localhost:27017/mydb"

# ClickHouse
export DATABASE_URL="clickhouse://user:password@localhost:9000/mydb"
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Tab` | Switch between columns |
| `↑/↓` | Navigate items in active column |
| `Enter` | Load tables/data; apply WHERE/ORDER BY |
| `Esc` | Clear WHERE or ORDER BY field |
| `Ctrl+P` | Previous page of data |
| `Ctrl+N` | Next page of data |
| `f` | Focus table search field |
| `Ctrl+F` | Clear table search |
| `q` | Quit application |

### Mouse Controls

- **Click** on database/table to select
- **Double-click** on table to view structure (columns and indexes)
- **Click** on `◀ ▶` arrows for pagination
- **Click** on `[ CSV ]` or `[ JSON ]` to export data
- **Click** on data cell to copy value to clipboard

### Filtering and Sorting

- **WHERE field**: Enter SQL WHERE clause (e.g., `id > 100`, `name LIKE '%test%'`)
  - For MongoDB: Use JSON format (e.g., `{"age": {"$gt": 18}}`)
- **ORDER BY field**: Enter sorting clause (e.g., `id DESC`, `name ASC`)
- **Table search**: Press `f` to filter table list by name

### Data Export

- **CSV export**: Click `[ CSV ]` button to export current data view
- **JSON export**: Click `[ JSON ]` button to export current data view
- Files are saved in the current directory with timestamp

## Project Structure

```
dbrowse/
├── main.py          # Application entry point
├── database.py      # Database adapters and connection management
├── ui.py            # TUI components and rendering
├── utils.py         # Utility functions
├── requirements.txt # Python dependencies
└── README.md        # This file
```

## Requirements

- Python 3.8+
- prompt_toolkit 3.0.48+
- psycopg2-binary (for PostgreSQL)
- pymysql (for MySQL/MariaDB)
- pymongo (for MongoDB)
- clickhouse-driver (for ClickHouse)
- python-dotenv
- termtables
- pyperclip

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [prompt_toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit)
- Inspired by [lazydocker](https://github.com/jesseduffield/lazydocker) and [lazygit](https://github.com/jesseduffield/lazygit) - amazing TUI tools
- Inspired by pgAdmin and other database management tools

## Support

For issues, feature requests, or questions, please open an issue on GitLab.
