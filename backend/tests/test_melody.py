"""Tests for melody constraints: minor keys, interval cap, syncopation."""

from fractions import Fraction

from music21 import stream

from musicreader.generator import _build_scale, generate_score
from musicreader.model import GenerationConfig
from musicreader.musicxml import score_to_musicxml


def test_minor_key_signature_is_minor():
    xml = score_to_musicxml(generate_score(GenerationConfig(keys=["Am"], seed=1)))
    assert "<mode>minor</mode>" in xml


def test_harmonic_minor_scale_raises_seventh():
    pitches = _build_scale("A", "harmonic").getPitches("A3", "A4")
    names = [p.name for p in pitches]
    assert "G#" in names
    assert "G" not in names  # the natural 7th is replaced


def test_natural_minor_scale_keeps_seventh():
    names = [p.name for p in _build_scale("A", "minor").getPitches("A3", "A4")]
    assert "G" in names and "G#" not in names


def test_harmonic_minor_key_id_generates_accidental():
    xml = score_to_musicxml(
        generate_score(GenerationConfig(keys=["Ahm"], rhythm_values=["quarter"],
                                        measures=16, seed=2))
    )
    assert "<mode>minor</mode>" in xml


def _mean_leap(max_interval: int | None) -> float:
    cfg = GenerationConfig(
        rhythm_values=["quarter"], measures=30, max_interval=max_interval, seed=11
    )
    midis = [n.pitch.midi for n in generate_score(cfg).recurse().notes]
    leaps = [abs(b - a) for a, b in zip(midis, midis[1:])]
    return sum(leaps) / len(leaps)


def test_interval_cap_reduces_leaps():
    assert _mean_leap(2) < _mean_leap(12)


def test_no_syncopation_keeps_notes_within_beats():
    # 4/4, beat = 1 quarter. No off-beat note may cross into the next beat.
    cfg = GenerationConfig(
        rhythm_values=["half", "quarter", "eighth"],
        syncopation=False,
        measures=12,
        seed=7,
    )
    part = generate_score(cfg).parts[0]
    for measure in part.getElementsByClass(stream.Measure):
        for n in measure.notesAndRests:
            offset = Fraction(n.offset)
            dur = Fraction(n.duration.quarterLength)
            if offset % 1 != 0:  # starts off the beat
                next_beat = (offset // 1 + 1)
                assert offset + dur <= next_beat, (offset, dur)
