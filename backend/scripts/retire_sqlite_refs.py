import re
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
app_dir = repo_root / 'backend' / 'app'

# 1. models.py
models_path = app_dir / 'infrastructure' / 'db' / 'models.py'
lines = models_path.read_text(encoding='utf-8').splitlines(True)
new_lines = [l for l in lines if 'sqlite_where' not in l]
models_path.write_text(''.join(new_lines), encoding='utf-8')
print('1. models.py updated')

# 2. community_trending_retention.py
ctr_path = app_dir / 'services' / 'community_trending_retention.py'
txt = ctr_path.read_text(encoding='utf-8')
txt = txt.replace("SQLite's ", "")
ctr_path.write_text(txt, encoding='utf-8')
print('2. community_trending_retention.py updated')

# 3. hotels_service.py
hs_path = app_dir / 'services' / 'hotels_service.py'
txt = hs_path.read_text(encoding='utf-8')
txt = txt.replace("SQLite ", "")
hs_path.write_text(txt, encoding='utf-8')
print('3. hotels_service.py updated')

# 4. quick_search_cache_upsert.py
qsc_path = app_dir / 'services' / 'quick_search_cache_upsert.py'
txt = qsc_path.read_text(encoding='utf-8')
txt = txt.replace("from sqlalchemy.dialects.sqlite import insert as sqlite_insert\n", "")
txt = txt.replace("from sqlalchemy.dialects.sqlite import insert as sqlite_insert\r\n", "")
# remove elif dialect_name == 'sqlite': db.execute(_build_sqlite_upsert(values))
txt = re.sub(r"\s*elif dialect_name == [\"']sqlite[\"']:\s*db\.execute\(_build_sqlite_upsert\(values\)\)", "", txt)
# remove _build_sqlite_upsert definition
txt = re.sub(r"def _build_sqlite_upsert\([\s\S]*?\n\n", "\n", txt)
qsc_path.write_text(txt, encoding='utf-8')
print('4. quick_search_cache_upsert.py updated')

# 5. quick_search_popularity.py
qsp_path = app_dir / 'services' / 'quick_search_popularity.py'
txt = qsp_path.read_text(encoding='utf-8')
txt = txt.replace("from sqlalchemy.dialects.sqlite import insert as sqlite_insert\n", "")
txt = txt.replace("from sqlalchemy.dialects.sqlite import insert as sqlite_insert\r\n", "")
txt = re.sub(r"\s*elif dialect_name == [\"']sqlite[\"']:[\s\S]*?db\.execute\(_build_sqlite_daily_upsert\(normalized\)\)", "", txt)
txt = re.sub(r"def _build_sqlite_upsert\([\s\S]*?\n\n", "\n", txt)
txt = re.sub(r"def _build_sqlite_daily_upsert\([\s\S]*?\n\n", "\n", txt)
qsp_path.write_text(txt, encoding='utf-8')
print('5. quick_search_popularity.py updated')

# 6. hotel_observability_metrics.py
hom_path = app_dir / 'services' / 'hotel_observability_metrics.py'
txt = hom_path.read_text(encoding='utf-8')
txt = txt.replace("from sqlalchemy.dialects.sqlite import insert as sqlite_insert\n", "")
txt = txt.replace("from sqlalchemy.dialects.sqlite import insert as sqlite_insert\r\n", "")
fallback_metric = '''    if dialect_name == "postgresql":\n        db.execute(_postgresql_upsert(key, increment))\n    else:\n        existing = db.query(HotelDailyMetric).filter_by(metric_date=key.metric_date, metric_name=key.metric_name, provider=key.provider, outcome=key.outcome).first()\n        if existing:\n            existing.count += increment\n            existing.updated_at = utc_now_naive()\n        else:\n            db.add(HotelDailyMetric(metric_date=key.metric_date, metric_name=key.metric_name, provider=key.provider, outcome=key.outcome, count=increment, updated_at=utc_now_naive()))'''
txt = re.sub(r"    if dialect_name == [\"']postgresql[\"']:[\s\S]*?raise RuntimeError\([\"']hotel_metric_atomic_upsert_unsupported_dialect[\"']\)", fallback_metric, txt)
txt = re.sub(r"def _sqlite_upsert\([\s\S]*?\n\n", "\n", txt)
hom_path.write_text(txt, encoding='utf-8')
print('6. hotel_observability_metrics.py updated')

# 7. hotel_provider_latency.py
hpl_path = app_dir / 'services' / 'hotel_provider_latency.py'
txt = hpl_path.read_text(encoding='utf-8')
txt = txt.replace("from sqlalchemy.dialects.sqlite import insert as sqlite_insert\n", "")
txt = txt.replace("from sqlalchemy.dialects.sqlite import insert as sqlite_insert\r\n", "")
fallback_latency = '''        else:\n            existing = db.query(HotelProviderLatencyAggregate).filter_by(provider_run_id=values["provider_run_id"], provider=values["provider"], operation=values["operation"], outcome=values["outcome"], error_code=values["error_code"]).first()\n            if existing:\n                existing.sample_count = values["sample_count"]\n                existing.total_duration_ms = values["total_duration_ms"]\n                existing.min_duration_ms = values["min_duration_ms"]\n                existing.max_duration_ms = values["max_duration_ms"]\n                existing.updated_at = utc_now_naive()\n            else:\n                db.add(HotelProviderLatencyAggregate(**values))'''
txt = re.sub(r"        elif dialect_name == [\"']sqlite[\"']:[\s\S]*?raise RuntimeError\([\"']hotel_provider_latency_aggregate_unsupported_dialect[\"']\)", fallback_latency, txt)
hpl_path.write_text(txt, encoding='utf-8')
print('7. hotel_provider_latency.py updated')

print('All services cleaned of SQLite references successfully.')
