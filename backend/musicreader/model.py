"""Difficulty profiles and musical constants for the generator.

The data model for an actual piece of music is just a music21 ``Score`` (built in
:mod:`musicreader.generator`); this module only holds the tunable knobs that
describe *how* a piece is generated at a given difficulty, plus the clef/range
information needed to place notes comfortably on the staff.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Clef(str, Enum):
    """Supported clefs / staff ranges."""

    TREBLE = "treble"
    BASS = "bass"


# Comfortable written range per clef, as (low, high) scientific-pitch names.
# Treble roughly matches the original guitar range (E3..D5); bass sits an
# octave-and-a-bit lower so the same algorithm reads well in bass clef.
CLEF_RANGE: dict[Clef, tuple[str, str]] = {
    Clef.TREBLE: ("E3", "D5"),
    Clef.BASS: ("E2", "D4"),
}


@dataclass(frozen=True)
class Difficulty:
    """Tunable parameters that define a difficulty level.

    Attributes:
        name: Human-readable level name.
        rhythm_denominators: Allowed note values as denominators of a whole
            note (1=whole, 2=half, 4=quarter, 8=eighth, 16=sixteenth).
        pair_eighths: If True, eighth notes are only emitted in adjacent pairs
            (keeps easier levels free of off-beat single eighths).
        allow_syncopation: If True, notes may start on off-beats.
        rest_chance: A rest is emitted with probability ``1 / rest_chance``.
    """

    name: str
    rhythm_denominators: tuple[int, ...]
    pair_eighths: bool
    allow_syncopation: bool
    rest_chance: int


# Chord-tone-weighted melodic preference. Index i is the weight for the scale
# degree i steps above the measure's chord root (0=root, 2=third, 4=fifth get
# the strong weights). Sampled via softmax in the generator.
CHORD_TONE_WEIGHTS: tuple[float, ...] = (1.6, 0.3, 1.5, 0.6, 1.4, 0.4, 0.2)


DIFFICULTIES: dict[str, Difficulty] = {
    "EASY": Difficulty(
        name="EASY",
        rhythm_denominators=(1, 2, 4),
        pair_eighths=True,
        allow_syncopation=False,
        rest_chance=4,
    ),
    "MEDIUM": Difficulty(
        name="MEDIUM",
        rhythm_denominators=(1, 2, 4, 8),
        pair_eighths=True,
        allow_syncopation=False,
        rest_chance=4,
    ),
    "HARD": Difficulty(
        name="HARD",
        rhythm_denominators=(1, 2, 4, 8, 16),
        pair_eighths=False,
        allow_syncopation=True,
        rest_chance=4,
    ),
}


def get_difficulty(level: str) -> Difficulty:
    """Look up a difficulty by name, defaulting to EASY for unknown values."""
    return DIFFICULTIES.get((level or "").upper(), DIFFICULTIES["EASY"])
