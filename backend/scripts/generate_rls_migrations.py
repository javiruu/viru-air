import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

import app.infrastructure.db.models as models
from app.infrastructure.db.session import Base

user_tables = []
for name, table in Base.metadata.tables.items():
    cols = [c.name for c in table.columns]
    if "user_id" in cols or "recipient_user_id" in cols:
        user_col = "recipient_user_id" if "recipient_user_id" in cols else "user_id"
        user_tables.append((name, user_col))

sql_lines = [
    "-- Enable Row Level Security (RLS) on all user-scoped tables",
    "-- Policy: Authenticated users can only access their own data via auth.uid()",
    "-- Backend services / workers using service_role have full access",
    ""
]

for table_name, user_col in sorted(user_tables):
    sql_lines.append(f"ALTER TABLE public.{table_name} ENABLE ROW LEVEL SECURITY;")
    sql_lines.append(f"DROP POLICY IF EXISTS \"Users own {table_name}\" ON public.{table_name};")
    sql_lines.append(f"CREATE POLICY \"Users own {table_name}\" ON public.{table_name}")
    sql_lines.append(f"    FOR ALL TO authenticated")
    sql_lines.append(f"    USING ((auth.uid())::text = {user_col}::text)")
    sql_lines.append(f"    WITH CHECK ((auth.uid())::text = {user_col}::text);")
    sql_lines.append("")

rls_sql = "\n".join(sql_lines)
output_path = backend_dir.parent / "supabase" / "migrations" / "20260912000003_enable_user_rls_policies.sql"
output_path.write_text(rls_sql, encoding="utf-8")
print(f"Generated RLS policies for {len(user_tables)} tables in {output_path}")
