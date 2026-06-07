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
- `model.py` — `Difficulty` profiles (allowed rhythm values, syncopation, rest
  chance), `Clef` enum + per-clef comfortable ranges, chord-tone weights.
- `generator.py` — the rule-based generator. `GenerationParams` + `generate_score`
  build a music21 `Score`. Core idea: per measure, pick a random diatonic chord
  root, fill the bar with rhythm values allowed by difficulty, and sample note
  scale-degrees with a softmax bias toward chord tones (root/third/fifth). Keys
  via music21 scales; treble/bass via clef range; optional polyphony adds a third.
- `musicxml.py` — exports a Score to a MusicXML string.
- `api.py` — FastAPI app: `GET /api/options`, `GET /api/generate` (returns MusicXML).
- `tests/` — pytest smoke tests (full bars, determinism by seed, valid MusicXML).

### Frontend (`frontend/src/`)
- `main.ts` — UI wiring: fetch options, build query, fetch MusicXML, load+render
  with OSMD, drive the player and controls (difficulty/key/clef/measures/poly/tempo).
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

- 4/4 only for now; `MAX_MEASURES = 64`. Supported keys are in `SUPPORTED_KEYS`.
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
