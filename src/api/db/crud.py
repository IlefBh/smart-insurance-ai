from __future__ import annotations

import json
import uuid
import datetime as dt
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from src.api.db.models import QuoteRequestORM, QuoteStatus


def create_request(db: Session, insured_id: str, request_payload: Dict[str, Any]) -> QuoteRequestORM:
    now = dt.datetime.utcnow()
    obj = QuoteRequestORM(
        id=str(uuid.uuid4()),
        insured_id=insured_id,
        created_at=now,
        updated_at=now,
        status=QuoteStatus.PENDING,
        request_json=json.dumps(request_payload, ensure_ascii=False),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_requests_by_insured(db: Session, insured_id: str) -> List[QuoteRequestORM]:
    stmt = (
        select(QuoteRequestORM)
        .where(QuoteRequestORM.insured_id == insured_id)
        .order_by(desc(QuoteRequestORM.created_at))
    )
    return list(db.execute(stmt).scalars().all())


def list_pending_requests(db: Session) -> List[QuoteRequestORM]:
    stmt = (
        select(QuoteRequestORM)
        .where(QuoteRequestORM.status.in_([QuoteStatus.PENDING, QuoteStatus.AI_PROPOSED]))
        .order_by(desc(QuoteRequestORM.created_at))
    )
    return list(db.execute(stmt).scalars().all())


def get_request(db: Session, request_id: str) -> Optional[QuoteRequestORM]:
    stmt = select(QuoteRequestORM).where(QuoteRequestORM.id == request_id)
    return db.execute(stmt).scalars().first()


def set_ai_quote(db: Session, request_id: str, quote_response: Dict[str, Any]) -> QuoteRequestORM:
    obj = get_request(db, request_id)
    if obj is None:
        raise ValueError("request_not_found")

    obj.ai_quote_json = json.dumps(quote_response, ensure_ascii=False)
    obj.status = QuoteStatus.AI_PROPOSED
    obj.updated_at = dt.datetime.utcnow()

    db.commit()
    db.refresh(obj)
    return obj


def finalize_request(
    db: Session,
    request_id: str,
    action: str,  # ACCEPT / MODIFY / REJECT
    final_offer: Optional[Dict[str, Any]],
    processed_by: str,
    notes: Optional[str] = None,
) -> QuoteRequestORM:
    obj = get_request(db, request_id)
    if obj is None:
        raise ValueError("request_not_found")

    now = dt.datetime.utcnow()
    obj.processed_by = processed_by
    obj.processed_at = now
    obj.updated_at = now
    obj.notes = notes

    action = action.upper().strip()
    if action == "REJECT":
        obj.status = QuoteStatus.REJECTED
        obj.final_offer_json = None
    else:
        if final_offer is None:
            raise ValueError("final_offer_required")
        obj.status = QuoteStatus.PROCESSED
        obj.final_offer_json = json.dumps(final_offer, ensure_ascii=False)

    db.commit()
    db.refresh(obj)
    return obj


def orm_to_public(obj: QuoteRequestORM) -> Dict[str, Any]:
    def safe_load(s: Optional[str]):
        return json.loads(s) if s else None

    return {
        "id": obj.id,
        "insured_id": obj.insured_id,
        "created_at": obj.created_at.isoformat() + "Z",
        "updated_at": obj.updated_at.isoformat() + "Z",
        "status": obj.status,
        "request": safe_load(obj.request_json),
        "ai_quote": safe_load(obj.ai_quote_json),
        "final_offer": safe_load(obj.final_offer_json),
        "processed_by": obj.processed_by,
        "processed_at": (obj.processed_at.isoformat() + "Z") if obj.processed_at else None,
        "notes": obj.notes,
    }
