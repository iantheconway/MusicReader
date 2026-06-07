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

- **Generation** is rule-based: each measure picks a diatonic chord root, then
  fills the bar with notes whose scale degrees are biased toward the chord tones,
  at a rhythmic complexity set by the difficulty level. See
  [backend/musicreader/generator.py](backend/musicreader/generator.py).
- The backend exports the piece as **MusicXML**; the frontend renders it with
  OSMD and plays it with a small Tone.js engine that schedules notes on the
  Transport (in ticks, so tempo can change live) and follows OSMD's cursor.
  See [frontend/src/player.ts](frontend/src/player.ts).

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
- `GET /api/options` — available difficulties, keys, clefs.
- `GET /api/generate?difficulty=EASY&key=C&clef=treble&measures=8&polyphonic=false&tempo=90`
  — returns MusicXML.

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

- Richer generation rules (phrasing, voice leading, time signatures beyond 4/4).
- Optional ML-based generation (modern models, not the retired Magenta path).

## Credits

Notation rendering by [OpenSheetMusicDisplay](https://opensheetmusicdisplay.org/);
audio via [Tone.js](https://tonejs.github.io/); music modeling via
[music21](https://web.mit.edu/music21/).
