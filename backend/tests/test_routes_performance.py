import json
from pathlib import Path


def test_reset_performance(client, monkeypatch, tmp_path):
    p = tmp_path / "performance.json"
    p.write_text(json.dumps([{"speed_cpm": 300.0, "char_count": 50}]), encoding="utf-8")
    monkeypatch.setattr("backend.performance_store.PERFORMANCE_PATH", p)

    r = client.post("/api/performance/reset")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert not p.exists()


def test_reset_performance_no_file(client):
    r = client.post("/api/performance/reset")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
