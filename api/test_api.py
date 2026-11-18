from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

GOOD = {
    "name": "Stripe",
    "entity_type": "company",
    "meeting_time": "2026-11-20T15:00:00Z",
    "meeting_type": "sales",
}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_generate_source_ids_exist():
    r = client.post("/generate", json=GOOD)
    assert r.status_code == 200
    data = r.json()

    valid_ids = {s["id"] for s in data["sources"]}
    used_ids = set(data["snapshot_source_ids"])
    for item in data["key_developments"] + data["talking_points"] + data["risks"]:
        used_ids.update(item["source_ids"])

    assert used_ids <= valid_ids, f"Unknown source ids: {used_ids - valid_ids}"


def test_generate_bad_time_gives_clean_error():
    r = client.post("/generate", json={**GOOD, "meeting_time": "tomorrow"})
    assert r.status_code == 400
    assert "error" in r.json()