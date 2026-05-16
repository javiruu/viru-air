import csv
import sys
import requests
from pathlib import Path

# Setup Python path to import app
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.db.session import SessionLocal, engine
from app.infrastructure.db.models import Airport, Base
from sqlalchemy import select

OURAIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"

def seed_airports():
    print(f"Downloading {OURAIRPORTS_URL}...")
    try:
        resp = requests.get(OURAIRPORTS_URL, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to download airports data: {e}")
        return

    lines = resp.text.splitlines()
    reader = csv.DictReader(lines)
    
    # Ensure table exists
    Base.metadata.create_all(engine)
    
    db = SessionLocal()
    try:
        existing = {a for a in db.scalars(select(Airport.iata)).all() if a}
        
        batch = []
        count = 0
        skipped = 0
        
        for row in reader:
            iata = row.get("iata_code", "").strip().upper()
            if not iata or len(iata) != 3:
                skipped += 1
                continue
                
            if iata in existing:
                skipped += 1
                continue
                
            airport_type = row.get("type", "")
            if airport_type in ("closed", "heliport", "seaplane_base"):
                skipped += 1
                continue
            
            try:
                lat = float(row.get("latitude_deg") or 0)
                lon = float(row.get("longitude_deg") or 0)
            except ValueError:
                skipped += 1
                continue
            
            # Limpiar nombre de ciudad si falta
            city = row.get("municipality")
            if not city:
                city = row.get("name", "Unknown")
            
            a = Airport(
                iata=iata,
                icao=row.get("ident") or None,
                name=row.get("name", "Unknown"),
                city=city,
                country=row.get("iso_country", "Unknown"),
                region=row.get("iso_region") or None,
                latitude=lat,
                longitude=lon,
                timezone=None,
                airport_type=airport_type,
                is_primary=(airport_type == "large_airport"),
                source="ourairports"
            )
            batch.append(a)
            existing.add(iata)
            
            if len(batch) >= 1000:
                db.add_all(batch)
                db.commit()
                count += len(batch)
                batch = []
                
        if batch:
            db.add_all(batch)
            db.commit()
            count += len(batch)
            
        print(f"Successfully seeded {count} airports. Skipped {skipped} without valid IATA or excluded type.")
        
    finally:
        db.close()

if __name__ == "__main__":
    seed_airports()
