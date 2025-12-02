# dbrowse

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-0.1.0-green.svg)](https://github.com/4nzor/dbrowse)
[![GitHub stars](https://img.shields.io/github/stars/4nzor/dbrowse?style=social)](https://github.com/4nzor/dbrowse)

**dbrowse** is a terminal-based database management utility (TUI) for Python, providing a lightweight alternative to GUI database tools like pgAdmin. It supports multiple database types and offers an intuitive interface for browsing databases, tables, and data.

> 💡 **Inspired by** [lazydocker](https://github.com/jesseduffield/lazydocker) and [lazygit](https://github.com/jesseduffield/lazygit) - bringing the same lazy, efficient experience to database management!

## ✨ Features

- 🗄️ **Multi-database support**: PostgreSQL, MySQL/MariaDB, SQLite, MongoDB, and ClickHouse
- 📊 **Interactive TUI**: Full-screen terminal interface with mouse and keyboard navigation
- 🔍 **Quick search**: Filter tables and data with WHERE clauses
- 📤 **Data export**: Export query results to CSV or JSON
- 💾 **Connection management**: Save and reuse database connections
- ⚡ **Fast pagination**: Efficient data loading with SQL LIMIT/OFFSET
- 🎨 **Visual indicators**: Color-coded table sizes and query execution times
- 📋 **Copy to clipboard**: Click any cell to copy its value
- 🔎 **Table structure view**: Double-click to see columns and indexes
- ⏱️ **Query timing**: See how long your queries take to execute

## 📸 Screenshots

> 📝 **Note**: Screenshots coming soon! Want to help? Take a screenshot of dbrowse in action and open a PR!

<!-- 
Add screenshots here when available:
![Main View](docs/screenshots/main.png)
![Table View](docs/screenshots/table.png)
![Filter View](docs/screenshots/filter.png)
-->

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
git clone https://github.com/4nzor/dbrowse.git
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

Or use Makefile for easier setup:

```bash
make setup          # Create venv and install dependencies
make quickstart     # Setup + create test database
make install-package # Install as command (dbrowse/dbrowser)
```

See [INSTALL.md](INSTALL.md) for detailed installation instructions.

### Create Test Database (Optional)

For screenshots and testing, create a sample database:

```bash
make test-db        # Using Makefile (recommended)
# or
python3 scripts/create_test_db.py
```

This creates `test_database.db` with sample data (users, products, orders, logs). See `.local-docs/TEST_DATABASE.md` for details (local documentation).

## 🚀 Usage

### Installation as Command

To install dbrowse as a system command:

```bash
# Development mode (recommended for contributors)
make install-package
# or
pip install -e .

# Production mode
pip install .
```

After installation, you can run:
```bash
dbrowse    # Main command
dbrowser   # Alias (convenience)
```

### Quick Start

**Option 1: Install as command (recommended)**
```bash
make install-package  # Install in development mode
dbrowse               # Run the application
# or
dbrowser              # Alias command
```

**Option 2: Install via Homebrew**
```bash
# From local formula
brew install --build-from-source ./Formula/dbrowse.rb

# Or from tap (when available)
brew tap yourusername/dbrowse
brew install dbrowse
```

**Option 3: Run directly**
```bash
make run           # Using Makefile
# or
python main.py
```

### Updating

dbrowse automatically checks for updates on startup. To update manually:

```bash
dbrowse --update   # Update to latest version
```

The update command automatically detects your installation method (pip or Homebrew) and updates accordingly.

The application will open a full-screen TUI with three columns:
- **Left column**: List of saved database connections
- **Middle column**: Tables/collections in the selected database
- **Right column**: Data from the selected table

### Example Workflow

1. **Start the application**: `python main.py`
2. **Add a connection**: Click `ADD` button → Enter database details
3. **Select a database**: Click on a connection in the left column
4. **Browse tables**: Tables appear in the middle column, sorted by size
5. **View data**: Click on a table to see its data in the right column
6. **Filter data**: Enter WHERE clause (e.g., `id > 100`) and press Enter
7. **Sort data**: Enter ORDER BY clause (e.g., `name ASC`) and press Enter
8. **Export data**: Click `[ CSV ]` or `[ JSON ]` buttons to export
9. **Copy values**: Click on any cell to copy its value to clipboard

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

## Development

### Using Makefile

The project includes a Makefile with useful commands:

```bash
make help          # Show all available commands
make setup         # Set up development environment
make run           # Run the application
make test-db       # Create test database
make format        # Format code with black
make lint          # Lint code with flake8
make check         # Run all checks (format, lint, type-check)
make clean         # Clean up generated files
```

See `make help` for all available commands.

## Project Structure

```
dbrowse/
├── main.py          # Application entry point
├── database.py      # Database adapters and connection management
├── ui.py            # TUI components and rendering
├── utils.py         # Utility functions
├── requirements.txt # Python dependencies
├── Makefile         # Development commands
├── scripts/         # Utility scripts
│   └── create_test_db.py
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

## 🙏 Acknowledgments

- Built with [prompt_toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) - amazing TUI framework
- Inspired by [lazydocker](https://github.com/jesseduffield/lazydocker) and [lazygit](https://github.com/jesseduffield/lazygit) - amazing TUI tools
- Inspired by pgAdmin and other database management tools

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Guide

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## 📝 Examples

### Filtering Data

```sql
-- In WHERE field:
id > 100 AND status = 'active'
name LIKE '%test%'
created_at > '2024-01-01'
```

### Sorting Data

```sql
-- In ORDER BY field:
id DESC
name ASC, created_at DESC
```

### MongoDB Filtering

```json
{"age": {"$gt": 18}}
{"status": "active", "verified": true}
{"tags": {"$in": ["python", "database"]}}
```

## 🐛 Support

For issues, feature requests, or questions:
- 📧 Open an [issue](https://github.com/4nzor/dbrowse/issues) on GitHub
- 💬 Start a [discussion](https://github.com/4nzor/dbrowse/discussions)

## ⭐ Show Your Support

If you find dbrowse useful, please consider giving it a star ⭐ on GitHub!

## 📦 Installation Methods

### Homebrew (macOS)

```bash
# From local formula
brew install --build-from-source ./Formula/dbrowse.rb

# Or from tap (when available)
brew tap yourusername/dbrowse
brew install dbrowse
```

### pip

```bash
# Development installation
pip install -e .

# Production installation
pip install git+https://github.com/4nzor/dbrowse.git
```

### From Source

```bash
git clone https://github.com/4nzor/dbrowse.git
cd dbrowse
make quickstart
make install-package
```

## 🔄 Updating

dbrowse automatically checks for updates on startup. You'll see a notification in the status panel if a new version is available.

To update manually:

```bash
dbrowse --update   # Updates via pip or Homebrew (auto-detected)
```

For detailed release instructions, see the local documentation in `.local-docs/` directory (not in git).
