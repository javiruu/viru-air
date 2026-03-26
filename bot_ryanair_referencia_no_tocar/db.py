# db.py
import aiosqlite
DB = "alerts.db"

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    user_id INTEGER,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    flight_date TEXT NOT NULL,
    threshold REAL NOT NULL,
    checks_per_day INTEGER NOT NULL,
    last_checked INTEGER DEFAULT 0,
    notified_at INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER,
    checked_at INTEGER,
    price REAL
);
"""

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.executescript(CREATE_TABLES)
        await db.commit()

# funciones helper: add_alert, get_active_alerts, update_last_checked, add_history, mark_notified
# (implementarlas según tu estilo; te doy estas firmas)
async def add_alert(alert: dict): ...
async def get_active_alerts(): ...
async def update_last_checked(alert_id, ts): ...
async def add_history(alert_id, ts, price): ...
async def mark_notified(alert_id, ts): ...
