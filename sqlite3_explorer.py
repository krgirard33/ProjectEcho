import sqlite3

conn = sqlite3.connect('journal.db')
cursor = conn.cursor()

tables = ['entries', 'todos', 'projects']
# Execute the PRAGMA command

for table in tables:
    print(f"\nTable: {table}\n")
    cursor.execute(f"PRAGMA table_info({table})")
    column_info = cursor.fetchall()
    print("Column Headers:")
    for col in column_info:
        print(col[1])  # The result columns are: (cid, name, type, notnull, dflt_value, pk)
        
conn.close()
