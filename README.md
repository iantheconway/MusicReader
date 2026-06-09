# MusicReader

A tool for practicing **sight reading**. It procedurally generates short
exercises of sheet music at varying difficulty, key, and clef, displays them in
the browser, and plays them back at an adjustable tempo with a moving cursor so
you can read along.

Originally a school project (~2015, Python 2 + LilyPond + TensorFlow/Magenta),
now modernized into a Python API + TypeScript web app.

## Architecture

```
backend/   Python 3.12 — music21 generator + FastAPI, emits MusicXML
frontend/  TypeScript + Vite — OpenSheetMusicDisplay (render) + Tone.js (playback)
```

- **Generation** is rule-based and driven by a `GenerationConfig`: each measure
  picks a diatonic chord root, fills the bar via a rhythm engine, and samples
  note scale-degrees biased toward the chord tones. Configurable: time signature
  (incl. compound/odd meters), keys (all 12 tonics in major / natural-minor /
  harmonic-minor), clef (treble/bass), note values (incl. dotted + triplets),
  rests with their own selectable durations + density, max melodic leap,
  pitch range (min/max), syncopation, polyphony, measures, and tempo.
  Easy/Medium/Hard are presets that
  fill the config; all customization lives behind a collapsible panel. See [generator.py](backend/musicreader/generator.py),
  [rhythm.py](backend/musicreader/rhythm.py), and [model.py](backend/musicreader/model.py).
- The backend exports the piece as **MusicXML**; the frontend renders it with
  OSMD and plays it with a small Tone.js engine that schedules notes on the
  Transport (in ticks, so tempo can change live) and follows OSMD's cursor.
  Playback offers a selectable instrument (piano / guitar / violin), an optional
  metronome click, and a one-bar count-in.
  See [frontend/src/player.ts](frontend/src/player.ts).
- **Configs persist** in the browser (localStorage): named saves + recent
  history, with JSON export/import for backup/sharing.
  See [frontend/src/store.ts](frontend/src/store.ts).

## Running it

You need **Python 3.12+** and **Node 18+**. The app is two servers that run
**at the same time** — the FastAPI backend on port 8000 and the Vite dev server
on 5173 (which proxies `/api` to the backend). Use two terminals, or the bundled
VS Code task (see below).

### Backend

First-time setup, then run (the `--reload` flag picks up code changes — don't
skip it during development):

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn musicreader.api:app --reload --port 8000
```

API endpoints:
- `GET /api/options` — available difficulties, keys, clefs, rhythm values, intervals.
- `GET /api/presets` — Easy/Medium/Hard as full configs.
- `POST /api/generate` — body is a `GenerationConfig` (JSON); returns MusicXML
  (HTTP 400 with a message if the config is invalid, e.g. note values that can't
  fill the meter).
- `GET /api/generate?difficulty=EASY&key=C&...` — quick preset-based link.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Then open the URL Vite prints (default http://localhost:5173). The dev server
proxies `/api` to the backend on port 8000, so run both.

### In VS Code

A workspace task is included that launches **both** servers in parallel (split
terminals): open the Command Palette → **Tasks: Run Task** → **dev (backend +
frontend)** (it's the default build task, so `Cmd/Ctrl+Shift+B` runs it too).
Then open http://localhost:5173. Stop them with the trash-can icon on each
terminal. The task assumes the backend venv exists (run the one-time setup
above first).

> Note: the frontend's `.ts` files are the source of truth. Never commit
> compiled `.js` next to them in `frontend/src/` — Vite resolves `.js` before
> `.ts`, so a stale sibling would shadow your source. `tsconfig.json` sets
> `"noEmit": true` so `tsc` only type-checks (`vite build` does the compiling).

### Tests

```bash
cd backend && .venv/bin/pytest
```

## Roadmap

- Richer generation rules (phrasing, voice leading).
- Optional ML-based generation (modern models, not the retired Magenta path).
- Optional server-side config storage (the localStorage layer is storage-agnostic).

## Credits

Notation rendering by [OpenSheetMusicDisplay](https://opensheetmusicdisplay.org/);
audio via [Tone.js](https://tonejs.github.io/); music modeling via
[music21](https://web.mit.edu/music21/).
