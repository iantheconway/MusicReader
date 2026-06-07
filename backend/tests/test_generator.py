"""Smoke tests for the generator and MusicXML export."""

import pytest
from music21 import stream

from musicreader.generator import GenerationParams, generate_score
from musicreader.model import Clef
from musicreader.musicxml import score_to_musicxml


def _total_quarter_lengths(score: stream.Score) -> list[float]:
    part = score.parts[0]
    return [round(m.duration.quarterLength, 6) for m in part.getElementsByClass(stream.Measure)]


@pytest.mark.parametrize("difficulty", ["EASY", "MEDIUM", "HARD"])
@pytest.mark.parametrize("clef", [Clef.TREBLE, Clef.BASS])
def test_measures_are_full_bars(difficulty, clef):
    score = generate_score(
        GenerationParams(difficulty=difficulty, clef=clef, measures=6, seed=1)
    )
    lengths = _total_quarter_lengths(score)
    assert len(lengths) == 6
    assert all(length == 4.0 for length in lengths), lengths


def _note_signature(score: stream.Score):
    """Pitches + durations of every note/chord/rest, ignoring volatile XML ids."""
    return [
        (getattr(n, "fullName", n.classes[0]), float(n.quarterLength))
        for n in score.recurse().notesAndRests
    ]


def test_seed_is_deterministic():
    params = GenerationParams(measures=8, seed=42)
    assert _note_signature(generate_score(params)) == _note_signature(
        generate_score(params)
    )


def test_exports_valid_musicxml():
    xml = score_to_musicxml(generate_score(GenerationParams(measures=4, seed=7)))
    assert xml.lstrip().startswith("<?xml")
    assert "<score-partwise" in xml


def test_keys_and_polyphony():
    for key in ("C", "G", "D", "A", "Bb"):
        score = generate_score(
            GenerationParams(key=key, polyphonic=True, measures=4, seed=3)
        )
        assert score_to_musicxml(score)
