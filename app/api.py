# app/api.py
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.pipeline import run_pipeline

app = FastAPI(title="Driftwatch", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/run")
def run(request: dict) -> JSONResponse:
    scenario = request.pop("scenario", None)
    scenario_dir = Path(scenario) if scenario else None
    if scenario_dir is not None and not scenario_dir.is_dir():
        return JSONResponse({"error": f"unknown scenario directory: {scenario_dir}"}, status_code=400)
    report, _ = run_pipeline(request, scenario_dir=scenario_dir)
    return JSONResponse(report.model_dump(by_alias=True))
