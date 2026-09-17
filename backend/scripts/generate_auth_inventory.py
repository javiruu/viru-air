import os
import re
import json
from pathlib import Path

os.environ['APP_ENV'] = 'test'
os.environ.setdefault('TEST_DB_URL', 'sqlite:///:memory:')

repo_root = Path(__file__).resolve().parents[2]
backend_dir = repo_root / 'backend'
frontend_dir = repo_root / 'frontend'

inventory = {
    'authority': '02_AUTH_SINGLE_AUTHORITY.md Phase A',
    'generated_at': '2026-09-12T23:15:00Z',
    'pbkdf2_occurrences': [],
    'jwt_issuer_occurrences': [],
    'refresh_token_occurrences': [],
    'viru_token_occurrences': [],
    'auth_endpoints': [],
    'supabase_helpers': [],
    'user_scoped_tables': []
}

for root, _, files in os.walk(backend_dir / 'app'):
    for f in files:
        if f.endswith('.py'):
            p = Path(root) / f
            txt = p.read_text(encoding='utf-8', errors='ignore')
            if re.search(r'pbkdf2|pwd_context|cryptcontext', txt, re.I):
                inventory['pbkdf2_occurrences'].append(str(p.relative_to(repo_root)).replace('\\', '/'))

for root, _, files in os.walk(backend_dir / 'app'):
    for f in files:
        if f.endswith('.py'):
            p = Path(root) / f
            txt = p.read_text(encoding='utf-8', errors='ignore')
            if 'create_access_token' in txt or 'create_refresh_token' in txt:
                inventory['jwt_issuer_occurrences'].append(str(p.relative_to(repo_root)).replace('\\', '/'))

for root, _, files in os.walk(backend_dir / 'app'):
    for f in files:
        if f.endswith('.py'):
            p = Path(root) / f
            txt = p.read_text(encoding='utf-8', errors='ignore')
            if re.search(r'refresh_token|refreshtoken', txt, re.I):
                inventory['refresh_token_occurrences'].append(str(p.relative_to(repo_root)).replace('\\', '/'))

for root, _, files in os.walk(frontend_dir / 'src'):
    for f in files:
        if f.endswith(('.ts', '.tsx', '.js', '.jsx')):
            p = Path(root) / f
            txt = p.read_text(encoding='utf-8', errors='ignore')
            if 'viru_token' in txt:
                inventory['viru_token_occurrences'].append(str(p.relative_to(repo_root)).replace('\\', '/'))

auth_py = backend_dir / 'app' / 'api' / 'v1' / 'auth.py'
if auth_py.exists():
    txt = auth_py.read_text(encoding='utf-8', errors='ignore')
    routes = re.findall(r'@router\.(post|get|put|delete)\(["\']([^"\']+)', txt)
    inventory['auth_endpoints'] = [{'method': m.upper(), 'path': p} for m, p in routes]

sb_client = frontend_dir / 'src' / 'lib' / 'supabase' / 'client.ts'
sb_server = frontend_dir / 'src' / 'lib' / 'supabase' / 'server.ts'
if sb_client.exists():
    inventory['supabase_helpers'].append('frontend/src/lib/supabase/client.ts')
if sb_server.exists():
    inventory['supabase_helpers'].append('frontend/src/lib/supabase/server.ts')

import sys
sys.path.insert(0, str(backend_dir))
from app.infrastructure.db.models import Base
for table in Base.metadata.sorted_tables:
    has_user_col = any('user' in c.name for c in table.columns)
    has_user_fk = any('user' in str(fk.target_fullname) for fk in table.foreign_keys)
    if has_user_col or has_user_fk:
        inventory['user_scoped_tables'].append(table.name)

out_dir = repo_root / 'docs' / 'migration' / 'final-decommission-v3'
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / 'auth-legacy-inventory.json'
out_file.write_text(json.dumps(inventory, indent=2), encoding='utf-8')
print(f'AUTH INVENTORY GENERATED: {len(inventory["user_scoped_tables"])} user-scoped tables')
