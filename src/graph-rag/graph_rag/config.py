"""Build configuration. Every build writes its resolved config next to the database."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
KB_DIR = REPO_ROOT / "kb"
ARTIFACTS = REPO_ROOT / "artifacts" / "graph"


@dataclass(slots=True)
class GraphConfig:
    build_id: str = "dev"
    # D2: scope to the companies the eval set touches, all of their years.
    dataset_id: str = "gw1000"
    label_source: str = "llm_pre"
    scope: str = "eval"  # eval = companies the eval set touches (D2); all = every kept report
    years: tuple[int, int] = (2020, 2025)
    # M1 aspect handling: normalised exact match only. Clustering is M2.
    min_surface_chars: int = 10
    min_surface_tokens: int = 2
    max_string_matches_per_company_year: int = 3
    seed: int = 20260912

    extra: dict = field(default_factory=dict)

    @property
    def out_dir(self) -> Path:
        return ARTIFACTS / self.build_id

    @property
    def db_path(self) -> Path:
        return self.out_dir / "graph.duckdb"

    def hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, default=str).encode()
        return hashlib.sha256(payload).hexdigest()[:12]

    @classmethod
    def load(cls, path: str | Path | None = None, **overrides) -> GraphConfig:
        data: dict = {}
        if path and Path(path).exists():
            data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        if "years" in data:
            data["years"] = tuple(data["years"])
        data.update({k: v for k, v in overrides.items() if v is not None})
        known = {f for f in cls.__dataclass_fields__}
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(**{k: v for k, v in data.items() if k in known}, extra=extra)
