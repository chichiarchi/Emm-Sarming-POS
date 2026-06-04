import sqlite3
import hashlib
import os
import sys

# Determine the correct path for the database file
if getattr(sys, 'frozen', False):
    # If running as a bundled executable, use the folder containing the .exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # If running in development, use the current directory
    BASE_DIR = os.path.abspath(".")

DB_NAME = os.path.join(BASE_DIR, "emma_sarming_store.db")

def get_connection():
    # Added timeout to prevent "Database is locked" errors in the long run
    return sqlite3.connect(DB_NAME, timeout=20)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'staff'))
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY, -- Using barcode as ID
            name TEXT NOT NULL,
            price REAL NOT NULL,
            wholesale_price REAL DEFAULT 0.0,
            category TEXT
        )
    """)
    
    # Migration for existing databases that don't have wholesale_price column yet
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN wholesale_price REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass

    # Migration: add cost column to products
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN cost REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass

    # Create Product Bundles Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_bundles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            bundle_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            wholesale_price REAL DEFAULT 0.0,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    """)
    
    # Migration for existing databases that don't have wholesale_price column in product_bundles yet
    try:
        cursor.execute("ALTER TABLE product_bundles ADD COLUMN wholesale_price REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass

    # Migration: add cost column to product_bundles
    try:
        cursor.execute("ALTER TABLE product_bundles ADD COLUMN cost REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass
    
    # Create Customers Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            phone TEXT
        )
    """)
    
    # Create Sales Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_amount REAL NOT NULL,
            amount_paid REAL NOT NULL,
            balance_due REAL NOT NULL,
            customer_id INTEGER,
            voided INTEGER DEFAULT 0, -- 0 = Active, 1 = Voided
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )
    """)

    # Create Sale Items Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY(sale_id) REFERENCES sales(id)
        )
    """)

    # Create Debtors Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS debtors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            sale_id INTEGER NOT NULL,
            balance_amount REAL NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(sale_id) REFERENCES sales(id)
        )
    """)
    
    # Create Audit Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            details TEXT,
            user_id TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create Settings Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Create Payment Notes Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payment_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            recipient TEXT NOT NULL,
            purpose TEXT,
            timestamp DATETIME DEFAULT (datetime('now', '+8 hours'))
        )
    """)

    # Create Parked Sales Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parked_sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT, -- Customer Reference
            cart_data TEXT NOT NULL, -- JSON serialized list
            total REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create Sale Payments Table (for split tenders)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sale_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            payment_method TEXT NOT NULL,
            amount REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(sale_id) REFERENCES sales(id)
        )
    """)
    
    # Add an initial admin user if the table is empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        password_hash, salt = hash_password('admin')
        cursor.execute(
            "INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)",
            ('admin', password_hash, salt, 'admin')
        )

    conn.commit()
    conn.close()
    
    # Run data retention policy to keep only 90 days of logs
    enforce_data_retention_policy()

def enforce_data_retention_policy():
    """
    Implements the '90-day Rolling Window' policy:
    1. Purge: Deletes audit logs older than 90 days.
    2. Compaction: Runs VACUUM to reclaim disk space.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Step 1: Identify and remove records from Day 91 and older
        cursor.execute("DELETE FROM audit_logs WHERE timestamp < date('now', '-90 days')")
        deleted_count = cursor.rowcount
        conn.commit()
        
        # Step 2: Perform Database Compaction to reclaim space on the hard drive
        cursor.execute("VACUUM")
        
    except sqlite3.Error as e:
        print(f"Data Retention Policy Error: {e}")
    finally:
        conn.close()

def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16)
    else:
        if isinstance(salt, str):
            salt = bytes.fromhex(salt)
            
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    return key.hex(), salt.hex()

def create_user(username, password, role):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        password_hash, salt = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)",
            (username, password_hash, salt, role)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_login(username, password):
    """
    Returns (user_id, role) if successfully verified, else None
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash, salt, role FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return None
        
    user_id, stored_hash, stored_salt, role = row
    
    # Verify the password
    computed_hash, _ = hash_password(password, stored_salt)
    
    if computed_hash == stored_hash:
        return user_id, role
    return None

def update_user_password(username, new_password):
    conn = get_connection()
    cursor = conn.cursor()
    password_hash, salt = hash_password(new_password)
    cursor.execute(
        "UPDATE users SET password_hash = ?, salt = ? WHERE username = ?",
        (password_hash, salt, username)
    )
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

def get_user_by_username(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row

def log_action(action, details=None, user_id="system"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO audit_logs (action, details, user_id, timestamp) VALUES (?, ?, ?, datetime('now', '+8 hours'))",
        (action, details, user_id)
    )
    conn.commit()
    conn.close()

def get_setting(key, default=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return default

def set_setting(key, value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def is_stock_management_disabled():
    return True

def add_payment_note(amount, recipient, purpose, timestamp=None):
    conn = get_connection()
    cursor = conn.cursor()
    if timestamp:
        cursor.execute("""
            INSERT INTO payment_notes (amount, recipient, purpose, timestamp)
            VALUES (?, ?, ?, ?)
        """, (amount, recipient, purpose, timestamp))
    else:
        cursor.execute("""
            INSERT INTO payment_notes (amount, recipient, purpose)
            VALUES (?, ?, ?)
        """, (amount, recipient, purpose))
    conn.commit()
    conn.close()

def get_payment_notes(date_from=None, date_to=None):
    conn = get_connection()
    cursor = conn.cursor()
    if date_from and date_to:
        cursor.execute("""
            SELECT id, amount, recipient, purpose, timestamp
            FROM payment_notes
            WHERE DATE(timestamp) BETWEEN ? AND ?
            ORDER BY timestamp DESC
        """, (date_from, date_to))
    else:
        cursor.execute("""
            SELECT id, amount, recipient, purpose, timestamp
            FROM payment_notes
            ORDER BY timestamp DESC
        """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_payment_note(note_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM payment_notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
