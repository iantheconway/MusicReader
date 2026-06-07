"""FastAPI app exposing the generator as a MusicXML endpoint."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .generator import GenerationParams, generate_score
from .model import (
    INTERVAL_OPTIONS,
    KEY_DEFS,
    PRESETS,
    Clef,
    ConfigError,
    GenerationConfig,
    RestConfig,
)
from .musicxml import score_to_musicxml
from .rhythm import CATALOG

app = FastAPI(title="MusicReader API", version="0.2.0")

# The frontend runs on a separate dev-server origin (Vite). Allow it in dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_MUSICXML = "application/vnd.recordare.musicxml+xml"


class RestBody(BaseModel):
    enabled: bool = False
    density: float = 0.0


class ConfigBody(BaseModel):
    """Request body mirroring GenerationConfig (snake_case, matches the frontend)."""

    name: str | None = None
    numerator: int = 4
    denominator: int = 4
    keys: list[str] = Field(default_factory=lambda: ["C"])
    clef: Clef = Clef.TREBLE
    measures: int = 16
    rhythm_values: list[str] = Field(
        default_factory=lambda: ["whole", "half", "quarter"]
    )
    rest_values: list[str] = Field(
        default_factory=lambda: ["whole", "half", "quarter"]
    )
    syncopation: bool = False
    max_interval: int | None = None
    rests: RestBody = Field(default_factory=RestBody)
    polyphonic: bool = False
    tempo_bpm: int = 90
    seed: int | None = None

    def to_config(self) -> GenerationConfig:
        return GenerationConfig(
            name=self.name,
            numerator=self.numerator,
            denominator=self.denominator,
            keys=self.keys,
            clef=self.clef,
            measures=self.measures,
            rhythm_values=self.rhythm_values,
            rest_values=self.rest_values,
            syncopation=self.syncopation,
            max_interval=self.max_interval,
            rests=RestConfig(enabled=self.rests.enabled, density=self.rests.density),
            polyphonic=self.polyphonic,
            tempo_bpm=self.tempo_bpm,
            seed=self.seed,
        )


def _render(config: GenerationConfig | GenerationParams) -> Response:
    try:
        xml = score_to_musicxml(generate_score(config))
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(content=xml, media_type=_MUSICXML)


@app.get("/api/options")
def options() -> dict:
    """Enumerate the choices the frontend can offer."""
    return {
        "difficulties": list(PRESETS.keys()),
        "keys": [{"id": k.id, "label": k.label, "group": k.group} for k in KEY_DEFS],
        "clefs": [c.value for c in Clef],
        "rhythmValues": [{"id": v.id, "label": v.label} for v in CATALOG.values()],
        "intervals": [{"semitones": s, "label": label} for s, label in INTERVAL_OPTIONS],
    }


@app.get("/api/presets")
def presets() -> dict:
    """Return the difficulty presets as full configs the frontend can load."""
    return {name: asdict(config) for name, config in PRESETS.items()}


@app.post("/api/generate")
def generate_from_config(body: ConfigBody) -> Response:
    """Generate an exercise from a full config and return it as MusicXML."""
    return _render(body.to_config())


@app.get("/api/generate")
def generate(
    difficulty: str = Query("EASY"),
    key: str = Query("C"),
    clef: Clef = Query(Clef.TREBLE),
    measures: int = Query(16, ge=1, le=64),
    polyphonic: bool = Query(False),
    tempo: int = Query(90, ge=20, le=300),
    seed: int | None = Query(None),
) -> Response:
    """Generate a preset-based exercise (quick links / back-compat)."""
    return _render(
        GenerationParams(
            difficulty=difficulty,
            key=key,
            clef=clef,
            measures=measures,
            polyphonic=polyphonic,
            tempo_bpm=tempo,
            seed=seed,
        )
    )
