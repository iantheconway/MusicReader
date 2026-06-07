/** The generation config — mirrors the backend GenerationConfig (snake_case),
 *  so it is POSTed as-is and persisted to localStorage unchanged. */
export const DEFAULT_CONFIG = {
    name: null,
    numerator: 4,
    denominator: 4,
    keys: ["C"],
    clef: "treble",
    measures: 8,
    rhythm_values: ["whole", "half", "quarter"],
    syncopation: false,
    max_interval: null,
    rests: { enabled: false, density: 0 },
    polyphonic: false,
    harmonic_minor: false,
    tempo_bpm: 90,
    seed: null,
};
/** Short human label for dropdowns / history. */
export function summarize(c) {
    const label = c.name ?? "Custom";
    const keys = c.keys.join(",") || "—";
    return `${label} · ${c.numerator}/${c.denominator} · ${keys} · ${c.measures} bars`;
}
