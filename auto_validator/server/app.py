from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auto_validator.server.routers import webhooks, reports

app = FastAPI(
    title="Auto-Validator",
    description="Autonomous business idea validation agent — webhook listener",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router)
app.include_router(reports.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
