from __future__ import annotations

import importlib


def test_api_startup_no_longer_exposes_hotel_sweep_scheduler() -> None:
    app_main = importlib.import_module("app.main")

    assert not hasattr(app_main, "_start_sweep_loop")
    assert not hasattr(app_main, "_hotel_sweep_enabled")
    assert not hasattr(app_main, "_hotel_sweep_interval")
    assert not hasattr(app_main, "_hotel_sweep_provider")
