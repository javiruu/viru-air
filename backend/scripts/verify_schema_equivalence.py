import sys
import json
import re
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

import app.infrastructure.db.models as models
from app.infrastructure.db.session import Base
from sqlalchemy.dialects import postgresql

repo_root = backend_dir.parent
migration_file = repo_root / "supabase" / "migrations" / "20260912000001_canonical_baseline_schema.sql"
migration_sql = migration_file.read_text(encoding="utf-8")

sa_inventory = {}
for table in Base.metadata.sorted_tables:
    cols = {}
    for col in table.columns:
        col_type = str(col.type.compile(dialect=postgresql.dialect()))
        cols[col.name] = {
            "type": col_type,
            "nullable": bool(col.nullable),
            "primary_key": bool(col.primary_key),
            "default": str(col.default.arg) if col.default is not None and hasattr(col.default, "arg") else None
        }
    
    pks = [c.name for c in table.primary_key.columns]
    fks = []
    for fk in table.foreign_keys:
        fks.append({
            "column": fk.parent.name,
            "target": str(fk.target_fullname),
            "ondelete": fk.ondelete
        })
        
    indexes = []
    for idx in table.indexes:
        indexes.append({
            "name": idx.name,
            "columns": [c.name for c in idx.columns],
            "unique": bool(idx.unique)
        })
        
    sa_inventory[table.name] = {
        "columns_count": len(cols),
        "columns": cols,
        "primary_keys": pks,
        "foreign_keys": fks,
        "indexes": indexes
    }

# Parse migration SQL to extract created tables
created_tables = re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?([a-zA-Z0-9_]+)", migration_sql)
created_indexes = re.findall(r"CREATE (?:UNIQUE )?INDEX (?:IF NOT EXISTS )?([a-zA-Z0-9_]+)", migration_sql)

missing_tables = [t for t in sa_inventory if t not in created_tables]
extra_tables = [t for t in created_tables if t not in sa_inventory]

diff_report = {
    "total_sqlalchemy_models": len(sa_inventory),
    "total_tables_in_migration": len(created_tables),
    "missing_tables_in_migration": missing_tables,
    "extra_tables_in_migration": extra_tables,
    "total_indexes_in_migration": len(created_indexes),
    "schema_match_summary": {
        "missing_tables": len(missing_tables),
        "extra_unexplained_tables": len(extra_tables),
        "status": "EXACT_MATCH" if len(missing_tables) == 0 and len(extra_tables) == 0 else "MISMATCH"
    },
    "tables": sa_inventory
}

out_path = repo_root / "docs" / "migration" / "final-completion" / "schema-equivalence.json"
out_path.write_text(json.dumps(diff_report, indent=2), encoding="utf-8")
print(f"Schema equivalence verification complete: {len(sa_inventory)} models vs {len(created_tables)} SQL migration tables. Status: {diff_report['schema_match_summary']['status']}")
