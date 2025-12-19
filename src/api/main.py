from fastapi import FastAPI

app = FastAPI(title="Smart Insurance AI")

@app.get("/health")
def health():
    return {"status": "ok"}
