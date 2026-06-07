"""Rhythm vocabulary and the measure-filling engine.

A :class:`RhythmValue` is a single selectable note value. Most are one note
(``group_size == 1``); tuplets are emitted as an indivisible group of notes
(e.g. an eighth-note triplet is three notes totalling one quarter). All
durations are exact :class:`fractions.Fraction` quarter-lengths so that filling
a bar is exact — no floating-point drift, and tuplet/normal values mix cleanly.

:func:`fill_measure` returns a random sequence of values whose total length is
*exactly* the measure length. :func:`can_fill` answers whether any such sequence
exists (used for config validation before we ever try to generate).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

F = Fraction


class UnfillableMeasureError(ValueError):
    """Raised when the allowed note values cannot exactly fill a measure."""


@dataclass(frozen=True)
class RhythmValue:
    """A selectable note value.

    Attributes:
        id: Stable identifier used in configs and the API.
        label: Human-readable name.
        quarter_length: Length of a *single* note of this value, in quarters.
        group_size: How many notes are emitted together (3 for triplets).
        tuplet: ``(actual, normal)`` ratio for tuplets, else ``None``
            (e.g. ``(3, 2)`` = three in the time of two).
    """

    id: str
    label: str
    quarter_length: Fraction
    group_size: int = 1
    tuplet: tuple[int, int] | None = None

    @property
    def total_quarter_length(self) -> Fraction:
        """Total length contributed by one placement of this value."""
        return self.quarter_length * self.group_size


# The full vocabulary, in a sensible display order.
_VALUES: tuple[RhythmValue, ...] = (
    RhythmValue("whole", "Whole", F(4)),
    RhythmValue("half", "Half", F(2)),
    RhythmValue("quarter", "Quarter", F(1)),
    RhythmValue("eighth", "Eighth", F(1, 2)),
    RhythmValue("sixteenth", "Sixteenth", F(1, 4)),
    RhythmValue("dotted-half", "Dotted half", F(3)),
    RhythmValue("dotted-quarter", "Dotted quarter", F(3, 2)),
    RhythmValue("dotted-eighth", "Dotted eighth", F(3, 4)),
    RhythmValue("eighth-triplet", "Eighth triplet", F(1, 3), 3, (3, 2)),
    RhythmValue("quarter-triplet", "Quarter triplet", F(2, 3), 3, (3, 2)),
    RhythmValue("sixteenth-triplet", "Sixteenth triplet", F(1, 6), 3, (3, 2)),
)

CATALOG: dict[str, RhythmValue] = {v.id: v for v in _VALUES}
ALL_IDS: tuple[str, ...] = tuple(CATALOG.keys())


def resolve(ids: Sequence[str]) -> list[RhythmValue]:
    """Map rhythm-value ids to :class:`RhythmValue` objects.

    Raises:
        KeyError: if any id is unknown.
    """
    return [CATALOG[i] for i in ids]


def can_fill(length: Fraction, values: Sequence[RhythmValue]) -> bool:
    """Whether some combination of ``values`` sums *exactly* to ``length``."""
    if length == 0:
        return True
    totals = {v.total_quarter_length for v in values if v.total_quarter_length <= length}
    if not totals:
        return False
    reachable: set[Fraction] = {F(0)}
    frontier = [F(0)]
    while frontier:
        current = frontier.pop()
        for step in totals:
            nxt = current + step
            if nxt == length:
                return True
            if nxt < length and nxt not in reachable:
                reachable.add(nxt)
                frontier.append(nxt)
    return False


def fill_measure(
    length: Fraction,
    values: Sequence[RhythmValue],
    rng: random.Random,
    beat_length: Fraction | None = None,
    allow_syncopation: bool = True,
) -> list[RhythmValue]:
    """Return a random sequence of ``values`` whose totals sum to ``length``.

    Uses randomized exhaustive backtracking, so it always finds a valid filling
    when one exists (and is reproducible for a given ``rng``).

    When ``allow_syncopation`` is False and ``beat_length`` is given, a note that
    starts off the beat may not cross the next beat boundary (the classic
    no-syncopation rule). Notes that start on a beat may span freely.

    Raises:
        UnfillableMeasureError: if no combination fills the measure exactly.
    """
    usable = [v for v in values if v.total_quarter_length <= length]
    result: list[RhythmValue] = []
    constrain = not allow_syncopation and beat_length

    def allowed_at(pos: Fraction, value: RhythmValue) -> bool:
        if not constrain or pos % beat_length == 0:
            return True
        next_boundary = (pos // beat_length + 1) * beat_length
        return pos + value.total_quarter_length <= next_boundary

    def backtrack(remaining: Fraction) -> bool:
        if remaining == 0:
            return True
        pos = length - remaining
        candidates = [
            v
            for v in usable
            if v.total_quarter_length <= remaining and allowed_at(pos, v)
        ]
        rng.shuffle(candidates)
        for value in candidates:
            result.append(value)
            if backtrack(remaining - value.total_quarter_length):
                return True
            result.pop()
        return False

    if not backtrack(length):
        raise UnfillableMeasureError(
            f"Cannot exactly fill {length} quarter-lengths with the selected values."
        )
    return result
