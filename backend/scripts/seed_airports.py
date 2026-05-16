import json
import sys
from pathlib import Path

# Setup Python path to import app
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.db.session import SessionLocal, engine
from app.infrastructure.db.models import Airport, Base
from sqlalchemy import select, delete

def seed_airports():
    master_path = Path(__file__).resolve().parents[1] / "data" / "airports_master.json"
    print(f"Reading from {master_path}...")
    
    if not master_path.exists():
        print(f"File not found: {master_path}")
        return

    with open(master_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Ensure table exists
    Base.metadata.create_all(engine)
    
    db = SessionLocal()
    try:
        # Delete existing airports to ensure ONLY the ones from Ryanair are kept
        db.execute(delete(Airport))
        db.commit()
        print("Cleared existing airports table.")
        
        batch = []
        count = 0
        
        for row in data:
            a = Airport(
                iata=row["iata"],
                icao=row.get("icao"),
                name=row["name"],
                city=row["city"],
                country=row["country"],
                region=row.get("region"),
                latitude=row["latitude"],
                longitude=row["longitude"],
                timezone=row.get("timezone"),
                airport_type=row.get("airport_type"),
                is_primary=row.get("is_primary", False),
                source=row.get("source", "ryanair_airports")
            )
            batch.append(a)
            
        if batch:
            db.add_all(batch)
            db.commit()
            count += len(batch)
            
        print(f"Successfully seeded {count} Ryanair-supported airports.")
        
    finally:
        db.close()

if __name__ == "__main__":
    seed_airports()
