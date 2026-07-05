from pathlib import Path
import builtins
import os
import sqlite3
import subprocess
import sys
import tempfile

from app.infrastructure.db.alembic_audit import build_audit_payload, inspect_database_revision


def test_current_alembic_chain_has_no_missing_down_revisions() -> None:
    backend_root = Path(__file__).resolve().parents[2]

    payload, exit_code = build_audit_payload(
        backend_root,
        db_url="sqlite:///:memory:",
    )

    assert exit_code == 0
    assert payload["chain_ok"] is True
    assert payload["missing_down_revisions"] == []
    assert payload["duplicate_revisions"] == {}
    assert payload["files_missing_identifiers"] == []
    assert payload["heads"] == ["0031_add_user_notification_state"]


def test_inspect_database_revision_flags_orphan_alembic_version(tmp_path: Path) -> None:
    db_path = tmp_path / "orphan-alembic.db"
    payload, exit_code = build_audit_payload(
        Path(__file__).resolve().parents[2],
        db_url=f"sqlite:///{db_path}",
    )
    known_revisions = payload["known_revisions"]

    import sqlite3

    connection = sqlite3.connect(db_path)
    try:
        connection.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        connection.execute("INSERT INTO alembic_version(version_num) VALUES (?)", ("0025_alert_rule_compare_against",))
        connection.commit()
    finally:
        connection.close()

    db_state = inspect_database_revision(f"sqlite:///{db_path}", known_revisions)

    assert db_state["status"] == "invalid_revision"
    assert db_state["invalid_revisions"] == ["0025_alert_rule_compare_against"]


def test_inspect_database_revision_reports_broken_sqlalchemy_import(monkeypatch) -> None:
    real_import = builtins.__import__

    def fail_sqlalchemy_import(name, *args, **kwargs):
        if name == "sqlalchemy" or name.startswith("sqlalchemy."):
            raise ImportError("broken SQLAlchemy install")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_sqlalchemy_import)

    db_state = inspect_database_revision("sqlite:///:memory:", [])

    assert db_state["status"] == "db_error"
    assert db_state["error"] == "sqlalchemy_unavailable: broken SQLAlchemy install"


def test_clean_upgrade_keeps_alembic_check_green() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    fd, db_path = tempfile.mkstemp(suffix="-alembic-clean.db", dir=backend_root)
    os.close(fd)

    env = os.environ.copy()
    env["DB_URL"] = f"sqlite:///./{Path(db_path).name}"

    try:
        upgrade = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=backend_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert upgrade.returncode == 0, upgrade.stderr

        check = subprocess.run(
            [sys.executable, "-m", "alembic", "check"],
            cwd=backend_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert check.returncode == 0, check.stderr or check.stdout
    finally:
        try:
            sqlite3.connect(db_path).close()
        except sqlite3.Error:
            pass
        try:
            os.remove(db_path)
        except OSError:
            pass
