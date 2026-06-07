"""The generation config, difficulty presets, and validation.

``GenerationConfig`` is the single object that fully describes an exercise to
generate. It is intentionally plain/serializable so it can travel over the API
and be saved to localStorage on the frontend unchanged. Easy/Medium/Hard are
just presets that fill it in; the user can tweak any field afterward.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from fractions import Fraction

from .rhythm import CATALOG, can_fill, resolve


class Clef(str, Enum):
    """Supported clefs / staff ranges."""

    TREBLE = "treble"
    BASS = "bass"


# Comfortable written range per clef, as (low, high) scientific-pitch names.
CLEF_RANGE: dict[Clef, tuple[str, str]] = {
    Clef.TREBLE: ("E3", "D5"),
    Clef.BASS: ("E2", "D4"),
}

# Supported keys. Major ids are the tonic ("C", "Bb"); minor ids add an "m"
# suffix ("Am", "F#m"). The minors here are the relative minors of the majors.
MAJOR_KEYS: tuple[str, ...] = ("C", "G", "D", "A", "E", "F", "Bb")
MINOR_KEYS: tuple[str, ...] = ("Am", "Em", "Bm", "F#m", "C#m", "Dm", "Gm")
SUPPORTED_KEYS: tuple[str, ...] = MAJOR_KEYS + MINOR_KEYS


def parse_key(key_id: str) -> tuple[str, bool]:
    """Split a key id into (music21 tonic name, is_minor). 'Bbm' -> ('B-', True)."""
    is_minor = key_id.endswith("m")
    tonic = key_id[:-1] if is_minor else key_id
    return tonic.replace("b", "-"), is_minor


def key_label(key_id: str) -> str:
    """Human-readable key name, e.g. 'F#m' -> 'F# minor'."""
    is_minor = key_id.endswith("m")
    tonic = key_id[:-1] if is_minor else key_id
    return f"{tonic} {'minor' if is_minor else 'major'}"


# Melodic-leap caps offered in the UI, in semitones.
INTERVAL_OPTIONS: tuple[tuple[int, str], ...] = (
    (2, "2nd"),
    (4, "3rd"),
    (5, "4th"),
    (7, "5th"),
    (9, "6th"),
    (12, "Octave"),
)

# Chord-tone-weighted melodic preference: index i is the weight for the scale
# degree i steps above the measure's chord root (0=root, 2=third, 4=fifth strong).
CHORD_TONE_WEIGHTS: tuple[float, ...] = (1.6, 0.3, 1.5, 0.6, 1.4, 0.4, 0.2)

VALID_DENOMINATORS: frozenset[int] = frozenset({1, 2, 4, 8, 16})
MAX_MEASURES = 64
MAX_NUMERATOR = 32


class ConfigError(ValueError):
    """Raised when a GenerationConfig is musically/logically invalid."""


@dataclass
class RestConfig:
    """Whether rests are emitted, and how often (probability per note slot)."""

    enabled: bool = False
    density: float = 0.0


@dataclass
class GenerationConfig:
    """A complete, serializable description of an exercise to generate."""

    name: str | None = None
    numerator: int = 4
    denominator: int = 4
    keys: list[str] = field(default_factory=lambda: ["C"])
    clef: Clef = Clef.TREBLE
    measures: int = 8
    rhythm_values: list[str] = field(
        default_factory=lambda: ["whole", "half", "quarter"]
    )
    syncopation: bool = False
    max_interval: int | None = None  # semitone cap on melodic leaps
    rests: RestConfig = field(default_factory=RestConfig)
    polyphonic: bool = False
    harmonic_minor: bool = False  # raise the 7th in minor keys
    tempo_bpm: int = 90
    seed: int | None = None

    @property
    def measure_quarter_length(self) -> Fraction:
        """Length of one bar in quarter-notes, e.g. 6/8 -> 3."""
        return Fraction(self.numerator * 4, self.denominator)

    @property
    def beat_quarter_length(self) -> Fraction:
        """Length of one beat. Compound meters (x/8 with numerator%3==0) beat in
        dotted quarters; everything else beats in 4/denominator."""
        if self.denominator == 8 and self.numerator % 3 == 0:
            return Fraction(3, 2)
        return Fraction(4, self.denominator)

    @property
    def time_signature(self) -> str:
        return f"{self.numerator}/{self.denominator}"

    def normalized(self) -> "GenerationConfig":
        """Clamp numeric fields and coerce the clef; logical checks are in validate()."""
        clef = self.clef if isinstance(self.clef, Clef) else Clef(str(self.clef))
        density = min(1.0, max(0.0, float(self.rests.density)))
        return replace(
            self,
            clef=clef,
            measures=max(1, min(int(self.measures), MAX_MEASURES)),
            tempo_bpm=max(20, min(int(self.tempo_bpm), 300)),
            numerator=max(1, min(int(self.numerator), MAX_NUMERATOR)),
            rests=RestConfig(enabled=bool(self.rests.enabled), density=density),
        )

    def validate(self) -> None:
        """Raise :class:`ConfigError` if the config cannot produce valid music."""
        if self.denominator not in VALID_DENOMINATORS:
            raise ConfigError(
                f"Unsupported time-signature denominator: {self.denominator}"
            )
        if not self.keys:
            raise ConfigError("At least one key must be selected.")
        unknown_keys = [k for k in self.keys if k not in SUPPORTED_KEYS]
        if unknown_keys:
            raise ConfigError(f"Unsupported key(s): {', '.join(unknown_keys)}")
        if not self.rhythm_values:
            raise ConfigError("At least one rhythm value must be selected.")
        unknown_rhythms = [r for r in self.rhythm_values if r not in CATALOG]
        if unknown_rhythms:
            raise ConfigError(f"Unknown rhythm value(s): {', '.join(unknown_rhythms)}")
        if not can_fill(self.measure_quarter_length, resolve(self.rhythm_values)):
            raise ConfigError(
                f"The selected note values can't exactly fill a "
                f"{self.time_signature} measure. Add a shorter value."
            )


PRESETS: dict[str, GenerationConfig] = {
    "EASY": GenerationConfig(
        name="Easy",
        numerator=4,
        denominator=4,
        keys=["C", "G"],
        rhythm_values=["whole", "half", "quarter"],
        syncopation=False,
        max_interval=4,
        rests=RestConfig(enabled=False, density=0.0),
        tempo_bpm=80,
    ),
    "MEDIUM": GenerationConfig(
        name="Medium",
        numerator=4,
        denominator=4,
        keys=["C", "G", "D", "F"],
        rhythm_values=["half", "quarter", "eighth"],
        syncopation=False,
        max_interval=7,
        rests=RestConfig(enabled=True, density=0.15),
        tempo_bpm=90,
    ),
    "HARD": GenerationConfig(
        name="Hard",
        numerator=4,
        denominator=4,
        keys=list(SUPPORTED_KEYS),
        rhythm_values=[
            "half",
            "quarter",
            "eighth",
            "sixteenth",
            "dotted-quarter",
            "eighth-triplet",
        ],
        syncopation=True,
        max_interval=12,
        rests=RestConfig(enabled=True, density=0.2),
        tempo_bpm=100,
    ),
}


def get_preset(name: str) -> GenerationConfig:
    """Return a deep-enough copy of a preset, defaulting to EASY for unknown names."""
    preset = PRESETS.get((name or "").upper(), PRESETS["EASY"])
    return replace(
        preset,
        keys=list(preset.keys),
        rhythm_values=list(preset.rhythm_values),
        rests=RestConfig(enabled=preset.rests.enabled, density=preset.rests.density),
    )
