"""Tests for GenerationConfig-driven generation (meters, tuplets, rests, validation)."""

import pytest
from fractions import Fraction
from music21 import stream

from musicreader.generator import GenerationParams, generate_score
from musicreader.model import Clef, ConfigError, GenerationConfig, RestConfig, get_preset
from musicreader.musicxml import score_to_musicxml


def measure_lengths(score: stream.Score) -> list[Fraction]:
    part = score.parts[0]
    return [
        Fraction(m.duration.quarterLength)
        for m in part.getElementsByClass(stream.Measure)
    ]


@pytest.mark.parametrize(
    "num,den,expected",
    [(4, 4, 4), (3, 4, 3), (2, 4, 2), (6, 8, 3), (9, 8, Fraction(9, 2)),
     (5, 4, 5), (7, 8, Fraction(7, 2))],
)
def test_meters_produce_full_bars(num, den, expected):
    cfg = GenerationConfig(
        numerator=num,
        denominator=den,
        rhythm_values=["quarter", "eighth", "sixteenth"],
        measures=4,
        seed=1,
    )
    lengths = measure_lengths(generate_score(cfg))
    assert lengths == [Fraction(expected)] * 4


def test_triplets_export_as_tuplets():
    cfg = GenerationConfig(rhythm_values=["eighth-triplet"], measures=2, seed=2)
    xml = score_to_musicxml(generate_score(cfg))
    assert "<time-modification>" in xml
    assert "<actual-notes>3</actual-notes>" in xml


def test_dotted_values_fill_three_four():
    cfg = GenerationConfig(
        numerator=3, denominator=4, rhythm_values=["dotted-half"], measures=2, seed=3
    )
    assert measure_lengths(generate_score(cfg)) == [Fraction(3), Fraction(3)]


def test_rests_can_be_forced():
    cfg = GenerationConfig(
        rhythm_values=["quarter"],
        rests=RestConfig(enabled=True, density=1.0),
        measures=2,
        seed=4,
    )
    xml = score_to_musicxml(generate_score(cfg))
    assert "<rest" in xml


def test_no_rests_when_disabled():
    cfg = GenerationConfig(
        rhythm_values=["quarter"],
        rests=RestConfig(enabled=False, density=1.0),
        measures=2,
        seed=5,
    )
    assert "<rest" not in score_to_musicxml(generate_score(cfg))


def test_unfillable_config_raises():
    cfg = GenerationConfig(numerator=3, denominator=4, rhythm_values=["half"])
    with pytest.raises(ConfigError):
        generate_score(cfg)


def test_empty_selections_raise():
    with pytest.raises(ConfigError):
        generate_score(GenerationConfig(rhythm_values=[]))
    with pytest.raises(ConfigError):
        generate_score(GenerationConfig(keys=[]))


def test_params_adapter_uses_preset_and_overrides():
    cfg = GenerationParams(
        difficulty="HARD", key="D", clef=Clef.BASS, measures=3, tempo_bpm=120
    ).to_config()
    assert cfg.keys == ["D"]
    assert cfg.clef is Clef.BASS
    assert cfg.measures == 3
    assert cfg.tempo_bpm == 120
    # Inherited from the HARD preset:
    assert cfg.rhythm_values == get_preset("HARD").rhythm_values
    assert cfg.syncopation is True
