import os
os.environ.setdefault('APP_ENV', 'test')
os.environ.setdefault('TEST_DB_URL', 'sqlite:///:memory:')
import json
from pathlib import Path
from app.main import app

def export_openapi() -> None:
    spec = app.openapi()
    target_path = Path(__file__).resolve().parents[2] / 'docs' / 'architecture' / 'openapi.json'
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, 'w', encoding='utf-8') as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print(f'Exported OpenAPI spec to {target_path} ({len(spec.get("paths", {}))} paths)')

if __name__ == '__main__':
    export_openapi()
