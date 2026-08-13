from pathlib import Path


def test_kubernetes_revalidation_worker_uses_the_real_entrypoint_and_runtime_secret() -> None:
    manifest = (Path(__file__).parents[3] / "infra" / "k8s" / "worker.yaml").read_text(encoding="utf-8")

    assert 'command: ["python", "-m", "app.services.revalidation_worker_entrypoint"]' in manifest
    assert 'name: DB_URL' in manifest
    assert 'name: JWT_SECRET' in manifest
    assert "worker placeholder" not in manifest
