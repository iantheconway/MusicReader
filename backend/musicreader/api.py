"""FastAPI app exposing the generator as a MusicXML endpoint."""

from __future__ import annotations

from fastapi import FastAPI, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from .generator import SUPPORTED_KEYS, GenerationParams, generate_score
from .model import Clef, DIFFICULTIES
from .musicxml import score_to_musicxml

app = FastAPI(title="MusicReader API", version="0.1.0")

# The frontend runs on a separate dev-server origin (Vite). Allow it in dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/options")
def options() -> dict:
    """Enumerate the choices the frontend can offer."""
    return {
        "difficulties": list(DIFFICULTIES.keys()),
        "keys": list(SUPPORTED_KEYS),
        "clefs": [c.value for c in Clef],
    }


@app.get("/api/generate")
def generate(
    difficulty: str = Query("EASY"),
    key: str = Query("C"),
    clef: Clef = Query(Clef.TREBLE),
    measures: int = Query(8, ge=1, le=64),
    polyphonic: bool = Query(False),
    tempo: int = Query(90, ge=20, le=300),
    seed: int | None = Query(None),
) -> Response:
    """Generate an exercise and return it as MusicXML."""
    params = GenerationParams(
        difficulty=difficulty,
        key=key,
        clef=clef,
        measures=measures,
        polyphonic=polyphonic,
        tempo_bpm=tempo,
        seed=seed,
    )
    xml = score_to_musicxml(generate_score(params))
    return Response(content=xml, media_type="application/vnd.recordare.musicxml+xml")
