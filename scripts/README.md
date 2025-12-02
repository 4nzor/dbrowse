# Scripts

This directory contains utility scripts for dbrowse development and testing.

## create_test_db.py

Creates a test SQLite database with sample data for screenshots and testing.

### Usage

```bash
python3 scripts/create_test_db.py
```

### What it creates

- **test_database.db** - SQLite database file in the project root
- **Tables:**
  - `users` - 10 sample users with various statuses
  - `products` - 10 sample products in different categories
  - `orders` - 50 sample orders with different statuses
  - `logs` - 200 log entries for large dataset demo

### Features demonstrated

- Different data types (text, numbers, dates, booleans)
- Foreign key relationships
- Indexes on various columns
- Various status values for filtering
- Date ranges for sorting/filtering
- Large dataset (logs table)

### Using in dbrowse

1. Run the script to create the database
2. In dbrowse, add a new connection:
   - Database type: **SQLite**
   - Database path: `/path/to/dbrowse/test_database.db`
   - Or use: `sqlite:///path/to/dbrowse/test_database.db`

### Example queries for screenshots

**WHERE examples:**
- `status = 'active'`
- `age > 25`
- `created_at > '2024-11-01'`
- `price < 100`

**ORDER BY examples:**
- `id DESC`
- `name ASC`
- `created_at DESC, price ASC`

### Cleanup

To remove the test database:
```bash
rm test_database.db
```

