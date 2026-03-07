"""
I made some changes to the database scheme by adding projects, and wanted to keep all my old data, so...
"""


import sqlite3

SOURCE_DB = 'journal - Copy.db'
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
    Applies COALESCE logic for specific columns (like 'entries.project') 
    to handle NOT NULL constraints.
    """
    print(f"Connecting to target database: {target_db_path}")
    
    target_conn = sqlite3.connect(target_db_path)
    target_cursor = target_conn.cursor()

    # 1. Attach the source database
    target_cursor.execute(f"ATTACH DATABASE '{source_db_path}' AS {ATTACH_ALIAS}")

    # Define the core tables we want to merge
    tables_to_merge = ['entries', 'todos', 'projects', 'recurring_todos'] 
    
    print(f"Tables to merge: {tables_to_merge}")
    
    # 2. Iterate through each table, compare schemas, and insert
    for table_name in tables_to_merge:
        print(f"\nProcessing table: {table_name}")
        
        # Get column names for the source and target databases
        source_cols = get_table_columns(target_cursor, ATTACH_ALIAS, table_name)
        target_cols = get_table_columns(target_cursor, None, table_name) # None for the main attached DB
        
        # Find the columns that exist in *both* databases
        common_cols = source_cols.intersection(target_cols)
        
        if not common_cols:
            print(f"  WARNING: No common columns found for {table_name}. Skipping table.")
            continue
            
        common_cols_list = sorted(list(common_cols))
        
        columns_to_insert_str = ', '.join(f'"{c}"' for c in common_cols_list)
        
        columns_to_select_list = []
        for col in common_cols_list:
            # CHECK: If we are merging the 'entries' table AND the column is 'project'
            if table_name == 'entries' and col == 'project':
                # FIX: Replace NULL project values with an empty string ''
                columns_to_select_list.append(f"COALESCE({ATTACH_ALIAS}.\"{col}\", 'Holder') AS \"{col}\"")
            else:
                # For all other columns/tables, just select the column normally
                columns_to_select_list.append(f"{ATTACH_ALIAS}.\"{col}\"")

        columns_to_select_str = ', '.join(columns_to_select_list)
        # ---------------------------------------------

        # Construct the safe INSERT query
        insert_query = f"""
            INSERT OR REPLACE INTO "{table_name}" ({columns_to_insert_str}) 
            SELECT {columns_to_select_str} 
            FROM {ATTACH_ALIAS}."{table_name}"
        """
        
        try:
            target_cursor.execute(insert_query)
            print(f"  SUCCESS: Merged data into {table_name} using common columns: {', '.join(common_cols_list)}")
        except sqlite3.Error as e:
            print(f"  *** ERROR merging {table_name}: {e} ***")
            print("  Rolling back changes for this table.")
            target_conn.rollback() 

    # Commit changes and clean up
    target_conn.commit()
    target_cursor.execute(f"DETACH DATABASE {ATTACH_ALIAS}")
    target_conn.close()
    
    print("\nSchema-aware merge process complete.")

if __name__ == '__main__':
    # Ensure you are pointing to the correct databases
    merge_sqlite_with_schema_check(SOURCE_DB, TARGET_DB)