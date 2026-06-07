# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this project is

**MusicReader** is a tool for practicing sight reading. It procedurally generates
short pieces of sheet music at varying difficulty, key, and clef, renders them as
notation in the browser, and plays them back at a controllable tempo with a moving
cursor so a musician can practice reading along.

Originally a school project (~2015: Python 2 + LilyPond PNG rendering +
TensorFlow/Magenta). Rebuilt June 2026 into a Python API + TypeScript web app; the
legacy code (Magenta ML path, bundled 32-bit LilyPond, copied LilyPond scripts,
Bootstrap theme) was removed from the working tree but remains in git history.

## Architecture

```
backend/   Python 3.12 — music21 generator + FastAPI, emits MusicXML
frontend/  TypeScript + Vite — OpenSheetMusicDisplay (render) + Tone.js (playback)
```

### Backend (`backend/musicreader/`)
- `model.py` — `GenerationConfig` (the single serializable description of an
  exercise) + `RestConfig`, `Clef`/ranges, key catalog (major + relative minors,
  `parse_key`/`key_label`), chord-tone weights, interval options, `validate()`
  (incl. fillability), and Easy/Medium/Hard `PRESETS`.
- `rhythm.py` — the rhythm vocabulary (`RhythmValue`: whole→sixteenth, dotted,
  triplets) in exact `Fraction` quarter-lengths, plus `fill_measure` (randomized
  exhaustive backtracking that fills any meter exactly, with an optional
  no-syncopation beat constraint) and `can_fill` (used by validation).
- `generator.py` — `generate_score(config)` builds a music21 `Score`: per measure
  pick a diatonic chord root, fill the bar via the rhythm engine, sample note
  scale-degrees with a softmax bias toward chord tones, respecting a max-interval
  cap. Minor keys use natural/harmonic scales (`_build_scale`); `GenerationParams`
  is a legacy flat adapter (`to_config`) over a preset.
- `musicxml.py` — exports a Score to a MusicXML string.
- `api.py` — FastAPI: `GET /api/options`, `GET /api/presets`,
  `POST /api/generate` (JSON config body; `ConfigError` → HTTP 400), and a
  back-compat `GET /api/generate`.
- `tests/` — pytest: rhythm engine, config/meters/tuplets/rests/validation,
  melody (minor keys, interval cap, syncopation), and API.

### Frontend (`frontend/src/`)
- `config.ts` — the `GenerationConfig` TS type (mirrors the backend, snake_case so
  it POSTs as-is and persists unchanged), `DEFAULT_CONFIG`, `summarize`.
- `store.ts` — `ConfigStore`: localStorage-backed named saves + recent history
  (de-duped by musical signature) + JSON export/import. Storage-agnostic surface.
- `main.ts` — UI wiring: builds the sectioned control panel from `/api/options`,
  reads/applies a `GenerationConfig`, POSTs to `/api/generate`, renders with OSMD,
  drives the player, presets, and the saved/recent library.
- `player.ts` — `Player`: flattens the rendered score into timed steps and plays
  them with Tone.js. Events are scheduled on `Tone.Transport` in **ticks**, so
  setting `Transport.bpm` rescales everything (live tempo). The OSMD cursor is
  advanced from `Tone.Draw` callbacks to stay in sync without blocking audio.
  NOTE: `osmd.cursor` only exists after the first `render()` — guard for undefined.
- Vite proxies `/api` → `http://127.0.0.1:8000`, so run both servers in dev.

## Running / testing

- Backend: `cd backend && .venv/bin/uvicorn musicreader.api:app --reload --port 8000`
- Frontend: `cd frontend && npm run dev` (needs Node; installed via Homebrew)
- Tests: `cd backend && .venv/bin/pytest`
- Headless visual check: Chrome is at `/Applications/Google Chrome.app`; can
  `--headless=new ... --screenshot` against the dev server to confirm rendering.

## Conventions / gotchas

- Any meter whose bar the selected rhythm values can tile; `MAX_MEASURES = 64`.
  Supported keys are in `SUPPORTED_KEYS` (major + relative minors).
- The no-syncopation rule is best-effort: if a bar can't be filled without it,
  `_fill_bar` falls back to allowing syncopation rather than failing. The
  interval cap is likewise best-effort near the edges of the staff range.
- music21's MusicXML export assigns a random `part id` each time — don't compare
  raw MusicXML for equality in tests; compare extracted notes/durations instead.
- `osmd-audio-player` was evaluated and rejected: abandoned, pinned to OSMD 0.8.x.
  Playback is intentionally hand-rolled on Tone.js against modern OSMD 1.9.

## Working agreements

- This is a deliberate, planning-heavy revival. Confirm the plan before large
  refactors or stack/dependency changes.
- The owner is most comfortable in Python and wants to keep generation there;
  improving generation rules and (eventually) adding modern ML generation are
  planned next steps.
