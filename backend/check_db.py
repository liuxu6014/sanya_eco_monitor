import sqlite3
import os

db_path = "sanya_eco.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print("--- Collect Logs ---")
    cursor.execute("SELECT task_name, status, records_count, created_at FROM collect_logs ORDER BY created_at DESC LIMIT 10")
    for row in cursor.fetchall():
        print(row)
    
    print("\n--- Record Counts ---")
    tables = ["insect_records", "spore_records", "weather_records", "soil_records"]
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"{table}: {count}")
    
    conn.close()
else:
    print("Database not found.")
