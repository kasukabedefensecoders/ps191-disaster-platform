from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from .auth.router import router as auth_router
from .routers.change_detection import router as change_detection_router
from .routers.dashboard import router as dashboard_router
from .routers.demo import router as demo_router
from .routers.escorts import router as escorts_router
from .routers.forecasts import router as forecasts_router
from .routers.handoffs import router as handoffs_router
from .routers.households import router as households_router
from .routers.incident_outcomes import router as incident_outcomes_router
from .routers.relocations import router as relocations_router
from .routers.routes import router as routes_router
from .routers.shelters import router as shelters_router
from .routers.surveys import router as surveys_router
from .routers.vehicles import router as vehicles_router
from .routers.zones import router as zones_router

app = FastAPI(title="PS191 — Hazard Red-Zone & Relocation Platform")

# Rule 8 (low-bandwidth by default): assume a satellite-backed link, gzip
# every response, not just the dashboard summary endpoint.
app.add_middleware(GZipMiddleware, minimum_size=500)

# Dev-only: lets the Vite dev server (localhost:5173) call this API
# (localhost:8000) from the browser. Revisit before any real deployment —
# this is not meant to describe a production origin policy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",  # frontend-field (Phase 9) dev server
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(zones_router)
app.include_router(shelters_router)
app.include_router(households_router)
app.include_router(vehicles_router)
app.include_router(escorts_router)
app.include_router(relocations_router)
app.include_router(routes_router)
app.include_router(dashboard_router)
app.include_router(surveys_router)
app.include_router(forecasts_router)
app.include_router(change_detection_router)
app.include_router(handoffs_router)
app.include_router(incident_outcomes_router)
app.include_router(demo_router)


@app.get("/health")
def health():
    return {"status": "ok"}
