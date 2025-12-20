from __future__ import annotations

import datetime as dt
from sqlalchemy import Column, String, DateTime, Text

from src.api.db.session import Base


class QuoteStatus:
    PENDING = "PENDING"
    AI_PROPOSED = "AI_PROPOSED"
    PROCESSED = "PROCESSED"
    REJECTED = "REJECTED"


class QuoteRequestORM(Base):
    __tablename__ = "quote_requests"

    id = Column(String, primary_key=True, index=True)
    insured_id = Column(String, index=True, nullable=False, default="demo_user")

    created_at = Column(DateTime, nullable=False, default=lambda: dt.datetime.utcnow())
    updated_at = Column(DateTime, nullable=False, default=lambda: dt.datetime.utcnow())

    status = Column(String, nullable=False, default=QuoteStatus.PENDING)

    request_json = Column(Text, nullable=False)
    ai_quote_json = Column(Text, nullable=True)     # QuoteResponse: {decision, offer}
    final_offer_json = Column(Text, nullable=True)  # Offer only (final)

    processed_by = Column(String, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
