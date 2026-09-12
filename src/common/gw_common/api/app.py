"""FastAPI factory. Routes are thin adapters over the same Protocols the eval harness uses."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from gw_common import registry
from gw_common.schemas import EvalItem, EvidenceCondition, EvidenceSpan, Label, Query

REPO_ROOT = Path(__file__).resolve().parents[4]
RUNS_DIR = REPO_ROOT / "artifacts" / "runs"
DEFAULT_TIMEOUT_S = 8.0


class ClassifyRequest(BaseModel):
    text: str
    system: str
    company: str | None = None
    year: int | None = None
    aspect: str | None = None
    condition: EvidenceCondition = EvidenceCondition.SENTENCE_ONLY


class ClassifyResponse(BaseModel):
    label: Label
    scores: dict[str, float] | None = None
    evidence: list[EvidenceSpan] = []
    latency_ms: float


class RetrieveRequest(BaseModel):
    query: str
    system: str
    company: str | None = None
    aspect: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    k: int = 10
    condition: EvidenceCondition = EvidenceCondition.CROSS_YEAR_RRF


def _system_or_404(name: str):
    try:
        return registry.load(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def create_app(system_names: list[str] | None = None) -> FastAPI:
    names = system_names or sorted(registry.available())
    app = FastAPI(title="Greenwash-RAG", version="0.1.0")
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:  # noqa: BLE001
        sha = "unknown"

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok", "git_sha": sha, "systems": names, "graph_build_id": None}

    @app.get("/systems")
    def systems() -> list[dict]:
        out = []
        for name in names:
            s = registry.load(name)
            out.append(
                {
                    "name": name,
                    "capabilities": {
                        "retrieve": s.retriever() is not None,
                        "classify": s.classifier() is not None,
                        "trajectory": s.trajectories() is not None,
                    },
                    "conditions": [c.value for c in s.supported_conditions()],
                }
            )
        return out

    @app.post("/classify", response_model=ClassifyResponse)
    def classify(req: ClassifyRequest) -> ClassifyResponse:
        system = _system_or_404(req.system)
        clf = system.classifier()
        if clf is None:
            raise HTTPException(status_code=501, detail=f"{req.system} cannot classify")
        item = EvalItem(
            item_id="adhoc",
            text=req.text,
            aspect=req.aspect,
            company=req.company or "unknown",
            year=req.year or 0,
        )
        evidence: dict[str, list[EvidenceSpan]] = {}
        retriever = system.retriever()
        if retriever is not None and req.condition is not EvidenceCondition.SENTENCE_ONLY:
            evidence["adhoc"] = retriever.retrieve(
                Query(text=req.text, company=req.company, aspect=req.aspect, condition=req.condition), k=5
            )
        t0 = time.perf_counter()
        pred = clf.classify([item], condition=req.condition, evidence=evidence or None)[0]
        return ClassifyResponse(
            label=pred.label,
            scores=pred.scores,
            evidence=evidence.get("adhoc", []),
            latency_ms=(time.perf_counter() - t0) * 1000,
        )

    @app.post("/retrieve")
    def retrieve(req: RetrieveRequest) -> dict:
        system = _system_or_404(req.system)
        retriever = system.retriever()
        if retriever is None:
            raise HTTPException(status_code=501, detail=f"{req.system} cannot retrieve")
        t0 = time.perf_counter()
        hits = retriever.retrieve(
            Query(
                text=req.query,
                company=req.company,
                aspect=req.aspect,
                year_from=req.year_from,
                year_to=req.year_to,
                condition=req.condition,
            ),
            k=req.k,
        )
        return {"hits": [h.model_dump() for h in hits], "latency_ms": (time.perf_counter() - t0) * 1000}

    @app.get("/trajectory")
    def trajectory(
        company: str, aspect: str, system: str, year_from: int = 2020, year_to: int = 2025
    ) -> dict:
        s = _system_or_404(system)
        builder = s.trajectories()
        if builder is None:
            raise HTTPException(status_code=501, detail=f"{system} has no trajectories")
        return builder.trajectory(company, aspect, range(year_from, year_to + 1)).model_dump()

    @app.get("/runs")
    def runs(limit: int = 20) -> list[dict]:
        out = []
        for d in sorted(RUNS_DIR.glob("*/metrics.json"), reverse=True)[:limit]:
            out.append(json.loads(d.read_text(encoding="utf-8")))
        return out

    for name in names:
        router: APIRouter | None = registry.load(name).router()
        if router is not None:
            app.include_router(router, prefix=f"/x/{name}", tags=[name])
    return app
