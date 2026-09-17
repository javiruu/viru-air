import json
from app.main import app

def audit():
    spec = app.openapi()
    paths = spec.get('paths', {})
    
    routes_info = []
    for r in app.routes:
        path = getattr(r, 'path', str(r))
        methods = getattr(r, 'methods', set())
        include_in_schema = getattr(r, 'include_in_schema', True)
        routes_info.append({
            'path': path,
            'methods': sorted(list(methods)) if methods else [],
            'name': getattr(r, 'name', ''),
            'type': type(r).__name__,
            'include_in_schema': include_in_schema
        })

    print(f'Total app.routes: {len(app.routes)}')
    print(f'Total OpenAPI paths: {len(paths)}')
    
    path_counts = {}
    for r in routes_info:
        p = r['path']
        path_counts[p] = path_counts.get(p, 0) + 1
    
    duplicates = {p: c for p, c in path_counts.items() if c > 1}
    print(f'Paths defined multiple times in app.routes: {len(duplicates)}')
    for p, c in sorted(duplicates.items()):
        print(f'  {p}: {c} times')
        
    routes_not_in_schema = [r for r in routes_info if not r['include_in_schema'] or r['path'] not in paths]
    print(f'Routes in app not in openapi.json paths: {len(routes_not_in_schema)}')
    for r in routes_not_in_schema:
        print(f"  {r['path']} {r['methods']} {r['name']} ({r['type']}) include_in_schema={r['include_in_schema']}")

if __name__ == '__main__':
    audit()
