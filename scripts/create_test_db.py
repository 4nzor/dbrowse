#!/usr/bin/env python3
"""
Script to create a test SQLite database with sample data for screenshots.
This creates a demo database with realistic data for showcasing dbrowse features.
"""

import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path

# Path to test database
TEST_DB_PATH = Path(__file__).parent.parent / "test_database.db"


def create_test_database():
    """Create test database with sample tables and data."""
    
    # Remove existing database if it exists
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
        print(f"Removed existing database: {TEST_DB_PATH}")
    
    # Connect to SQLite (creates file if doesn't exist)
    conn = sqlite3.connect(str(TEST_DB_PATH))
    cursor = conn.cursor()
    
    print("Creating test database...")
    
    # Create users table
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) NOT NULL UNIQUE,
            email VARCHAR(100) NOT NULL,
            full_name VARCHAR(100),
            status VARCHAR(20) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            age INTEGER,
            country VARCHAR(50)
        )
    """)
    
    # Create products table
    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            category VARCHAR(50),
            price DECIMAL(10, 2),
            stock INTEGER DEFAULT 0,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    """)
    
    # Create orders table
    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER DEFAULT 1,
            total_amount DECIMAL(10, 2),
            status VARCHAR(20) DEFAULT 'pending',
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    
    # Create logs table (for large dataset demo)
    cursor.execute("""
        CREATE TABLE logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level VARCHAR(10),
            message TEXT,
            source VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX idx_users_email ON users(email)")
    cursor.execute("CREATE INDEX idx_users_status ON users(status)")
    cursor.execute("CREATE INDEX idx_products_category ON products(category)")
    cursor.execute("CREATE INDEX idx_orders_user_id ON orders(user_id)")
    cursor.execute("CREATE INDEX idx_orders_status ON orders(status)")
    cursor.execute("CREATE INDEX idx_logs_created_at ON logs(created_at)")
    
    print("Tables created!")
    
    # Insert sample users
    print("Inserting users...")
    users_data = [
        ("alice", "alice@example.com", "Alice Johnson", "active", 25, "USA"),
        ("bob", "bob@example.com", "Bob Smith", "active", 30, "UK"),
        ("charlie", "charlie@example.com", "Charlie Brown", "inactive", 28, "Canada"),
        ("diana", "diana@example.com", "Diana Prince", "active", 32, "USA"),
        ("eve", "eve@example.com", "Eve Adams", "active", 27, "Australia"),
        ("frank", "frank@example.com", "Frank Miller", "pending", 35, "Germany"),
        ("grace", "grace@example.com", "Grace Kelly", "active", 29, "France"),
        ("henry", "henry@example.com", "Henry Ford", "active", 40, "USA"),
        ("iris", "iris@example.com", "Iris West", "inactive", 26, "UK"),
        ("jack", "jack@example.com", "Jack Sparrow", "active", 33, "Caribbean"),
    ]
    
    base_time = datetime.now() - timedelta(days=30)
    for i, (username, email, full_name, status, age, country) in enumerate(users_data):
        created_at = base_time + timedelta(days=i*3)
        last_login = created_at + timedelta(days=random.randint(1, 20)) if status == "active" else None
        cursor.execute("""
            INSERT INTO users (username, email, full_name, status, age, country, created_at, last_login)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, email, full_name, status, age, country, created_at, last_login))
    
    # Insert sample products
    print("Inserting products...")
    products_data = [
        ("Laptop Pro 15", "Electronics", 1299.99, 45, "High-performance laptop with 16GB RAM"),
        ("Wireless Mouse", "Electronics", 29.99, 120, "Ergonomic wireless mouse"),
        ("Office Chair", "Furniture", 199.99, 30, "Comfortable office chair"),
        ("Desk Lamp", "Furniture", 49.99, 80, "LED desk lamp with adjustable brightness"),
        ("Python Book", "Books", 39.99, 50, "Learn Python programming"),
        ("Coffee Maker", "Appliances", 89.99, 25, "Automatic coffee maker"),
        ("Headphones", "Electronics", 79.99, 60, "Noise-cancelling headphones"),
        ("Notebook", "Stationery", 9.99, 200, "A5 ruled notebook"),
        ("Pen Set", "Stationery", 19.99, 150, "Premium pen set"),
        ("Monitor 27\"", "Electronics", 299.99, 20, "4K monitor"),
    ]
    
    for name, category, price, stock, description in products_data:
        created_at = base_time + timedelta(days=random.randint(1, 25))
        cursor.execute("""
            INSERT INTO products (name, category, price, stock, description, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, category, price, stock, description, created_at, 1))
    
    # Insert sample orders
    print("Inserting orders...")
    order_statuses = ["pending", "completed", "shipped", "cancelled"]
    for i in range(50):
        user_id = random.randint(1, 10)
        product_id = random.randint(1, 10)
        quantity = random.randint(1, 5)
        
        # Get product price
        cursor.execute("SELECT price FROM products WHERE id = ?", (product_id,))
        price = cursor.fetchone()[0]
        total_amount = price * quantity
        
        status = random.choice(order_statuses)
        order_date = base_time + timedelta(days=random.randint(1, 28))
        
        cursor.execute("""
            INSERT INTO orders (user_id, product_id, quantity, total_amount, status, order_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, product_id, quantity, total_amount, status, order_date))
    
    # Insert sample logs (for large dataset)
    print("Inserting logs...")
    log_levels = ["INFO", "WARNING", "ERROR", "DEBUG"]
    log_sources = ["api", "database", "auth", "payment", "email"]
    log_messages = [
        "User logged in successfully",
        "Database query executed",
        "Payment processed",
        "Email sent",
        "Cache updated",
        "Session expired",
        "File uploaded",
        "API request received",
        "Error occurred",
        "Data synchronized",
    ]
    
    for i in range(200):
        level = random.choice(log_levels)
        message = random.choice(log_messages)
        source = random.choice(log_sources)
        created_at = base_time + timedelta(
            days=random.randint(1, 30),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        cursor.execute("""
            INSERT INTO logs (level, message, source, created_at)
            VALUES (?, ?, ?, ?)
        """, (level, message, source, created_at))
    
    # Commit and close
    conn.commit()
    conn.close()
    
    print(f"\n✅ Test database created successfully!")
    print(f"📁 Location: {TEST_DB_PATH}")
    print(f"\n📊 Database contains:")
    print(f"   - 10 users")
    print(f"   - 10 products")
    print(f"   - 50 orders")
    print(f"   - 200 logs")
    print(f"\n💡 To use in dbrowse:")
    print(f"   1. Add connection: sqlite://{TEST_DB_PATH}")
    print(f"   2. Or use path: {TEST_DB_PATH}")


if __name__ == "__main__":
    create_test_database()

