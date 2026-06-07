"""Rule-based sight-reading exercise generator.

Ported and modernized from the original Python 2 ``MusicGenerator``. The core
idea is preserved: each measure picks a random diatonic chord root, then fills
the bar with notes whose scale degrees are sampled with a bias toward the
chord tones (root / third / fifth), at a rhythmic complexity set by difficulty.

Output is a :class:`music21.stream.Score`, which can be exported to MusicXML
for the frontend (see :mod:`musicreader.musicxml`).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from music21 import clef as m21clef
from music21 import key as m21key
from music21 import meter, note, stream, tempo
from music21.pitch import Pitch
from music21.scale import MajorScale

from .model import CHORD_TONE_WEIGHTS, CLEF_RANGE, Clef, Difficulty, get_difficulty

# Supported major keys, mapped to their tonic pitch name.
SUPPORTED_KEYS: tuple[str, ...] = ("C", "G", "D", "A", "E", "F", "Bb")

MAX_MEASURES = 64
_BEATS_PER_MEASURE = 4.0  # 4/4 only, for now


@dataclass
class GenerationParams:
    """Parameters controlling a single generated exercise."""

    difficulty: str = "EASY"
    key: str = "C"
    clef: Clef = Clef.TREBLE
    measures: int = 8
    polyphonic: bool = False
    tempo_bpm: int = 90
    seed: int | None = None

    def normalized(self) -> "GenerationParams":
        """Return a copy with values clamped to safe, supported ranges."""
        key = self.key if self.key in SUPPORTED_KEYS else "C"
        clef = self.clef if isinstance(self.clef, Clef) else Clef(str(self.clef))
        measures = max(1, min(int(self.measures), MAX_MEASURES))
        tempo_bpm = max(20, min(int(self.tempo_bpm), 300))
        return GenerationParams(
            difficulty=self.difficulty,
            key=key,
            clef=clef,
            measures=measures,
            polyphonic=self.polyphonic,
            tempo_bpm=tempo_bpm,
            seed=self.seed,
        )


def _softmax(weights: tuple[float, ...]) -> list[float]:
    exps = [math.exp(w) for w in weights]
    total = sum(exps)
    return [e / total for e in exps]


_DEGREE_PROBS = _softmax(CHORD_TONE_WEIGHTS)


def _measure_durations(diff: Difficulty, rng: random.Random) -> list[float]:
    """Build a list of quarter-length durations that exactly fill one 4/4 bar."""
    remaining = _BEATS_PER_MEASURE
    out: list[float] = []
    while remaining > 1e-9:
        fitting = [
            4.0 / d for d in diff.rhythm_denominators if 4.0 / d <= remaining + 1e-9
        ]
        ql = rng.choice(fitting)
        # On easier levels, eighths only appear as adjacent pairs.
        if ql == 0.5 and diff.pair_eighths:
            if remaining >= 1.0:
                out.extend([0.5, 0.5])
                remaining -= 1.0
                continue
            non_eighth = [c for c in fitting if c != 0.5]
            ql = rng.choice(non_eighth) if non_eighth else 0.5
        out.append(ql)
        remaining -= ql
    return out


class _PitchPool:
    """Diatonic pitches of a key within a clef's range, indexed by scale degree."""

    def __init__(self, key: str, clef: Clef):
        low, high = CLEF_RANGE[clef]
        self.scale = MajorScale(key.replace("b", "-"))  # music21 uses '-' for flat
        pitches = self.scale.getPitches(low, high)
        self.by_degree: dict[int, list[Pitch]] = {}
        for p in pitches:
            degree = self.scale.getScaleDegreeFromPitch(p)
            if degree is not None:
                self.by_degree.setdefault(degree, []).append(p)
        # Fallback so we never fail to place a note.
        self.all = pitches

    def pick(self, degree: int, near: Pitch | None) -> Pitch:
        candidates = self.by_degree.get(degree) or self.all
        if near is None:
            return candidates[len(candidates) // 2]
        return min(candidates, key=lambda p: abs(p.midi - near.midi))

    def third_above(self, base: Pitch) -> Pitch | None:
        """The diatonic third above ``base``, if it exists within range."""
        base_degree = self.scale.getScaleDegreeFromPitch(base)
        if base_degree is None:
            return None
        target = (base_degree - 1 + 2) % 7 + 1
        candidates = [p for p in self.by_degree.get(target, []) if p.midi > base.midi]
        return min(candidates, key=lambda p: p.midi) if candidates else None


def generate_score(params: GenerationParams) -> stream.Score:
    """Generate a sight-reading exercise as a music21 Score."""
    params = params.normalized()
    rng = random.Random(params.seed)
    diff = get_difficulty(params.difficulty)
    pool = _PitchPool(params.key, params.clef)

    part = stream.Part()
    part.append(
        m21clef.TrebleClef() if params.clef is Clef.TREBLE else m21clef.BassClef()
    )
    part.append(m21key.Key(params.key.replace("b", "-")))
    part.append(meter.TimeSignature("4/4"))
    part.append(tempo.MetronomeMark(number=params.tempo_bpm))

    prev: Pitch | None = None
    for _ in range(params.measures):
        measure = stream.Measure()
        chord_root = rng.randint(1, 7)
        for ql in _measure_durations(diff, rng):
            if rng.randint(1, diff.rest_chance) == 1:
                measure.append(note.Rest(quarterLength=ql))
                continue
            note_index = rng.choices(range(7), weights=_DEGREE_PROBS, k=1)[0]
            degree = (chord_root - 1 + note_index) % 7 + 1
            p = pool.pick(degree, prev)
            third = pool.third_above(p) if params.polyphonic else None
            if third is not None and rng.randint(0, 3) == 2:
                from music21 import chord as m21chord

                measure.append(m21chord.Chord([p, third], quarterLength=ql))
            else:
                measure.append(note.Note(p, quarterLength=ql))
            prev = p
        part.append(measure)

    score = stream.Score()
    score.append(part)
    score.metadata = _metadata(params)
    return score


def _metadata(params: GenerationParams):
    from music21 import metadata as m21meta

    md = m21meta.Metadata()
    md.title = f"Sight Reading — {params.difficulty.title()} in {params.key}"
    md.composer = "MusicReader"
    return md
