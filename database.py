# File: database.py
import sqlite3
import os  # Import os module

# Use a more robust way to define the database path
# This places the database in the same directory as the script
script_dir = os.path.dirname(os.path.abspath(__file__))
DATABASE_NAME = os.path.join(script_dir, "skus.db")


def init_db():
    """Initializes the database and creates the skus table if it doesn't exist."""
    conn = None
    try:
        # Connect will create the file if it doesn't exist in the specified path
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        # Create table with a unique constraint to avoid duplicate SKUs
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS skus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku_name TEXT NOT NULL UNIQUE
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


def add_sku(sku_name):
    """Adds a new SKU to the database."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO skus (sku_name) VALUES (?)", (sku_name,))
        conn.commit()
        print(f"SKU '{sku_name}' added successfully.")
        return True
    except sqlite3.IntegrityError:
        # This error specifically occurs when the UNIQUE constraint is violated
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
    conn = None
    skus = []
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT sku_name FROM skus ORDER BY sku_name COLLATE NOCASE"
        )  # Sort case-insensitively
        rows = cursor.fetchall()
        # Extract the first element (sku_name) from each tuple in the list
        skus = [row[0] for row in rows]
    except sqlite3.Error as e:
        print(f"Database error while retrieving SKUs: {e}")
    finally:
        if conn:
            conn.close()
    return skus


def delete_sku(sku_name):
    """Deletes an SKU from the database."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM skus WHERE sku_name = ?", (sku_name,))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"SKU '{sku_name}' deleted successfully.")
            return True
        else:
            # This might happen if the SKU was deleted by another process or doesn't exist
            print(f"Info: SKU '{sku_name}' not found for deletion.")
            return False
    except sqlite3.Error as e:
        print(f"Database error while deleting SKU '{sku_name}': {e}")
        return False
    finally:
        if conn:
            conn.close()


def update_sku(old_sku_name, new_sku_name):
    """Updates an existing SKU name in the database."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE skus SET sku_name = ? WHERE sku_name = ?",
            (new_sku_name, old_sku_name),
        )
        conn.commit()
        if cursor.rowcount > 0:
            print(f"SKU '{old_sku_name}' updated to '{new_sku_name}'.")
            return True
        else:
            # This case should ideally not happen if the old_sku_name came from the list
            print(f"Error: SKU '{old_sku_name}' not found during update attempt.")
            return False
    except sqlite3.IntegrityError:
        # UNIQUE constraint failed, meaning new_sku_name likely already exists
        print(f"Error: Cannot update. SKU '{new_sku_name}' may already exist.")
        return False
    except sqlite3.Error as e:
        print(f"Database error while updating SKU: {e}")
        return False
    finally:
        if conn:
            conn.close()


# Initialize the database automatically when this module is imported for the first time
# Or if run directly (though typically it will just be imported)
if __name__ == "__main__":
    print("Running database module directly for initialization check.")
    init_db()
else:
    # Ensure DB exists when imported by main_app.py
    init_db()
