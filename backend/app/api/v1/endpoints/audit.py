import os
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.db.audit_models import Session, AuditRecord
from app.db import state_logic
from app.models.schemas import AuditCommitRequest, AuditRecordOut, AuditLogResponse

router = APIRouter()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
BRIEF_PATH = os.path.join(BACKEND_DIR, "data", "intelligence_brief.json")

def _seed_initial_audit_records(session):
    """Seed initial records from intelligence_brief.json if audit_records is empty."""
    candidate_paths = [
        BRIEF_PATH,
        os.path.join(BACKEND_DIR, "..", "data", "processed", "intelligence_brief.json"),
        os.path.join(BACKEND_DIR, "..", "SIH backend", "intelligence_brief.json"),
    ]
    brief_file = None
    for p in candidate_paths:
        if os.path.exists(p):
            brief_file = p
            break

    if not brief_file:
        print("[!] No intelligence_brief.json found for pre-population.")
        return

    try:
        with open(brief_file, "r", encoding="utf-8") as f:
            brief_data = json.load(f)
    except Exception as e:
        print(f"[!] Warning: Could not read {brief_file}: {e}")
        return

    samples = brief_data[:3]
    for item in samples:
        loc = item.get("location", {})
        lat = loc.get("latitude", 28.6)
        lon = loc.get("longitude", 77.2)
        rec = AuditRecord(
            query_string=item.get("query", "tactical reconnaissance"),
            latitude=lat,
            longitude=lon,
            sensor_type=item.get("sensor_type", "Sentinel-2"),
            status="APPROVED",
            confidence_score=item.get("confidence_score", 0.95),
            patch_id=item.get("patch_id") or f"patch_{item.get('id', 1)}",
            analyst_id=item.get("analyst_id", "OFFICER_DELHI_01"),
            analyst_rationale=item.get("analyst_rationale", "Pre-populated tactical brief entry."),
            extra_metadata=json.dumps({"seeded": True})
        )
        session.add(rec)
        session.flush()
        rec.hash_value = state_logic.generate_hash(rec)
        
    session.commit()
    print(f"[*] Pre-populated {len(samples)} audit entries from intelligence brief.")

@router.post("/commit", response_model=AuditRecordOut)
def commit_audit(payload: AuditCommitRequest):
    """
    Commit or update an analyst audit record.
    If record_id exists, updates through state_logic.update_status().
    If record_id is None, creates a new AuditRecord, generates SHA-256 hash, and commits.
    """
    session = Session()
    try:
        if payload.record_id is not None:
            try:
                record = state_logic.update_status(
                    session=session,
                    record_id=payload.record_id,
                    new_status=payload.new_status,
                    confidence=payload.confidence,
                    analyst_id=payload.analyst_id,
                    rationale=payload.rationale
                )
                return record
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))
        else:
            norm_status = str(payload.new_status).strip().upper()
            new_record = AuditRecord(
                patch_id=payload.patch_id,
                latitude=payload.latitude if payload.latitude is not None else 28.5,
                longitude=payload.longitude if payload.longitude is not None else 76.5,
                status=norm_status,
                confidence_score=payload.confidence,
                analyst_id=payload.analyst_id or "OFFICER_DELHI_01",
                analyst_rationale=payload.rationale,
                reviewed_at=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            session.add(new_record)
            session.flush()
            new_record.hash_value = state_logic.generate_hash(new_record)
            session.commit()
            session.refresh(new_record)
            return new_record
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@router.get("/log", response_model=AuditLogResponse)
def get_audit_log(
    status: Optional[str] = Query(None, description="Filter by status (PENDING, APPROVED, REJECTED)"),
    limit: int = Query(50, ge=1, le=200)
):
    """
    Retrieve audit trail log entries with optional status filtering.
    Pre-populates sample entries on first run if database is empty.
    """
    session = Session()
    try:
        count = session.query(AuditRecord).count()
        if count == 0:
            _seed_initial_audit_records(session)

        query = session.query(AuditRecord)
        if status:
            query = query.filter(AuditRecord.status == status.strip().upper())

        total = query.count()
        records = query.order_by(AuditRecord.timestamp.desc(), AuditRecord.id.desc()).limit(limit).all()
        return {"total": total, "records": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.get("/export")
def export_provenance(
    status: Optional[str] = Query(None, description="Filter by status (APPROVED, REJECTED, PENDING)"),
    limit: int = Query(200, ge=1, le=1000)
):
    """
    Export analyst decisions as a GeoJSON FeatureCollection with full provenance.
    Each feature includes source scene, processing hash, analyst rationale,
    confidence, sensor and acquisition metadata — satisfying PS §2.2.5.
    """
    from fastapi.responses import Response

    session = Session()
    try:
        query = session.query(AuditRecord)
        if status:
            query = query.filter(AuditRecord.status == status.strip().upper())
        records = query.order_by(AuditRecord.timestamp.desc()).limit(limit).all()

        features = []
        for rec in records:
            lat = rec.latitude or 0.0
            lon = rec.longitude or 0.0
            # Point geometry for the committed location
            geometry = {"type": "Point", "coordinates": [lon, lat]}

            # Parse any extra metadata stored as JSON string
            extra = {}
            if rec.extra_metadata:
                try:
                    extra = json.loads(rec.extra_metadata)
                except Exception:
                    extra = {}

            reviewed_str = None
            if rec.reviewed_at:
                try:
                    reviewed_str = rec.reviewed_at.isoformat() + "Z"
                except Exception:
                    reviewed_str = str(rec.reviewed_at)

            timestamp_str = None
            if rec.timestamp:
                try:
                    timestamp_str = rec.timestamp.isoformat() + "Z"
                except Exception:
                    timestamp_str = str(rec.timestamp)

            properties = {
                "patch_id": rec.patch_id,
                "status": rec.status,
                "confidence_score": rec.confidence_score,
                "analyst_id": rec.analyst_id,
                "analyst_rationale": rec.analyst_rationale,
                "sensor_type": rec.sensor_type or "Sentinel-2 L2A",
                "query_string": rec.query_string,
                "hash_value": rec.hash_value,
                "timestamp": timestamp_str,
                "reviewed_at": reviewed_str,
                "processing_provenance": {
                    "engine": "CLIP ViT-L/14 + FAISS HNSW",
                    "scl_masking": "Sentinel-2 SCL band (20m)",
                    "false_alarm_gate": "SFAS cosine gate (τ=0.15)",
                    "classifier": "Zero-shot tactical CLIP (τ=0.07)",
                    "record_id": rec.id,
                    **extra
                }
            }
            features.append({"type": "Feature", "geometry": geometry, "properties": properties})

        geojson = {
            "type": "FeatureCollection",
            "name": "IDEAX_Provenance_Export",
            "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_records": len(features),
            "features": features
        }

        payload = json.dumps(geojson, indent=2)
        return Response(
            content=payload,
            media_type="application/geo+json",
            headers={"Content-Disposition": "attachment; filename=\"ideax_provenance.geojson\""}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

