"""Tests for the measure-filling rhythm engine."""

import random
from fractions import Fraction

import pytest

from musicreader.rhythm import (
    CATALOG,
    UnfillableMeasureError,
    can_fill,
    fill_measure,
    resolve,
)

F = Fraction


def total(values) -> Fraction:
    return sum((v.total_quarter_length for v in values), F(0))


# Common meters as quarter-length totals: 4/4=4, 3/4=3, 6/8=3, 5/4=5, 7/8=3.5.
METERS = {
    "4/4": F(4),
    "3/4": F(3),
    "2/4": F(2),
    "6/8": F(3),
    "9/8": F(9, 2),
    "5/4": F(5),
    "7/8": F(7, 2),
}


@pytest.mark.parametrize("length", METERS.values(), ids=list(METERS.keys()))
def test_fills_exactly_with_full_vocabulary(length):
    values = resolve(CATALOG.keys())
    rng = random.Random(0)
    for _ in range(50):
        filled = fill_measure(length, values, rng)
        assert total(filled) == length


def test_only_eighths_in_4_4():
    values = resolve(["eighth"])
    filled = fill_measure(F(4), values, random.Random(1))
    assert len(filled) == 8
    assert all(v.id == "eighth" for v in filled)
    assert total(filled) == F(4)


def test_triplets_keep_their_group_and_sum():
    values = resolve(["eighth-triplet"])
    filled = fill_measure(F(4), values, random.Random(2))
    # Eighth triplet = 1 quarter total, so a 4/4 bar needs four groups.
    assert len(filled) == 4
    assert all(v.tuplet == (3, 2) and v.group_size == 3 for v in filled)
    assert total(filled) == F(4)


def test_dotted_values_fill_three_four():
    # A dotted half exactly fills a 3/4 bar.
    filled = fill_measure(F(3), resolve(["dotted-half"]), random.Random(3))
    assert [v.id for v in filled] == ["dotted-half"]


def test_unfillable_raises():
    # Half notes cannot tile a 3/4 bar.
    with pytest.raises(UnfillableMeasureError):
        fill_measure(F(3), resolve(["half"]), random.Random(4))


def test_can_fill_matches_fill_measure():
    assert can_fill(F(4), resolve(["eighth"])) is True
    assert can_fill(F(3), resolve(["half"])) is False
    assert can_fill(F(3), resolve(["half", "quarter"])) is True
    assert can_fill(F(0), resolve(["quarter"])) is True
    assert can_fill(F(4), []) is False


def test_fill_is_deterministic_per_rng():
    values = resolve(["quarter", "eighth", "half", "eighth-triplet"])
    a = fill_measure(F(4), values, random.Random(99))
    b = fill_measure(F(4), values, random.Random(99))
    assert [v.id for v in a] == [v.id for v in b]
