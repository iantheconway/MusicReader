"""Tests for the FastAPI endpoints."""

from fastapi.testclient import TestClient

from musicreader.api import app

client = TestClient(app)


def test_options_lists_keys_rhythms_intervals():
    data = client.get("/api/options").json()
    key_ids = {k["id"] for k in data["keys"]}
    assert {"C", "Am", "Ahm", "F#hm"} <= key_ids  # major, minor, harmonic minor
    assert {k["group"] for k in data["keys"]} == {"Major", "Minor", "Harmonic minor"}
    assert any(r["id"] == "eighth-triplet" for r in data["rhythmValues"])
    assert any(i["semitones"] == 12 for i in data["intervals"])


def test_presets_endpoint():
    data = client.get("/api/presets").json()
    assert set(data) == {"EASY", "MEDIUM", "HARD"}
    assert data["HARD"]["syncopation"] is True


def test_post_generate_returns_musicxml():
    body = {
        "numerator": 6,
        "denominator": 8,
        "keys": ["Em"],
        "rhythm_values": ["eighth", "quarter"],
        "measures": 3,
        "seed": 5,
    }
    res = client.post("/api/generate", json=body)
    assert res.status_code == 200
    assert "vnd.recordare.musicxml" in res.headers["content-type"]
    assert "<score-partwise" in res.text


def test_post_generate_rejects_unfillable_config():
    body = {"numerator": 3, "denominator": 4, "rhythm_values": ["half"]}
    res = client.post("/api/generate", json=body)
    assert res.status_code == 400
    assert "fill" in res.json()["detail"].lower()


def test_get_generate_still_works():
    res = client.get("/api/generate", params={"difficulty": "HARD", "seed": 1})
    assert res.status_code == 200
    assert "<score-partwise" in res.text
