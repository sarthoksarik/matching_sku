# File: database.py
import sqlite3
import os

# Determine database path relative to this file
script_dir = os.path.dirname(os.path.abspath(__file__))
DATABASE_NAME = os.path.join(script_dir, "skus.db")


def get_connection():
    """Establishes and returns a database connection."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None


def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = get_connection()
    if conn is None:
        return
    try:
        cursor = conn.cursor()
        # Create skus table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS skus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku_name TEXT NOT NULL UNIQUE
            )
        """
        )
        # Create settings table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT
            )
        """
        )
        conn.commit()
        print(f"Database initialized/checked at: {DATABASE_NAME}")
    except sqlite3.Error as e:
        print(f"Database error during initialization: {e}")
    finally:
        if conn:
            conn.close()


# --- SKU Functions ---


def add_sku(sku_name):
    """Adds a new SKU to the database."""
    sql = "INSERT INTO skus (sku_name) VALUES (?)"
    conn = get_connection()
    if conn is None:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (sku_name,))
        conn.commit()
        print(f"SKU '{sku_name}' added successfully.")
        return True
    except sqlite3.IntegrityError:
        print(f"Info: SKU '{sku_name}' already exists.")
        return False
    except sqlite3.Error as e:
        print(f"Database error while adding SKU '{sku_name}': {e}")
        return False
    finally:
        if conn:
            conn.close()


def get_all_skus():
    """Retrieves all SKUs from the database, ordered alphabetically."""
    sql = "SELECT sku_name FROM skus ORDER BY sku_name COLLATE NOCASE"
    conn = get_connection()
    skus = []
    if conn is None:
        return skus
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        skus = [row[0] for row in rows]
    except sqlite3.Error as e:
        print(f"Database error while retrieving SKUs: {e}")
    finally:
        if conn:
            conn.close()
    return skus


def delete_sku(sku_name):
    """Deletes an SKU from the database."""
    sql = "DELETE FROM skus WHERE sku_name = ?"
    conn = get_connection()
    if conn is None:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (sku_name,))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"SKU '{sku_name}' deleted successfully.")
            return True
        else:
            print(f"Info: SKU '{sku_name}' not found for deletion.")
            return False  # Return False if not found, though not strictly an error
    except sqlite3.Error as e:
        print(f"Database error while deleting SKU '{sku_name}': {e}")
        return False
    finally:
        if conn:
            conn.close()


def update_sku(old_sku_name, new_sku_name):
    """Updates an existing SKU name in the database."""
    sql = "UPDATE skus SET sku_name = ? WHERE sku_name = ?"
    conn = get_connection()
    if conn is None:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (new_sku_name, old_sku_name))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"SKU '{old_sku_name}' updated to '{new_sku_name}'.")
            return True
        else:
            print(f"Error: SKU '{old_sku_name}' not found during update attempt.")
            return False
    except sqlite3.IntegrityError:
        print(f"Error: Cannot update. SKU '{new_sku_name}' may already exist.")
        return False
    except sqlite3.Error as e:
        print(f"Database error while updating SKU: {e}")
        return False
    finally:
        if conn:
            conn.close()


# --- Settings Functions ---


def save_setting(key, value):
    """Saves a setting (key-value pair) to the database. Replaces if key exists."""
    # Use INSERT OR REPLACE for simplicity
    sql = "INSERT OR REPLACE INTO settings (setting_key, setting_value) VALUES (?, ?)"
    conn = get_connection()
    if conn is None:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (key, value))
        conn.commit()
        print(f"Setting '{key}' saved successfully.")
        return True
    except sqlite3.Error as e:
        print(f"Database error while saving setting '{key}': {e}")
        return False
    finally:
        if conn:
            conn.close()


def load_setting(key, default_value=None):
    """Loads a setting value from the database."""
    sql = "SELECT setting_value FROM settings WHERE setting_key = ?"
    conn = get_connection()
    value = default_value
    if conn is None:
        return value
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (key,))
        row = cursor.fetchone()
        if row:
            value = row[0]
            print(f"Setting '{key}' loaded.")
        else:
            print(f"Setting '{key}' not found, using default.")
    except sqlite3.Error as e:
        print(f"Database error while loading setting '{key}': {e}")
    finally:
        if conn:
            conn.close()
    return value


# Initialize DB when module is loaded
init_db()
