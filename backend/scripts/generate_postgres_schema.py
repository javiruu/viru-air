import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable, CreateIndex
import app.infrastructure.db.models as models
from app.infrastructure.db.session import Base

output_lines = [
    "-- Canonical Baseline Schema for Supabase PostgreSQL",
    "-- Generated from SQLAlchemy metadata (Base.metadata)",
    "-- Tables: %d" % len(Base.metadata.sorted_tables),
    "",
    "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";",
    "CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";",
    "",
]

for table in Base.metadata.sorted_tables:
    create_table_stmt = CreateTable(table).compile(dialect=postgresql.dialect())
    clean_stmt = str(create_table_stmt).strip()
    output_lines.append(f"{clean_stmt};")
    output_lines.append("")
    
    for index in table.indexes:
        idx_stmt = CreateIndex(index).compile(dialect=postgresql.dialect())
        output_lines.append(f"{str(idx_stmt).strip()};")
    output_lines.append("")

schema_sql = "\n".join(output_lines)
output_path = backend_dir.parent / "supabase" / "migrations" / "20260912000002_canonical_baseline_schema.sql"
output_path.write_text(schema_sql, encoding="utf-8")
print(f"Wrote {len(Base.metadata.sorted_tables)} tables to {output_path}")
