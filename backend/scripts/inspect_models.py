import sys
import json
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.infrastructure.db.session import Base

tables_info = {}
for name, table in Base.metadata.tables.items():
    cols = []
    has_user_id = False
    user_fk = False
    fks = []
    for c in table.columns:
        if "user" in c.name:
            has_user_id = True
        for fk in c.foreign_keys:
            fk_target = str(fk.target_fullname)
            fks.append(f"{c.name} -> {fk_target}")
            if "user" in fk_target:
                user_fk = True
        cols.append(c.name)
    tables_info[name] = {
        "columns_count": len(cols),
        "has_user_id": has_user_id,
        "user_fk": user_fk,
        "foreign_keys": fks,
        "columns": cols
    }

print(json.dumps({
    "total_tables": len(tables_info),
    "tables": tables_info
}, indent=2))
