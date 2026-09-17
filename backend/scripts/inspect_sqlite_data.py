import sqlite3
import json
from pathlib import Path

db_path = Path(__file__).resolve().parents[2] / "viru.db"
if not db_path.exists():
    print(json.dumps({"error": "viru.db not found"}))
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]

table_counts = {}
for t in tables:
    cursor.execute(f"SELECT COUNT(*) FROM [{t}];")
    count = cursor.fetchone()[0]
    if count > 0:
        table_counts[t] = count

print(json.dumps({
    "total_tables_in_sqlite": len(tables),
    "non_empty_tables_count": len(table_counts),
    "counts": table_counts
}, indent=2))
