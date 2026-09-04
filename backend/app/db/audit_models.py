import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class AuditRecord(Base):
    __tablename__ = "audit_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    query_string = Column(String, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    sensor_type = Column(String, default="Sentinel-2")
    status = Column(String, default="PENDING")  # 'PENDING', 'APPROVED', 'REJECTED'
    confidence_score = Column(Float, nullable=True)
    hash_value = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)   
    patch_id = Column(String, nullable=True)  # e.g., "T43RFM_4500_4500"
    t1_timestamp = Column(DateTime, nullable=True)
    t2_timestamp = Column(DateTime, nullable=True)
    t1_image_path = Column(String, nullable=True)
    t2_image_path = Column(String, nullable=True)
    geojson_polygon = Column(Text, nullable=True)
    sfas_confidence = Column(Float, nullable=True)
    analyst_id = Column(String, nullable=True)  # e.g., "OFFICER_DELHI_01"
    analyst_rationale = Column(Text, nullable=True)
    extra_metadata = Column(Text, nullable=True)

# Locate audit.db in the backend/data directory
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DB_PATH = os.path.join(BASE_DIR, "backend", "data", "audit.db")
engine = create_engine(f"sqlite:///{DB_PATH}")
Base.metadata.create_all(engine)

# Auto-migration: ensure all model columns exist in existing SQLite table
def _ensure_columns():
    inspector = inspect(engine)
    existing_cols = {col['name'] for col in inspector.get_columns("audit_records")}
    column_defs = [
        ("reviewed_at", "DATETIME"),
        ("patch_id", "TEXT"),
        ("t1_timestamp", "DATETIME"),
        ("t2_timestamp", "DATETIME"),
        ("t1_image_path", "TEXT"),
        ("t2_image_path", "TEXT"),
        ("geojson_polygon", "TEXT"),
        ("sfas_confidence", "FLOAT"),
        ("analyst_id", "TEXT"),
        ("analyst_rationale", "TEXT"),
        ("extra_metadata", "TEXT")
    ]
    with engine.connect() as conn:
        for col_name, col_type in column_defs:
            if col_name not in existing_cols:
                conn.execute(text(f"ALTER TABLE audit_records ADD COLUMN {col_name} {col_type}"))
        conn.commit()

_ensure_columns()

Session = sessionmaker(bind=engine)
session = Session()

if __name__ == "__main__":
    new_record = AuditRecord(
        query_string="newly built structures near river",
        latitude=28.6,
        longitude=77.2,
        sensor_type="Sentinel-2",
        status="PENDING",
        patch_id="T43RFM_4500_4500",
        t1_timestamp=datetime.now(timezone.utc),
        t2_timestamp=datetime.now(timezone.utc)
    )
    session.add(new_record)
    session.commit()
    print("Saved! Record ID:", new_record.id)