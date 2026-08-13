from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8-sig")


def test_backend_image_contract_is_locked_and_non_root() -> None:
    dockerfile = _read("backend/Dockerfile")

    assert "python:3.12-slim-bookworm AS builder" in dockerfile
    assert "uv sync --locked --no-dev --no-install-project" in dockerfile
    assert "USER app" in dockerfile
    assert "LOG_FILE=/tmp/viru.log" in dockerfile
    assert "alembic upgrade" not in dockerfile

    dockerignore = _read("backend/.dockerignore")
    assert ".env" in dockerignore
    assert "*.db" in dockerignore
    assert "logs/" in dockerignore


def test_hotel_sweep_cronjob_is_safe_by_default() -> None:
    manifest = _read("infra/k8s/hotels-sweep-cronjob.yaml")

    assert "kind: CronJob" in manifest
    assert "suspend: true" in manifest
    assert "schedule: \"0 * * * *\"" in manifest
    assert "concurrencyPolicy: Forbid" in manifest
    assert "restartPolicy: OnFailure" in manifest
    assert "runAsNonRoot: true" in manifest
    assert "runAsUser: 10001" in manifest
    assert "allowPrivilegeEscalation: false" in manifest
    assert 'drop: ["ALL"]' in manifest
    assert 'command: ["python", "-m", "app.worker.hotels_sweep"]' in manifest
    assert 'args: ["--once", "--provider", "mock"]' in manifest
    assert "name: DB_URL" in manifest
    assert "name: viru-backend-runtime" in manifest
    assert "key: DB_URL" in manifest
    assert 'name: LOG_FILE\n                  value: "/tmp/viru.log"' in manifest
    assert 'name: HOTEL_SWEEP_ENABLED\n                  value: "false"' in manifest
    assert "key: JWT_SECRET" in manifest
    assert "name: tmp" in manifest
    assert "mountPath: /tmp" in manifest


def test_hotel_migration_job_is_separate_and_suspended() -> None:
    manifest = _read("infra/k8s/hotels-migrate-job.yaml")
    cronjob = _read("infra/k8s/hotels-sweep-cronjob.yaml")

    assert "kind: Job" in manifest
    assert "suspend: true" in manifest
    assert "restartPolicy: Never" in manifest
    assert "runAsNonRoot: true" in manifest
    assert "runAsUser: 10001" in manifest
    assert "allowPrivilegeEscalation: false" in manifest
    assert 'drop: ["ALL"]' in manifest
    assert 'command: ["alembic", "upgrade", "head"]' in manifest
    assert "name: DB_URL" in manifest
    assert "name: viru-backend-runtime" in manifest
    assert "key: JWT_SECRET" in manifest
    assert 'name: LOG_FILE\n              value: "/tmp/viru.log"' in manifest
    assert "name: tmp" in manifest
    assert "mountPath: /tmp" in manifest
    assert 'image: ghcr.io/your-org/viru-backend:latest' in manifest
    assert 'image: ghcr.io/your-org/viru-backend:latest' in cronjob


def test_runtime_fixes_from_container_gate_are_registered() -> None:
    alembic_ini = _read("backend/alembic.ini")
    pyproject = _read("backend/pyproject.toml")
    cronjob = _read("infra/k8s/hotels-sweep-cronjob.yaml")
    migrate = _read("infra/k8s/hotels-migrate-job.yaml")

    assert "prepend_sys_path = ." in alembic_ini

    deps_start = pyproject.index("[project]")
    opt_start = pyproject.index("[project.optional-dependencies]")
    core_section = pyproject[deps_start:opt_start]
    dev_section = pyproject[opt_start:]
    assert '"httpx>=0.28.0"' in core_section
    assert '"httpx>=0.28.0"' not in dev_section

    assert "key: JWT_SECRET" in cronjob
    assert "key: JWT_SECRET" in migrate


def test_ci_runs_the_redacted_hotel_mock_canary_gate_in_backend_job() -> None:
    workflow = _read("infra/github/workflows/ci.yml")
    backend_block = workflow.split("\n  backend:\n", 1)[1].split("\n  frontend:\n", 1)[0]

    assert "working-directory: backend" in backend_block
    assert "Hotel Mock canary dry-run (H44/H43)" in backend_block
    assert "python scripts/hotel_mock_canary.py --dry-run" in backend_block


def test_ghcr_publish_workflow_and_activation_overlay_are_prepared() -> None:
    release = _read("infra/github/workflows/release.yml")
    secret = _read("infra/k8s/runtime-secret.example.yaml")
    overlay = _read("infra/k8s/overlays/staging/kustomization.yaml")
    base_cron = _read("infra/k8s/hotels-sweep-cronjob.yaml")

    assert "publish-image" in release
    assert "docker/build-push-action" in release
    assert "packages: write" in release
    assert "sha-${{ github.sha }}" in release

    assert "suspend: true" in base_cron  # base must stay fail-closed

    assert "kind: Secret" in secret
    assert "name: viru-backend-runtime" in secret
    assert "DB_URL" in secret
    assert "JWT_SECRET" in secret

    assert "patchesStrategicMerge" in overlay
    assert "hotels-sweep-cronjob-enabled-patch.yaml" in overlay
    assert "newName" in overlay


def test_enabled_cronjob_patch_is_explicit_and_not_default() -> None:
    base = _read("infra/k8s/hotels-sweep-cronjob.yaml")
    patch = _read("infra/k8s/hotels-sweep-cronjob-enabled-patch.yaml")

    assert 'suspend: true' in base
    assert 'suspend: false' in patch
    assert 'Kustomize strategic-merge patch only' in patch
    assert 'name: HOTEL_FEATURE_ENABLED' in patch
    assert 'name: HOTEL_SWEEP_ENABLED' in patch
    assert 'value: "true"' in patch
