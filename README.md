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
  (incl. compound/odd meters), allowed keys (major + minor, natural/harmonic),
  clef (treble/bass), rhythm values (incl. dotted + triplets), rests, max melodic
  leap, syncopation, polyphony, measures, and tempo. Easy/Medium/Hard are presets
  that fill the config. See [generator.py](backend/musicreader/generator.py),
  [rhythm.py](backend/musicreader/rhythm.py), and [model.py](backend/musicreader/model.py).
- The backend exports the piece as **MusicXML**; the frontend renders it with
  OSMD and plays it with a small Tone.js engine that schedules notes on the
  Transport (in ticks, so tempo can change live) and follows OSMD's cursor.
  See [frontend/src/player.ts](frontend/src/player.ts).
- **Configs persist** in the browser (localStorage): named saves + recent
  history, with JSON export/import for backup/sharing.
  See [frontend/src/store.ts](frontend/src/store.ts).

## Running it

You need **Python 3.12+** and **Node 18+**.

### Backend

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
