from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def _literal_value(node: ast.expr) -> str | list[str] | None:
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) or node.value is None else None
    if isinstance(node, ast.List | ast.Tuple):
        values: list[str] = []
        for element in node.elts:
            value = _literal_value(element)
            if not isinstance(value, str):
                return None
            values.append(value)
        return values
    return None


def _extract_identifier(module: ast.Module, name: str) -> str | list[str] | None:
    for statement in module.body:
        target_names: list[str] = []
        value_node: ast.expr | None = None

        if isinstance(statement, ast.Assign):
            target_names = [
                target.id
                for target in statement.targets
                if isinstance(target, ast.Name)
            ]
            value_node = statement.value
        elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            target_names = [statement.target.id]
            value_node = statement.value

        if name in target_names and value_node is not None:
            return _literal_value(value_node)

    return None


def _normalize_down_revisions(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [item for item in value if item]


def collect_revision_graph(versions_dir: Path) -> dict[str, Any]:
    revision_files: list[dict[str, Any]] = []
    revision_to_file: dict[str, str] = {}
    duplicate_revisions: dict[str, list[str]] = {}
    files_missing_identifiers: list[str] = []

    for path in sorted(versions_dir.glob("*.py")):
        module = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        revision = _extract_identifier(module, "revision")
        down_revision = _extract_identifier(module, "down_revision")

        if not isinstance(revision, str):
            files_missing_identifiers.append(path.name)
            continue

        down_revisions = _normalize_down_revisions(down_revision)
        revision_files.append(
            {
                "file": path.name,
                "revision": revision,
                "down_revisions": down_revisions,
            }
        )

        existing_file = revision_to_file.get(revision)
        if existing_file:
            duplicate_revisions.setdefault(revision, [existing_file]).append(path.name)
        else:
            revision_to_file[revision] = path.name

    known_revisions = set(revision_to_file)
    referenced_revisions = {
        down_revision
        for item in revision_files
        for down_revision in item["down_revisions"]
    }
    missing_down_revisions = sorted(referenced_revisions - known_revisions)
    heads = sorted(
        revision
        for revision in known_revisions
        if revision not in referenced_revisions
    )

    return {
        "versions_dir": str(versions_dir),
        "files": revision_files,
        "known_revisions": sorted(known_revisions),
        "heads": heads,
        "missing_down_revisions": missing_down_revisions,
        "duplicate_revisions": duplicate_revisions,
        "files_missing_identifiers": sorted(files_missing_identifiers),
    }


def detect_untracked_migration_files(backend_root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--", "backend/alembic/versions"],
            cwd=backend_root.parent,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []

    untracked: list[str] = []
    for line in result.stdout.splitlines():
        if not line.startswith("?? "):
            continue
        candidate = line[3:].strip().replace("\\", "/")
        if candidate.endswith(".py"):
            untracked.append(candidate)
    return sorted(untracked)


def inspect_database_revision(db_url: str, known_revisions: Iterable[str]) -> dict[str, Any]:
    try:
        from sqlalchemy import create_engine, inspect, text
        from sqlalchemy.exc import SQLAlchemyError
    except (ImportError, AttributeError) as exc:
        return {"status": "db_error", "db_url": db_url, "error": f"sqlalchemy_unavailable: {exc}"}

    engine = create_engine(db_url)
    known_revision_set = set(known_revisions)
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            if "alembic_version" not in inspector.get_table_names():
                return {"status": "no_version_table", "db_url": db_url, "version_rows": []}

            version_rows = [row[0] for row in connection.execute(text("SELECT version_num FROM alembic_version"))]
            invalid_revisions = [revision for revision in version_rows if revision not in known_revision_set]
            return {
                "status": "invalid_revision" if invalid_revisions else "valid",
                "db_url": db_url,
                "version_rows": version_rows,
                "invalid_revisions": invalid_revisions,
            }
    except SQLAlchemyError as exc:
        return {"status": "db_error", "db_url": db_url, "error": str(exc)}
    finally:
        engine.dispose()


def build_audit_payload(backend_root: Path, db_url: str | None = None) -> tuple[dict[str, Any], int]:
    versions_dir = backend_root / "alembic" / "versions"
    graph = collect_revision_graph(versions_dir)
    resolved_db_url = db_url or os.getenv("DB_URL") or "sqlite:///./viru.db"
    db_state = inspect_database_revision(resolved_db_url, graph["known_revisions"])
    untracked = detect_untracked_migration_files(backend_root)

    chain_ok = not (
        graph["missing_down_revisions"]
        or graph["duplicate_revisions"]
        or graph["files_missing_identifiers"]
    )
    payload = {
        "chain_ok": chain_ok,
        "heads": graph["heads"],
        "missing_down_revisions": graph["missing_down_revisions"],
        "duplicate_revisions": graph["duplicate_revisions"],
        "files_missing_identifiers": graph["files_missing_identifiers"],
        "known_revisions": graph["known_revisions"],
        "db_state": db_state,
        "untracked_migration_files": untracked,
    }

    if not chain_ok:
        return payload, 3
    if db_state["status"] == "invalid_revision":
        return payload, 2
    if db_state["status"] == "db_error":
        return payload, 4
    return payload, 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Alembic revision graph and local DB state")
    parser.add_argument("--json", action="store_true", help="Emit JSON payload")
    parser.add_argument("--db-url", help="Override DB URL for validation")
    args = parser.parse_args()

    backend_root = Path(__file__).resolve().parents[3]
    payload, exit_code = build_audit_payload(backend_root, db_url=args.db_url)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
