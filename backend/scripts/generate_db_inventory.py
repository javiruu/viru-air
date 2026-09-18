import os
import sys
import glob
import re
import json
import hashlib
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
repo_root = backend_dir.parent
sys.path.insert(0, str(backend_dir))

import app.infrastructure.db.models as models
from app.infrastructure.db.session import Base
from sqlalchemy.dialects import postgresql

inventory = {
    "generated_at": "2026-09-12T22:30:00Z",
    "authority": "01_DATABASE_SINGLE_AUTHORITY.md Phase A",
    "db_connection_and_sqlite_references": [],
    "alembic_references": [],
    "alembic_revisions": [],
    "supabase_migration_files": [],
    "sqlalchemy_models_tables": {},
    "database_extensions_triggers_functions": []
}

target_exts = ('.py', '.ts', '.tsx', '.json', '.env', '.example', '.yml', '.yaml', '.ps1', '.sh', '.ini')
for root, dirs, files in os.walk(repo_root):
    norm_root = root.replace(os.sep, '/')
    if any(p in norm_root for p in ['node_modules', '.git', '.venv', 'alembic/versions', 'viru-completion', 'viru-final-decommission', 'docs/archive/migration-era', '.agents']):
        continue
    for f in files:
        if f.endswith(target_exts):
            p = Path(root) / f
            rel_p = str(p.relative_to(repo_root)).replace(os.sep, '/')
            try:
                text_content = p.read_text(encoding='utf-8', errors='ignore')
                matches = []
                for term in ['DB_URL', 'DATABASE_URL', 'sqlite://', 'viru.db', 'create_engine', 'sessionmaker']:
                    found = len(re.findall(re.escape(term), text_content, re.IGNORECASE))
                    if found:
                        matches.append({"term": term, "count": found})
                if matches:
                    inventory["db_connection_and_sqlite_references"].append({
                        "file": rel_p,
                        "matches": matches
                    })
            except Exception:
                pass

for root, dirs, files in os.walk(repo_root):
    norm_root = root.replace(os.sep, '/')
    if any(p in norm_root for p in ['node_modules', '.git', '.venv', 'alembic/versions', 'viru-completion', 'viru-final-decommission', 'docs/archive/migration-era', '.agents']):
        continue
    for f in files:
        if f.endswith(target_exts):
            p = Path(root) / f
            rel_p = str(p.relative_to(repo_root)).replace(os.sep, '/')
            try:
                text_content = p.read_text(encoding='utf-8', errors='ignore')
                found = len(re.findall(r'alembic', text_content, re.IGNORECASE))
                if found:
                    inventory["alembic_references"].append({
                        "file": rel_p,
                        "count": found
                    })
            except Exception:
                pass

rev_files = sorted(glob.glob(str(backend_dir / "alembic" / "versions" / "*.py")))
for rf in rev_files:
    content = Path(rf).read_text(encoding='utf-8', errors='ignore')
    rev_match = re.search(r"^revision\s*[:=]\s*['\"]([^'\"]+)['\"]", content, re.M)
    down_match = re.search(r"^down_revision\s*[:=]\s*['\"]?([^'\"\n,]+)['\"]?", content, re.M)
    branch_match = re.search(r"^branch_labels\s*[:=]\s*(.+)$", content, re.M)
    depends_match = re.search(r"^depends_on\s*[:=]\s*(.+)$", content, re.M)
    
    rev_id = rev_match.group(1) if rev_match else "unknown"
    down_rev = down_match.group(1) if down_match else None
    if down_rev in ("None", ""):
        down_rev = None
        
    inventory["alembic_revisions"].append({
        "file": Path(rf).name,
        "revision": rev_id,
        "down_revision": down_rev,
        "branch_labels": branch_match.group(1).strip() if branch_match else None,
        "depends_on": depends_match.group(1).strip() if depends_match else None
    })

sb_dir = repo_root / "supabase" / "migrations"
if sb_dir.exists():
    for mf in sorted(sb_dir.glob("*.sql")):
        content_b = mf.read_bytes()
        sha256 = hashlib.sha256(content_b).hexdigest()
        inventory["supabase_migration_files"].append({
            "name": mf.name,
            "bytes": len(content_b),
            "sha256": sha256
        })

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
    unique_constraints = []
    for uq in table.constraints:
        if hasattr(uq, "columns") and uq.__class__.__name__ == "UniqueConstraint":
            unique_constraints.append({
                "name": uq.name,
                "columns": [c.name for c in uq.columns]
            })
    indexes = []
    for idx in table.indexes:
        indexes.append({
            "name": idx.name,
            "unique": bool(idx.unique),
            "columns": [c.name for c in idx.columns]
        })
    
    inventory["sqlalchemy_models_tables"][table.name] = {
        "columns_count": len(cols),
        "columns": cols,
        "primary_key": pks,
        "foreign_keys": fks,
        "unique_constraints": unique_constraints,
        "indexes": indexes
    }

for mf in inventory["supabase_migration_files"]:
    sql = (sb_dir / mf["name"]).read_text(encoding='utf-8', errors='ignore')
    ext_matches = re.findall(r'CREATE EXTENSION IF NOT EXISTS ["\']?([a-zA-Z0-9_-]+)["\']?', sql, re.I)
    for ext in set(ext_matches):
        inventory["database_extensions_triggers_functions"].append({
            "kind": "extension",
            "name": ext,
            "defined_in": mf["name"]
        })
    func_matches = re.findall(r'CREATE (?:OR REPLACE )?FUNCTION ["\']?([a-zA-Z0-9_.]+)["\']?', sql, re.I)
    for fn in set(func_matches):
        inventory["database_extensions_triggers_functions"].append({
            "kind": "function",
            "name": fn,
            "defined_in": mf["name"]
        })
    trig_matches = re.findall(r'CREATE TRIGGER ["\']?([a-zA-Z0-9_.]+)["\']?', sql, re.I)
    for tr in set(trig_matches):
        inventory["database_extensions_triggers_functions"].append({
            "kind": "trigger",
            "name": tr,
            "defined_in": mf["name"]
        })

out_dir = repo_root / "docs" / "migration" / "final-decommission-v3"
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / "database-inventory.json"
out_file.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
print(f"DATABASE INVENTORY GENERATED: {len(inventory['sqlalchemy_models_tables'])} tables, {len(inventory['alembic_revisions'])} alembic revisions")
