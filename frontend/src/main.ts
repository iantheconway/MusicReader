import { OpenSheetMusicDisplay } from "opensheetmusicdisplay";
import { Player } from "./player";
import "./style.css";

// --- DOM ---------------------------------------------------------------------
const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

const difficultyEl = $<HTMLSelectElement>("difficulty");
const keyEl = $<HTMLSelectElement>("key");
const clefEl = $<HTMLSelectElement>("clef");
const measuresEl = $<HTMLInputElement>("measures");
const polyEl = $<HTMLInputElement>("polyphonic");
const controlsEl = $<HTMLFormElement>("controls");

const playBtn = $<HTMLButtonElement>("play");
const pauseBtn = $<HTMLButtonElement>("pause");
const stopBtn = $<HTMLButtonElement>("stop");
const tempoEl = $<HTMLInputElement>("tempo");
const tempoValueEl = $<HTMLSpanElement>("tempo-value");
const statusEl = $<HTMLParagraphElement>("status");

// --- OSMD + playback ---------------------------------------------------------
const osmd = new OpenSheetMusicDisplay($("sheet"), {
  autoResize: true,
  drawTitle: true,
  drawSubtitle: false,
  drawComposer: false,
  drawPartNames: false,
  followCursor: true,
  cursorsOptions: [{ type: 0, color: "#2b6cb0", alpha: 0.4, follow: true }],
});
const engine = new Player(osmd);

let scoreLoaded = false;

function setStatus(message: string, isError = false) {
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}

function updateButtons() {
  const state = engine.state; // "PLAYING" | "PAUSED" | "STOPPED"
  playBtn.disabled = !scoreLoaded || state === "PLAYING";
  pauseBtn.disabled = !scoreLoaded || state !== "PLAYING";
  stopBtn.disabled = !scoreLoaded || state === "STOPPED";
}

engine.onStateChange = updateButtons;

// --- API ---------------------------------------------------------------------
async function loadOptions() {
  const res = await fetch("/api/options");
  const opts = (await res.json()) as {
    difficulties: string[];
    keys: string[];
    clefs: string[];
  };
  fillSelect(difficultyEl, opts.difficulties, (v) => titleCase(v));
  fillSelect(keyEl, opts.keys);
  fillSelect(clefEl, opts.clefs, titleCase);
}

function fillSelect(
  el: HTMLSelectElement,
  values: string[],
  label: (v: string) => string = (v) => v,
) {
  el.innerHTML = "";
  for (const v of values) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = label(v);
    el.appendChild(opt);
  }
}

const titleCase = (v: string) => v.charAt(0).toUpperCase() + v.slice(1).toLowerCase();

async function generate() {
  setStatus("Generating…");
  scoreLoaded = false;
  updateButtons();
  engine.stop();

  const params = new URLSearchParams({
    difficulty: difficultyEl.value,
    key: keyEl.value,
    clef: clefEl.value,
    measures: measuresEl.value || "8",
    polyphonic: String(polyEl.checked),
    tempo: tempoEl.value,
  });

  const res = await fetch(`/api/generate?${params}`);
  if (!res.ok) throw new Error(`Server returned ${res.status}`);
  const xml = await res.text();

  await osmd.load(xml);
  osmd.render();
  osmd.cursor?.show();

  engine.load();
  engine.setBpm(Number(tempoEl.value));

  scoreLoaded = true;
  updateButtons();
  setStatus("Ready. Press play.");
}

// --- Wiring ------------------------------------------------------------------
controlsEl.addEventListener("submit", (e) => {
  e.preventDefault();
  generate().catch((err) => setStatus(`Error: ${err.message}`, true));
});

playBtn.addEventListener("click", () => engine.play());
pauseBtn.addEventListener("click", () => engine.pause());
stopBtn.addEventListener("click", () => engine.stop());

tempoEl.addEventListener("input", () => {
  tempoValueEl.textContent = tempoEl.value;
  if (scoreLoaded) engine.setBpm(Number(tempoEl.value));
});

// --- Boot --------------------------------------------------------------------
loadOptions()
  .then(generate)
  .catch((err) => setStatus(`Error: ${err.message}`, true));
