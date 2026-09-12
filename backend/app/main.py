from fastapi import FastAPI

app = FastAPI(title="PS191 — Hazard Red-Zone & Relocation Platform")


@app.get("/health")
def health():
    return {"status": "ok"}
