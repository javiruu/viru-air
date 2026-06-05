from pathlib import Path

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
    assert payload["heads"] == ["0026"]


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
