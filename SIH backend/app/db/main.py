import os
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from typing import Optional, List
from app.db.audit_models import Session as get_db, AuditRecord
from app.db.state_logic import update_status, export_approved_records

app = FastAPI(
    title="Geospatial Intelligence Audit & Commit API (VAYU Defense)",
    version="1.0.0",
    description="Air-gapped operational audit trail and intelligence brief exporter for Indian Army"
)

# CORS Middleware for frontend dashboard integration (Member P's React UI)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AuditActionRequest(BaseModel):
    record_id: int
    new_status: str  # "APPROVED" or "REJECTED"
    confidence_score: Optional[float] = None
    analyst_id: Optional[str] = "OFFICER_DELHI_01"
    analyst_rationale: Optional[str] = None

    @field_validator("record_id", mode="before")
    @classmethod
    def parse_record_id(cls, v):
        if isinstance(v, str):
            return int(v.strip())
        return v

    @field_validator("confidence_score", mode="before")
    @classmethod
    def parse_confidence(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return float(v.strip())
        return v

    @field_validator("new_status", mode="before")
    @classmethod
    def clean_status(cls, v):
        if isinstance(v, str):
            return v.strip().upper()
        return v

@app.get("/")
def read_root():
    return {
        "service": "VAYU Geospatial Intelligence Audit API",
        "status": "online",
        "mode": "air-gapped-edge"
    }

@app.get("/audit/records", status_code=status.HTTP_200_OK)
def get_all_records(status_filter: Optional[str] = None):
    """Fetches records for Member P's Tactical UI cards."""
    db_session = get_db()
    try:
        query = db_session.query(AuditRecord)
        if status_filter:
            query = query.filter(AuditRecord.status == status_filter.upper())
        records = query.all()
        return [
            {
                "id": r.id,
                "query": r.query_string,
                "location": {"latitude": r.latitude, "longitude": r.longitude},
                "timestamp": str(r.timestamp),
                "sensor_type": r.sensor_type,
                "status": r.status,
                "confidence_score": r.confidence_score,
                "patch_id": r.patch_id,
                "t1_image_path": r.t1_image_path,
                "t2_image_path": r.t2_image_path,
                "hash": r.hash_value,
                "analyst_id": r.analyst_id
            }
            for r in records
        ]
    finally:
        db_session.close()

@app.post("/audit/commit", status_code=status.HTTP_200_OK)
def commit_audit_record(payload: AuditActionRequest):
    db_session = get_db()
    try:
        record = update_status(
            session=db_session,
            record_id=payload.record_id,
            new_status=payload.new_status,
            confidence=payload.confidence_score,
            analyst_id=payload.analyst_id,
            rationale=payload.analyst_rationale
        )
        return {
            "status": "success",
            "message": f"Record {payload.record_id} successfully updated to {payload.new_status}",
            "record_id": record.id,
            "new_status": record.status,
            "hash": record.hash_value
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()

@app.get("/audit/export", status_code=status.HTTP_200_OK)
def export_brief():
    db_session = get_db()
    try:
        brief = export_approved_records(db_session)
        return {
            "status": "success",
            "count": len(brief),
            "message": "Approved records exported successfully to intelligence_brief.json"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()