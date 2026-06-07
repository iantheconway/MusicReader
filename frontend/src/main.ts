import { OpenSheetMusicDisplay } from "opensheetmusicdisplay";
import { Player } from "./player";
import { DEFAULT_CONFIG, summarize, type GenerationConfig } from "./config";
import { ConfigStore } from "./store";
import "./style.css";

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

// Control elements
const numeratorEl = $<HTMLInputElement>("numerator");
const denominatorEl = $<HTMLSelectElement>("denominator");
const keysEl = $<HTMLDivElement>("keys");
const harmonicEl = $<HTMLInputElement>("harmonic_minor");
const clefEl = $<HTMLSelectElement>("clef");
const rhythmEl = $<HTMLDivElement>("rhythm");
const restsEnabledEl = $<HTMLInputElement>("rests_enabled");
const densityEl = $<HTMLInputElement>("density");
const densityValueEl = $<HTMLSpanElement>("density_value");
const maxIntervalEl = $<HTMLSelectElement>("max_interval");
const syncopationEl = $<HTMLInputElement>("syncopation");
const polyphonicEl = $<HTMLInputElement>("polyphonic");
const measuresEl = $<HTMLInputElement>("measures");
const presetsEl = $<HTMLDivElement>("presets");
const controlsEl = $<HTMLFormElement>("controls");

// Library elements
const configListEl = $<HTMLSelectElement>("config_list");
const loadBtn = $<HTMLButtonElement>("load");
const saveBtn = $<HTMLButtonElement>("save");
const deleteBtn = $<HTMLButtonElement>("delete");
const exportBtn = $<HTMLButtonElement>("export");
const importEl = $<HTMLInputElement>("import");

// Player elements
const playBtn = $<HTMLButtonElement>("play");
const pauseBtn = $<HTMLButtonElement>("pause");
const stopBtn = $<HTMLButtonElement>("stop");
const tempoEl = $<HTMLInputElement>("tempo");
const tempoValueEl = $<HTMLSpanElement>("tempo-value");
const statusEl = $<HTMLParagraphElement>("status");

interface Options {
  difficulties: string[];
  keys: { id: string; label: string }[];
  clefs: string[];
  rhythmValues: { id: string; label: string }[];
  intervals: { semitones: number; label: string }[];
}

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
const store = new ConfigStore();

let scoreLoaded = false;
let presets: Record<string, GenerationConfig> = {};

function setStatus(message: string, isError = false) {
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}

function updateButtons() {
  const state = engine.state;
  playBtn.disabled = !scoreLoaded || state === "PLAYING";
  pauseBtn.disabled = !scoreLoaded || state !== "PLAYING";
  stopBtn.disabled = !scoreLoaded || state === "STOPPED";
}
engine.onStateChange = updateButtons;

// --- Build dynamic controls from /api/options --------------------------------
function buildCheckgroup(
  container: HTMLElement,
  items: { id: string; label: string }[],
) {
  container.innerHTML = "";
  for (const { id, label } of items) {
    const wrap = document.createElement("label");
    wrap.className = "checkbox";
    const box = document.createElement("input");
    box.type = "checkbox";
    box.value = id;
    wrap.append(box, document.createTextNode(" " + label));
    container.appendChild(wrap);
  }
}

function checkedValues(container: HTMLElement): string[] {
  return [...container.querySelectorAll<HTMLInputElement>("input:checked")].map(
    (el) => el.value,
  );
}

function setChecked(container: HTMLElement, values: string[]) {
  const wanted = new Set(values);
  for (const el of container.querySelectorAll<HTMLInputElement>("input")) {
    el.checked = wanted.has(el.value);
  }
}

async function loadOptions() {
  const [options, presetData] = await Promise.all([
    fetch("/api/options").then((r) => r.json() as Promise<Options>),
    fetch("/api/presets").then((r) => r.json() as Promise<Record<string, GenerationConfig>>),
  ]);
  presets = presetData;

  buildCheckgroup(keysEl, options.keys);
  buildCheckgroup(rhythmEl, options.rhythmValues);

  clefEl.innerHTML = "";
  for (const c of options.clefs) {
    const opt = document.createElement("option");
    opt.value = c;
    opt.textContent = c.charAt(0).toUpperCase() + c.slice(1);
    clefEl.appendChild(opt);
  }

  maxIntervalEl.innerHTML = "";
  const any = document.createElement("option");
  any.value = "";
  any.textContent = "Any";
  maxIntervalEl.appendChild(any);
  for (const i of options.intervals) {
    const opt = document.createElement("option");
    opt.value = String(i.semitones);
    opt.textContent = i.label;
    maxIntervalEl.appendChild(opt);
  }

  presetsEl.innerHTML = "";
  for (const name of options.difficulties) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = name.charAt(0) + name.slice(1).toLowerCase();
    btn.addEventListener("click", () => {
      applyConfig(presets[name]);
      generate();
    });
    presetsEl.appendChild(btn);
  }
}

// --- Config <-> DOM ----------------------------------------------------------
function applyConfig(c: GenerationConfig) {
  numeratorEl.value = String(c.numerator);
  denominatorEl.value = String(c.denominator);
  setChecked(keysEl, c.keys);
  harmonicEl.checked = c.harmonic_minor;
  clefEl.value = c.clef;
  setChecked(rhythmEl, c.rhythm_values);
  restsEnabledEl.checked = c.rests.enabled;
  densityEl.value = String(Math.round(c.rests.density * 100));
  densityValueEl.textContent = densityEl.value + "%";
  maxIntervalEl.value = c.max_interval === null ? "" : String(c.max_interval);
  syncopationEl.checked = c.syncopation;
  polyphonicEl.checked = c.polyphonic;
  measuresEl.value = String(c.measures);
  tempoEl.value = String(c.tempo_bpm);
  tempoValueEl.textContent = tempoEl.value;
}

function readConfig(): GenerationConfig {
  return {
    name: null,
    numerator: Number(numeratorEl.value) || 4,
    denominator: Number(denominatorEl.value) || 4,
    keys: checkedValues(keysEl),
    clef: clefEl.value,
    measures: Number(measuresEl.value) || 8,
    rhythm_values: checkedValues(rhythmEl),
    syncopation: syncopationEl.checked,
    max_interval: maxIntervalEl.value === "" ? null : Number(maxIntervalEl.value),
    rests: {
      enabled: restsEnabledEl.checked,
      density: Number(densityEl.value) / 100,
    },
    polyphonic: polyphonicEl.checked,
    harmonic_minor: harmonicEl.checked,
    tempo_bpm: Number(tempoEl.value) || 90,
    seed: null,
  };
}

// --- Generate ----------------------------------------------------------------
async function generate() {
  const config = readConfig();
  if (config.keys.length === 0) return setStatus("Select at least one key.", true);
  if (config.rhythm_values.length === 0)
    return setStatus("Select at least one rhythm value.", true);

  setStatus("Generating…");
  scoreLoaded = false;
  updateButtons();
  engine.stop();

  const res = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!res.ok) {
    const detail = res.status === 400 ? (await res.json()).detail : `Server ${res.status}`;
    return setStatus(detail, true);
  }

  const xml = await res.text();
  await osmd.load(xml);
  osmd.render();
  osmd.cursor?.show();

  engine.load();
  engine.setBpm(config.tempo_bpm);
  scoreLoaded = true;
  updateButtons();
  setStatus("Ready. Press play.");

  store.pushRecent(config);
  refreshLibrary();
}

// --- Library (saved + recent) ------------------------------------------------
function refreshLibrary() {
  const saved = store.listSaved();
  const recent = store.listRecent();
  configListEl.innerHTML = "";

  if (saved.length) {
    const group = document.createElement("optgroup");
    group.label = "Saved";
    for (const s of saved) {
      const opt = document.createElement("option");
      opt.value = "saved:" + s.id;
      opt.textContent = s.name;
      group.appendChild(opt);
    }
    configListEl.appendChild(group);
  }
  if (recent.length) {
    const group = document.createElement("optgroup");
    group.label = "Recent";
    recent.forEach((c, i) => {
      const opt = document.createElement("option");
      opt.value = "recent:" + i;
      opt.textContent = summarize(c);
      group.appendChild(opt);
    });
    configListEl.appendChild(group);
  }
}

function selectedConfig(): GenerationConfig | null {
  const value = configListEl.value;
  if (value.startsWith("saved:")) {
    return store.listSaved().find((s) => s.id === value.slice(6))?.config ?? null;
  }
  if (value.startsWith("recent:")) {
    return store.listRecent()[Number(value.slice(7))] ?? null;
  }
  return null;
}

// --- Wiring ------------------------------------------------------------------
controlsEl.addEventListener("submit", (e) => {
  e.preventDefault();
  generate().catch((err) => setStatus(`Error: ${err.message}`, true));
});

densityEl.addEventListener("input", () => {
  densityValueEl.textContent = densityEl.value + "%";
});

playBtn.addEventListener("click", () => engine.play());
pauseBtn.addEventListener("click", () => engine.pause());
stopBtn.addEventListener("click", () => engine.stop());
tempoEl.addEventListener("input", () => {
  tempoValueEl.textContent = tempoEl.value;
  if (scoreLoaded) engine.setBpm(Number(tempoEl.value));
});

loadBtn.addEventListener("click", () => {
  const config = selectedConfig();
  if (config) {
    applyConfig(config);
    generate().catch((err) => setStatus(`Error: ${err.message}`, true));
  }
});

saveBtn.addEventListener("click", () => {
  const name = prompt("Save this configuration as:");
  if (!name) return;
  store.save(name.trim(), readConfig());
  refreshLibrary();
  configListEl.value = "saved:" + name.trim();
  setStatus(`Saved "${name.trim()}".`);
});

deleteBtn.addEventListener("click", () => {
  const value = configListEl.value;
  if (!value.startsWith("saved:")) return setStatus("Select a saved config to delete.", true);
  store.remove(value.slice(6));
  refreshLibrary();
});

exportBtn.addEventListener("click", () => {
  const blob = new Blob([store.exportLibrary()], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "musicreader-configs.json";
  a.click();
  URL.revokeObjectURL(url);
});

importEl.addEventListener("change", async () => {
  const file = importEl.files?.[0];
  if (!file) return;
  try {
    const count = store.importLibrary(await file.text());
    refreshLibrary();
    setStatus(`Imported ${count} config(s).`);
  } catch {
    setStatus("Import failed: invalid file.", true);
  }
  importEl.value = "";
});

// --- Boot --------------------------------------------------------------------
loadOptions()
  .then(() => {
    refreshLibrary();
    applyConfig(presets["EASY"] ?? DEFAULT_CONFIG);
    return generate();
  })
  .catch((err) => setStatus(`Error: ${err.message}`, true));
