from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from src.api.db.session import Base, engine
from src.api.routes.requests import router as requests_router
from src.api.schemas import QuoteRequest, QuoteResponse
from src.pricing.service import compute_quote

load_dotenv()

app = FastAPI(title="سالمة API", version="0.1.0")

# DB init
Base.metadata.create_all(bind=engine)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(requests_router)


@app.get("/health")
def health():
    return {"status": "ok"}


# Debug endpoint (UI will not use it directly)
@app.post("/quote", response_model=QuoteResponse)
def quote(req: QuoteRequest):
    return compute_quote(req)
