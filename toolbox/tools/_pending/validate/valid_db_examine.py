import sqlite3

try:
    # Connect to the database
    conn = sqlite3.connect('qieos.db')
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("Tables in qieos.db:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # For each table, show structure and sample data
    for table in tables:
        table_name = table[0]
        print(f"\n=== {table_name} ===")
        
        # Get table structure
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        print("Columns:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        # Get sample data
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")
        rows = cursor.fetchall()
        print(f"Sample data ({len(rows)} rows):")
        for row in rows:
            print(f"  {row}")
    
    conn.close()
    print("\nDatabase examination complete!")
    
except Exception as e:
    print(f"Error: {e}")
