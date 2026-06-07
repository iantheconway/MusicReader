"""Rule-based sight-reading exercise generator.

Builds a :class:`music21.stream.Score` from a :class:`GenerationConfig`. The core
idea is preserved from the original: each measure picks a random diatonic chord
root, then fills the bar (via the :mod:`musicreader.rhythm` engine) with notes
whose scale degrees are sampled with a bias toward the chord tones.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace

from music21 import clef as m21clef
from music21 import key as m21key
from music21 import meter, note, stream, tempo
from music21.pitch import Pitch
from music21.scale import ConcreteScale, HarmonicMinorScale, MajorScale, MinorScale

from .model import (
    CHORD_TONE_WEIGHTS,
    CLEF_RANGE,
    SUPPORTED_KEYS,
    Clef,
    GenerationConfig,
    get_preset,
    parse_key,
)
from .rhythm import RhythmValue, UnfillableMeasureError, fill_measure, resolve

__all__ = ["GenerationParams", "GenerationConfig", "SUPPORTED_KEYS", "generate_score"]


@dataclass
class GenerationParams:
    """Legacy flat parameters, kept as a thin adapter over GenerationConfig.

    The difficulty name selects a preset; the remaining fields override it.
    """

    difficulty: str = "EASY"
    key: str = "C"
    clef: Clef = Clef.TREBLE
    measures: int = 16
    polyphonic: bool = False
    tempo_bpm: int = 90
    seed: int | None = None

    def to_config(self) -> GenerationConfig:
        return replace(
            get_preset(self.difficulty),
            keys=[self.key],
            clef=self.clef,
            measures=self.measures,
            polyphonic=self.polyphonic,
            tempo_bpm=self.tempo_bpm,
            seed=self.seed,
        )


def _softmax(weights: tuple[float, ...]) -> list[float]:
    exps = [math.exp(w) for w in weights]
    total = sum(exps)
    return [e / total for e in exps]


_DEGREE_PROBS = _softmax(CHORD_TONE_WEIGHTS)


def _build_scale(tonic: str, quality: str) -> ConcreteScale:
    """Build the music21 scale for a key quality (major / minor / harmonic)."""
    if quality == "major":
        return MajorScale(tonic)
    if quality == "harmonic":
        return HarmonicMinorScale(tonic)
    return MinorScale(tonic)


class _PitchPool:
    """Diatonic pitches of a scale within a clef's range, indexed by scale degree."""

    def __init__(self, scale: ConcreteScale, clef: Clef):
        low, high = CLEF_RANGE[clef]
        self.scale = scale
        pitches = self.scale.getPitches(low, high)
        self.by_degree: dict[int, list[Pitch]] = {}
        for p in pitches:
            degree = self.scale.getScaleDegreeFromPitch(p)
            if degree is not None:
                self.by_degree.setdefault(degree, []).append(p)
        self.all = pitches

    def pick(self, degree: int, near: Pitch | None) -> Pitch:
        candidates = self.by_degree.get(degree) or self.all
        if near is None:
            return candidates[len(candidates) // 2]
        return min(candidates, key=lambda p: abs(p.midi - near.midi))

    def third_above(self, base: Pitch) -> Pitch | None:
        base_degree = self.scale.getScaleDegreeFromPitch(base)
        if base_degree is None:
            return None
        target = (base_degree - 1 + 2) % 7 + 1
        candidates = [p for p in self.by_degree.get(target, []) if p.midi > base.midi]
        return min(candidates, key=lambda p: p.midi) if candidates else None


def generate_score(config: GenerationConfig | GenerationParams) -> stream.Score:
    """Generate a sight-reading exercise as a music21 Score."""
    if isinstance(config, GenerationParams):
        config = config.to_config()
    config = config.normalized()
    config.validate()

    rng = random.Random(config.seed)
    key = rng.choice(config.keys)
    tonic, quality = parse_key(key)
    pool = _PitchPool(_build_scale(tonic, quality), config.clef)
    fill_values = resolve(config.fill_values)
    note_ids = set(config.rhythm_values)
    rest_ids = set(config.rest_values) if config.rests.enabled else set()
    measure_len = config.measure_quarter_length

    part = stream.Part()
    part.append(
        m21clef.TrebleClef() if config.clef is Clef.TREBLE else m21clef.BassClef()
    )
    part.append(m21key.Key(tonic, "minor" if quality != "major" else "major"))
    part.append(meter.TimeSignature(config.time_signature))
    part.append(tempo.MetronomeMark(number=config.tempo_bpm))

    prev: Pitch | None = None
    for _ in range(config.measures):
        measure = stream.Measure()
        chord_root = rng.randint(1, 7)
        for token in _fill_bar(measure_len, fill_values, config, rng):
            prev = _emit_token(
                measure, token, config, note_ids, rest_ids, pool, chord_root, prev, rng
            )
        part.append(measure)

    _finalize(part)
    score = stream.Score()
    score.append(part)
    score.metadata = _metadata(config, key)
    return score


def _fill_bar(
    measure_len, values, config: GenerationConfig, rng: random.Random
) -> list[RhythmValue]:
    """Fill a bar, honoring the no-syncopation rule when possible.

    If the rhythm set can't fill the bar without syncopation, fall back to
    allowing it for this bar rather than failing (rare; keeps generation robust).
    """
    if config.syncopation:
        return fill_measure(measure_len, values, rng)
    try:
        return fill_measure(
            measure_len,
            values,
            rng,
            beat_length=config.beat_quarter_length,
            allow_syncopation=False,
        )
    except UnfillableMeasureError:
        return fill_measure(measure_len, values, rng)


def _choose_pitch(
    pool: _PitchPool,
    chord_root: int,
    prev: Pitch | None,
    max_interval: int | None,
    rng: random.Random,
) -> Pitch:
    """Sample a chord-tone-weighted pitch, preferring leaps within max_interval.

    Best-effort: if no sampled degree lands within the cap (e.g. near the edge of
    the staff range), the smallest available leap is used.
    """
    best: Pitch | None = None
    best_leap = 0
    for _ in range(8):
        note_index = rng.choices(range(7), weights=_DEGREE_PROBS, k=1)[0]
        degree = (chord_root - 1 + note_index) % 7 + 1
        pitch = pool.pick(degree, prev)
        if prev is None or max_interval is None:
            return pitch
        leap = abs(pitch.midi - prev.midi)
        if leap <= max_interval:
            return pitch
        if best is None or leap < best_leap:
            best, best_leap = pitch, leap
    return best if best is not None else pitch


def _emit_token(
    measure: stream.Measure,
    token: RhythmValue,
    config: GenerationConfig,
    note_ids: set[str],
    rest_ids: set[str],
    pool: _PitchPool,
    chord_root: int,
    prev: Pitch | None,
    rng: random.Random,
) -> Pitch | None:
    """Append one rhythm token (1 note, or a tuplet group) to the measure.

    A slot becomes a rest when its duration is rest-only, or when it is valid as
    both and the rest coin-flip (density) lands; otherwise it's a pitched note.
    """
    can_note = token.id in note_ids
    can_rest = token.id in rest_ids
    for _ in range(token.group_size):
        ql = token.quarter_length
        if can_rest and (not can_note or rng.random() < config.rests.density):
            measure.append(note.Rest(quarterLength=ql))
            continue
        pitch = _choose_pitch(pool, chord_root, prev, config.max_interval, rng)
        third = pool.third_above(pitch) if config.polyphonic else None
        if third is not None and rng.randint(0, 3) == 2:
            from music21 import chord as m21chord

            measure.append(m21chord.Chord([pitch, third], quarterLength=ql))
        else:
            measure.append(note.Note(pitch, quarterLength=ql))
        prev = pitch
    return prev


def _finalize(part: stream.Part) -> None:
    """Add accidentals, beams, and tuplet brackets; best-effort so generation
    never fails on notation cleanup (e.g. the raised 7th in harmonic minor)."""
    for method in ("makeAccidentals", "makeBeams", "makeTupletBrackets"):
        try:
            getattr(part, method)(inPlace=True)
        except Exception:
            pass


def _metadata(config: GenerationConfig, key: str):
    from music21 import metadata as m21meta

    md = m21meta.Metadata()
    label = config.name or "Custom"
    md.title = f"Sight Reading — {label} in {key}"
    md.composer = "MusicReader"
    return md
