import os
import json
import hashlib
from datetime import datetime, timezone
from app.db.audit_models import AuditRecord, session

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

def generate_hash(record):
    """Cryptographic SHA-256 hash for operational auditability & defense compliance."""
    data_string = (
        f"{record.id}|{record.query_string}|{record.latitude}|{record.longitude}|"
        f"{record.timestamp}|{record.sensor_type}|{record.status}|{record.confidence_score}|"
        f"{record.reviewed_at}|{record.analyst_id}"
    )
    return hashlib.sha256(data_string.encode("utf-8")).hexdigest()

def update_status(session, record_id, new_status, confidence=None, analyst_id=None, rationale=None):
    record = session.query(AuditRecord).filter(AuditRecord.id == record_id).first()

    if record is None:
        raise ValueError(f"Record with ID {record_id} not found!")

    # Normalize to uppercase for consistent state checking
    normalized_status = str(new_status).strip().upper()
    current_status = str(record.status).strip().upper() if record.status else "PENDING"

    valid_transitions = {
        "PENDING": ["APPROVED", "REJECTED"],
        "APPROVED": ["REJECTED"],
        "REJECTED": ["APPROVED"]
    }

    if normalized_status not in valid_transitions.get(current_status, []):
        raise ValueError(f"Invalid state transition: {current_status} -> {normalized_status}")

    record.status = normalized_status
    record.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    
    if confidence is not None:
        record.confidence_score = float(confidence)
    if analyst_id is not None:
        record.analyst_id = str(analyst_id)
    if rationale is not None:
        record.analyst_rationale = str(rationale)

    record.hash_value = generate_hash(record)
    session.commit()
    print(f"Record {record_id} successfully updated to {normalized_status} [Hash: {record.hash_value[:10]}...]")
    return record

def export_approved_records(session, filename=None):
    if filename is None:
        filename = os.path.join(BASE_DIR, "intelligence_brief.json")
    elif not os.path.isabs(filename):
        filename = os.path.join(BASE_DIR, filename)

    approved_records = session.query(AuditRecord).filter(
        AuditRecord.status.in_(["APPROVED", "Approved"])
    ).all()

    brief = []
    for r in approved_records:
        brief.append({
            "id": r.id,
            "query": r.query_string,
            "location": {"latitude": r.latitude, "longitude": r.longitude},
            "timestamp": str(r.timestamp),
            "reviewed_at": str(r.reviewed_at) if r.reviewed_at else None,
            "sensor_type": r.sensor_type,
            "confidence_score": r.confidence_score,
            "patch_id": r.patch_id,
            "t1_timestamp": str(r.t1_timestamp) if r.t1_timestamp else None,
            "t2_timestamp": str(r.t2_timestamp) if r.t2_timestamp else None,
            "t1_image_path": r.t1_image_path,
            "t2_image_path": r.t2_image_path,
            "geojson_polygon": r.geojson_polygon,
            "analyst_id": r.analyst_id,
            "analyst_rationale": r.analyst_rationale,
            "hash": r.hash_value or generate_hash(r)
        })

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(brief, f, indent=4)

    print(f"Exported {len(brief)} approved records to {filename}")
    return brief

# ---- Standalone Testing ----
if __name__ == "__main__":
    try:
        update_status(
            session=session,
            record_id=1,
            new_status="APPROVED",
            confidence=0.95,
            analyst_id="OFFICER_DELHI_01",
            rationale="Confirmed military infrastructure change.",
        )
        export_approved_records(session)
    except Exception as e:
        print("Error during test:", e)