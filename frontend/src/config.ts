/** The generation config — mirrors the backend GenerationConfig (snake_case),
 *  so it is POSTed as-is and persisted to localStorage unchanged. */

export interface RestConfig {
  enabled: boolean;
  density: number; // 0..1
}

export interface GenerationConfig {
  name: string | null;
  numerator: number;
  denominator: number;
  keys: string[];
  clef: string;
  measures: number;
  rhythm_values: string[];
  rest_values: string[];
  syncopation: boolean;
  max_interval: number | null;
  rests: RestConfig;
  polyphonic: boolean;
  tempo_bpm: number;
  seed: number | null;
  min_pitch: string | null;
  max_pitch: string | null;
}

export const DEFAULT_CONFIG: GenerationConfig = {
  name: null,
  numerator: 4,
  denominator: 4,
  keys: ["C"],
  clef: "treble",
  measures: 16,
  rhythm_values: ["whole", "half", "quarter"],
  rest_values: ["whole", "half", "quarter"],
  syncopation: false,
  max_interval: null,
  rests: { enabled: false, density: 0 },
  polyphonic: false,
  tempo_bpm: 90,
  seed: null,
  min_pitch: null,
  max_pitch: null,
};

/** Short human label for dropdowns / history. */
export function summarize(c: GenerationConfig): string {
  const label = c.name ?? "Custom";
  const keys = c.keys.join(",") || "—";
  return `${label} · ${c.numerator}/${c.denominator} · ${keys} · ${c.measures} bars`;
}
