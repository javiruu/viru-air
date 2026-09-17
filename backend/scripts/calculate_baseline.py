import os, glob, re, json

results = {}

# 1. Alembic revisions
alembic_revs = len(glob.glob('backend/alembic/versions/*.py'))
results["alembic_revisions"] = alembic_revs

# 2. Alembic runtime/deploy refs
alembic_files = []
for root, dirs, files in os.walk('.'):
    norm_root = root.replace('\\', '/')
    if any(p in norm_root for p in ['node_modules', '.git', '.venv', 'alembic/versions', 'viru-completion', 'viru-final-decommission', 'docs/migration', '.agents']):
        continue
    for f in files:
        if f.endswith(('.py', '.ps1', '.sh', '.yml', '.yaml', '.bat', '.json', '.toml', '.ini', '.ts', '.tsx')):
            p = os.path.join(root, f)
            try:
                content = open(p, encoding='utf-8', errors='ignore').read()
                if 'alembic' in content.lower():
                    matches = len(re.findall(r'alembic', content, re.IGNORECASE))
                    alembic_files.append((p.replace('\\', '/'), matches))
            except Exception:
                pass
results["alembic_runtime_deploy_refs"] = {
    "total_matches": sum(m for _, m in alembic_files),
    "files_count": len(alembic_files),
    "files": alembic_files
}

# 3. SQLite runtime refs (in backend/app)
sqlite_files = []
for root, dirs, files in os.walk('backend/app'):
    for f in files:
        if f.endswith('.py'):
            p = os.path.join(root, f)
            content = open(p, encoding='utf-8', errors='ignore').read()
            if 'sqlite' in content.lower() or 'viru.db' in content.lower():
                matches = len(re.findall(r'sqlite|viru\.db', content, re.IGNORECASE))
                sqlite_files.append((p.replace('\\', '/'), matches))
results["sqlite_runtime_refs"] = {
    "total_matches": sum(m for _, m in sqlite_files),
    "files_count": len(sqlite_files),
    "files": sqlite_files
}

# 4. PBKDF2 production call sites
pbkdf2_files = []
for root, dirs, files in os.walk('backend/app'):
    for f in files:
        if f.endswith('.py'):
            p = os.path.join(root, f)
            content = open(p, encoding='utf-8', errors='ignore').read()
            if 'pbkdf2' in content.lower() or 'pwd_context' in content.lower() or 'cryptcontext' in content.lower():
                matches = len(re.findall(r'pbkdf2|pwd_context|cryptcontext', content, re.IGNORECASE))
                pbkdf2_files.append((p.replace('\\', '/'), matches))
results["pbkdf2_production_call_sites"] = {
    "total_matches": sum(m for _, m in pbkdf2_files),
    "files_count": len(pbkdf2_files),
    "files": pbkdf2_files
}

# 5. Legacy JWT issuer refs
jwt_files = []
for root, dirs, files in os.walk('backend/app'):
    for f in files:
        if f.endswith('.py'):
            p = os.path.join(root, f)
            content = open(p, encoding='utf-8', errors='ignore').read()
            if 'create_access_token' in content or 'create_refresh_token' in content or 'jwt.encode' in content:
                matches = len(re.findall(r'create_access_token|create_refresh_token|jwt\.encode', content))
                jwt_files.append((p.replace('\\', '/'), matches))
results["legacy_jwt_issuer_refs"] = {
    "total_matches": sum(m for _, m in jwt_files),
    "files_count": len(jwt_files),
    "files": jwt_files
}

# 6. Legacy refresh-token refs
rt_files = []
for root, dirs, files in os.walk('backend/app'):
    for f in files:
        if f.endswith('.py'):
            p = os.path.join(root, f)
            content = open(p, encoding='utf-8', errors='ignore').read()
            if 'refresh_token' in content.lower() or 'refreshtoken' in content:
                matches = len(re.findall(r'refresh_token|refreshtoken', content, re.IGNORECASE))
                rt_files.append((p.replace('\\', '/'), matches))
results["legacy_refresh_token_refs"] = {
    "total_matches": sum(m for _, m in rt_files),
    "files_count": len(rt_files),
    "files": rt_files
}

# 7. viru_token in frontend/src
vt_files = []
for root, dirs, files in os.walk('frontend/src'):
    for f in files:
        if f.endswith(('.ts', '.tsx', '.js', '.jsx')):
            p = os.path.join(root, f)
            content = open(p, encoding='utf-8', errors='ignore').read()
            if 'viru_token' in content:
                matches = len(re.findall(r'viru_token', content))
                vt_files.append((p.replace('\\', '/'), matches))
results["viru_token_frontend_src_refs"] = {
    "total_matches": sum(m for _, m in vt_files),
    "files_count": len(vt_files),
    "files": vt_files
}

# 8. Legacy apiFetch consumers in frontend/src
apifetch_files = []
for root, dirs, files in os.walk('frontend/src'):
    for f in files:
        if f.endswith(('.ts', '.tsx', '.js', '.jsx')):
            p = os.path.join(root, f)
            content = open(p, encoding='utf-8', errors='ignore').read()
            if 'apiFetch' in content:
                apifetch_files.append(p.replace('\\', '/'))
results["legacy_apifetch_consumers"] = {
    "files_count": len(apifetch_files),
    "files": apifetch_files
}

# 9. Native fetch calls in frontend/src
fetch_files = []
for root, dirs, files in os.walk('frontend/src'):
    for f in files:
        if f.endswith(('.ts', '.tsx', '.js', '.jsx')):
            p = os.path.join(root, f)
            content = open(p, encoding='utf-8', errors='ignore').read()
            matches = re.findall(r'\bfetch\s*\(', content)
            if matches:
                fetch_files.append((p.replace('\\', '/'), len(matches)))
results["native_fetch_calls"] = {
    "total_matches": sum(m for _, m in fetch_files),
    "files_count": len(fetch_files),
    "files": fetch_files
}

# 10. useEffect in frontend/src
ue_files = []
for root, dirs, files in os.walk('frontend/src'):
    for f in files:
        if f.endswith(('.ts', '.tsx', '.js', '.jsx')):
            p = os.path.join(root, f)
            content = open(p, encoding='utf-8', errors='ignore').read()
            matches = re.findall(r'\buseEffect\s*\(', content)
            if matches:
                ue_files.append((p.replace('\\', '/'), len(matches)))
results["use_effect_calls"] = {
    "total_matches": sum(m for _, m in ue_files),
    "files_count": len(ue_files),
    "files": ue_files
}

os.makedirs('docs/migration/final-decommission-v3', exist_ok=True)
with open('docs/migration/final-decommission-v3/baseline.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)
print("BASELINE GENERATED SUCCESSFULLY")

