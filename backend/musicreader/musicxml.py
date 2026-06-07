"""Serialize a generated music21 Score to a MusicXML string."""

from __future__ import annotations

from music21 import stream
from music21.musicxml.m21ToXml import GeneralObjectExporter


def score_to_musicxml(score: stream.Score) -> str:
    """Return the MusicXML representation of ``score`` as a UTF-8 string."""
    return GeneralObjectExporter(score).parse().decode("utf-8")
