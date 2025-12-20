from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.db.session import get_db
from src.api.db import crud
from src.api.schemas import QuoteRequest, FinalizeRequest
from src.pricing.service import compute_quote

router = APIRouter(prefix="/requests", tags=["requests"])


@router.post("", response_model=dict)
def create_new_request(req: QuoteRequest, insured_id: str = "demo_user", db: Session = Depends(get_db)):
    obj = crud.create_request(db, insured_id=insured_id, request_payload=req.model_dump())
    return {"id": obj.id, "status": obj.status}


@router.get("", response_model=List[dict])
def list_my_requests(insured_id: str = "demo_user", db: Session = Depends(get_db)):
    rows = crud.list_requests_by_insured(db, insured_id=insured_id)
    return [crud.orm_to_public(r) for r in rows]


@router.get("/pending", response_model=List[dict])
def list_pending_requests(db: Session = Depends(get_db)):
    rows = crud.list_pending_requests(db)
    return [crud.orm_to_public(r) for r in rows]


@router.get("/{request_id}", response_model=dict)
def get_request(request_id: str, db: Session = Depends(get_db)):
    obj = crud.get_request(db, request_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="request_not_found")
    return crud.orm_to_public(obj)


@router.post("/{request_id}/ai_offer", response_model=dict)
def generate_ai_offer(request_id: str, db: Session = Depends(get_db)):
    obj = crud.get_request(db, request_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="request_not_found")

    public = crud.orm_to_public(obj)
    payload = public["request"]
    req = QuoteRequest(**payload)

    quote_resp = compute_quote(req)
    updated = crud.set_ai_quote(db, request_id, quote_resp.model_dump())

    return crud.orm_to_public(updated)


@router.post("/{request_id}/finalize", response_model=dict)
def finalize(request_id: str, body: FinalizeRequest, db: Session = Depends(get_db)):
    action = body.action.upper().strip()
    if action not in {"ACCEPT", "MODIFY", "REJECT"}:
        raise HTTPException(status_code=400, detail="invalid_action")

    try:
        updated = crud.finalize_request(
            db=db,
            request_id=request_id,
            action=action,
            final_offer=body.final_offer,
            processed_by=body.processed_by,
            notes=body.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return crud.orm_to_public(updated)
