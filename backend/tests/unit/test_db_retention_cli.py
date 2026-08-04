import json
import os
import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    log_file = tmp_path / "retention.log"
    alert_file = tmp_path / "retention-alert.json"
    env = os.environ.copy()
    env["DB_URL"] = f"sqlite:///{(tmp_path / 'unused.db').as_posix()}"
    return subprocess.run(
        [
            sys.executable,
            "scripts/db_retention.py",
            *args,
            "--log-file",
            str(log_file),
            "--alert-file",
            str(alert_file),
        ],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_retention_cli_rejects_unsafe_community_window_before_db_work(tmp_path: Path) -> None:
    result = _run("--dry-run", "--community-trending-days", "29", tmp_path=tmp_path)

    assert result.returncode == 1
    alert = json.loads((tmp_path / "retention-alert.json").read_text(encoding="utf-8"))
    assert alert["error_type"] == "ValueError"
    assert "community_trending_days" in alert["error"]
    assert not (tmp_path / "unused.db").exists()


def test_retention_cli_rejects_conflicting_modes_before_db_work(tmp_path: Path) -> None:
    result = _run("--dry-run", "--apply", tmp_path=tmp_path)

    assert result.returncode == 1
    alert = json.loads((tmp_path / "retention-alert.json").read_text(encoding="utf-8"))
    assert alert["error_type"] == "ValueError"
    assert "mutually exclusive" in alert["error"]
    assert not (tmp_path / "unused.db").exists()
