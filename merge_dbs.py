"""
This script will connect to the new database (new.db), attach the source database (journal.db), and then copy all records from every table from the source to the new database.


"""

import sqlite3

SOURCE_DB = 'journal2.db'
TARGET_DB = 'journal.db'
ATTACH_ALIAS = 'source_db'

def get_table_columns(cursor, db_alias, table_name):
    """Fetches a list of column names for a given table in a given database."""
    # PRAGMA table_info is the standard way to get schema info
    if db_alias:
        query = f"PRAGMA {db_alias}.table_info('{table_name}')"
    else:
        query = f"PRAGMA table_info('{table_name}')"
        
    cursor.execute(query)
    # The 'name' column is the second column (index 1) in the table_info results
    return {row[1] for row in cursor.fetchall()}

def merge_sqlite_with_schema_check(source_db_path, target_db_path):
    """
    Copies data from source_db to target_db, mapping only identical columns.
    Assumes tables already exist in the target_db, or will be created/initialized 
    by your Flask app's init_db() function before running this script.
    """
    print(f"Connecting to target database: {target_db_path}")
    
    target_conn = sqlite3.connect(target_db_path)
    target_cursor = target_conn.cursor()

    # 1. Attach the source database
    target_cursor.execute(f"ATTACH DATABASE '{source_db_path}' AS {ATTACH_ALIAS}")

    # 2. Get the list of common tables (important for your app: entries, todos, projects, recurring_todos)
    tables_to_merge = ['entries', 'todos', 'projects', 'recurring_todos'] 
    
    print(f"Tables to merge: {tables_to_merge}")
    
    # 3. Iterate through each table, compare schemas, and insert
    for table_name in tables_to_merge:
        print(f"\nProcessing table: {table_name}")
        
        # Get column names for the source database
        source_cols = get_table_columns(target_cursor, ATTACH_ALIAS, table_name)
        
        # Get column names for the target database
        target_cols = get_table_columns(target_cursor, None, table_name) # None for the main attached DB
        
        # Find the columns that exist in *both* databases
        common_cols = source_cols.intersection(target_cols)
        
        if not common_cols:
            print(f"  WARNING: No common columns found for {table_name}. Skipping table.")
            continue
            
        # Remove the 'id' column if we are using 'INSERT OR IGNORE' and expect 
        # auto-increment IDs to be handled by the target DB.
        # However, for a clean merge, it's often better to include 'id'
        # and use 'INSERT OR REPLACE' or 'INSERT OR IGNORE' based on your needs.
        # We will keep 'id' and use 'INSERT OR REPLACE' to ensure unique IDs are preserved.
        
        common_cols_list = sorted(list(common_cols))
        columns_str = ', '.join(f'"{c}"' for c in common_cols_list) # Quote column names for safety

        # Construct the SQL query
        # INSERT OR REPLACE handles both insertion and overwriting if a primary key (id) matches.
        insert_query = f"""
            INSERT OR REPLACE INTO "{table_name}" ({columns_str}) 
            SELECT {columns_str} 
            FROM {ATTACH_ALIAS}."{table_name}"
        """
        
        try:
            target_cursor.execute(insert_query)
            print(f"  SUCCESS: Merged data into {table_name} using common columns: {', '.join(common_cols_list)}")
        except sqlite3.Error as e:
            print(f"  *** ERROR merging {table_name}: {e} ***")
            print("  This error usually means a data type mismatch or a NOT NULL constraint violation.")
            target_conn.rollback() # Rollback to keep the target DB clean

    # 4. Commit changes and clean up
    target_conn.commit()
    target_cursor.execute(f"DETACH DATABASE {ATTACH_ALIAS}")
    target_conn.close()
    
    print("\nSchema-aware merge process complete.")

if __name__ == '__main__':
    # NOTE: Before running, ensure TARGET_DB has the latest (target) schema 
    # by running your Flask app which calls init_db().
    merge_sqlite_with_schema_check(SOURCE_DB, TARGET_DB)