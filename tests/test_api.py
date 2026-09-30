"""The API must stay a thin adapter: it boots with zero systems configured and reports capabilities."""

from fastapi.testclient import TestClient
from gw_common.api.app import create_app


def test_healthz_and_systems():
    client = TestClient(create_app(["majority"]))
    health = client.get("/healthz").json()
    assert health["status"] == "ok"
    assert health["systems"] == ["majority"]

    systems = client.get("/systems").json()
    assert systems[0]["name"] == "majority"
    assert systems[0]["capabilities"] == {"retrieve": False, "classify": True, "trajectory": False}


def test_classify_roundtrip_and_501():
    client = TestClient(create_app(["majority", "agentic-graph-rag"]))
    resp = client.post("/classify", json={"text": "We installed solar panels.", "system": "majority"})
    assert resp.status_code == 200
    assert resp.json()["label"] in {"implemented", "planning", "indeterminate", "none"}

    # a system that cannot classify says so rather than pretending (the agentic arm is still a stub)
    assert client.post("/classify", json={"text": "x", "system": "agentic-graph-rag"}).status_code == 501
    assert client.post("/classify", json={"text": "x", "system": "nope"}).status_code == 404
