import { OpenSheetMusicDisplay } from "opensheetmusicdisplay";
import { Player } from "./player";
import { DEFAULT_CONFIG, summarize, type GenerationConfig } from "./config";
import { ConfigStore } from "./store";
import "./style.css";

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

// Top bar / library
const presetsEl = $<HTMLDivElement>("presets");
const nameEl = $<HTMLInputElement>("config_name");
const generateBtn = $<HTMLButtonElement>("generate");
const configListEl = $<HTMLSelectElement>("config_list");
const loadBtn = $<HTMLButtonElement>("load");
const saveBtn = $<HTMLButtonElement>("save");
const deleteBtn = $<HTMLButtonElement>("delete");
const exportBtn = $<HTMLButtonElement>("export");
const importEl = $<HTMLInputElement>("import");

// Customization controls
const numeratorEl = $<HTMLInputElement>("numerator");
const denominatorEl = $<HTMLSelectElement>("denominator");
const keysEl = $<HTMLDivElement>("keys");
const clefEl = $<HTMLSelectElement>("clef");
const rhythmEl = $<HTMLDivElement>("rhythm");
const restValuesEl = $<HTMLDivElement>("rest_values");
const restsEnabledEl = $<HTMLInputElement>("rests_enabled");
const densityEl = $<HTMLInputElement>("density");
const densityValueEl = $<HTMLSpanElement>("density_value");
const maxIntervalEl = $<HTMLSelectElement>("max_interval");
const syncopationEl = $<HTMLInputElement>("syncopation");
const polyphonicEl = $<HTMLInputElement>("polyphonic");
const minPitchEl = $<HTMLSelectElement>("min_pitch");
const maxPitchEl = $<HTMLSelectElement>("max_pitch");
const measuresEl = $<HTMLInputElement>("measures");
const controlsEl = $<HTMLFormElement>("controls");

// Player
const playBtn = $<HTMLButtonElement>("play");
const pauseBtn = $<HTMLButtonElement>("pause");
const stopBtn = $<HTMLButtonElement>("stop");
const tempoEl = $<HTMLInputElement>("tempo");
const tempoValueEl = $<HTMLSpanElement>("tempo-value");
const instrumentEl = $<HTMLSelectElement>("instrument");
const metronomeEl = $<HTMLInputElement>("metronome");
const countInEl = $<HTMLInputElement>("count_in");
const statusEl = $<HTMLParagraphElement>("status");

interface Options {
  difficulties: string[];
  keys: { id: string; label: string; group: string }[];
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
  drawMeasureNumbers: false,
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

// --- Build dynamic controls --------------------------------------------------
function buildCheckgroup(container: HTMLElement, items: { id: string; label: string }[]) {
  container.innerHTML = "";
  for (const { id, label } of items) container.appendChild(checkbox(id, label));
}

function checkbox(value: string, label: string): HTMLLabelElement {
  const wrap = document.createElement("label");
  wrap.className = "checkbox";
  const box = document.createElement("input");
  box.type = "checkbox";
  box.value = value;
  wrap.append(box, document.createTextNode(" " + label));
  return wrap;
}

const CLEF_RANGES: Record<string, [string, number][]> = (() => {
  const FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
  // Treble: E3 (midi 52) to D5 (midi 74); Bass: E2 (midi 40) to D4 (midi 62)
  function range(lowMidi: number, highMidi: number): [string, number][] {
    const result: [string, number][] = [];
    for (let m = lowMidi; m <= highMidi; m++) {
      result.push([FLAT_NAMES[m % 12] + Math.floor(m / 12 - 1), m]);
    }
    return result;
  }
  return { treble: range(52, 74), bass: range(40, 62) };
})();

function buildPitchDropdowns(clef: string) {
  const pitches = CLEF_RANGES[clef] ?? CLEF_RANGES["treble"];
  const validLabels = new Set(pitches.map(([label]) => label));
  for (const el of [minPitchEl, maxPitchEl]) {
    const current = el.value;
    el.innerHTML = "";
    el.add(new Option("Any", ""));
    for (const [label] of pitches) el.add(new Option(label, label));
    el.value = validLabels.has(current) ? current : "";
  }
}

function buildKeyGroups(container: HTMLElement, keys: Options["keys"]) {
  container.innerHTML = "";
  const groups = new Map<string, typeof keys>();
  for (const k of keys) {
    if (!groups.has(k.group)) groups.set(k.group, []);
    groups.get(k.group)!.push(k);
  }
  for (const [group, items] of groups) {
    const col = document.createElement("div");
    col.className = "keygroup";
    const heading = document.createElement("span");
    heading.className = "keygroup-title";
    heading.textContent = group;
    col.appendChild(heading);
    const grid = document.createElement("div");
    grid.className = "checkgroup";
    for (const k of items) grid.appendChild(checkbox(k.id, k.label));
    col.appendChild(grid);
    container.appendChild(col);
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

  buildKeyGroups(keysEl, options.keys);
  buildCheckgroup(rhythmEl, options.rhythmValues);
  buildCheckgroup(restValuesEl, options.rhythmValues);

  clefEl.innerHTML = "";
  for (const c of options.clefs) {
    const opt = new Option(c.charAt(0).toUpperCase() + c.slice(1), c);
    clefEl.add(opt);
  }
  buildPitchDropdowns(clefEl.value);

  maxIntervalEl.innerHTML = "";
  maxIntervalEl.add(new Option("Any", ""));
  for (const i of options.intervals) maxIntervalEl.add(new Option(i.label, String(i.semitones)));

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
  nameEl.value = c.name ?? "";
  numeratorEl.value = String(c.numerator);
  denominatorEl.value = String(c.denominator);
  setChecked(keysEl, c.keys);
  clefEl.value = c.clef;
  setChecked(rhythmEl, c.rhythm_values);
  setChecked(restValuesEl, c.rest_values);
  restsEnabledEl.checked = c.rests.enabled;
  densityEl.value = String(Math.round(c.rests.density * 100));
  densityValueEl.textContent = densityEl.value + "%";
  maxIntervalEl.value = c.max_interval === null ? "" : String(c.max_interval);
  syncopationEl.checked = c.syncopation;
  polyphonicEl.checked = c.polyphonic;
  measuresEl.value = String(c.measures);
  tempoEl.value = String(c.tempo_bpm);
  tempoValueEl.textContent = tempoEl.value;
  buildPitchDropdowns(c.clef);
  minPitchEl.value = c.min_pitch ?? "";
  maxPitchEl.value = c.max_pitch ?? "";
}

function readConfig(): GenerationConfig {
  return {
    name: nameEl.value.trim() || null,
    numerator: Number(numeratorEl.value) || 4,
    denominator: Number(denominatorEl.value) || 4,
    keys: checkedValues(keysEl),
    clef: clefEl.value,
    measures: Number(measuresEl.value) || 16,
    rhythm_values: checkedValues(rhythmEl),
    rest_values: checkedValues(restValuesEl),
    syncopation: syncopationEl.checked,
    max_interval: maxIntervalEl.value === "" ? null : Number(maxIntervalEl.value),
    rests: { enabled: restsEnabledEl.checked, density: Number(densityEl.value) / 100 },
    polyphonic: polyphonicEl.checked,
    tempo_bpm: Number(tempoEl.value) || 90,
    seed: null,
    min_pitch: minPitchEl.value || null,
    max_pitch: maxPitchEl.value || null,
  };
}

// --- Generate ----------------------------------------------------------------
async function generate() {
  const config = readConfig();
  if (config.keys.length === 0) return setStatus("Select at least one key.", true);
  if (config.rhythm_values.length === 0)
    return setStatus("Select at least one note value.", true);

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
  const scrollY = window.scrollY; // OSMD's cursor.show() can steal scroll; restore it
  await osmd.load(xml);
  osmd.render();
  osmd.cursor?.show();
  requestAnimationFrame(() => window.scrollTo({ top: scrollY }));

  engine.load();
  engine.setBpm(config.tempo_bpm);
  engine.setMeasureLength(config.numerator, config.denominator);
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
    for (const s of saved) group.appendChild(new Option(s.name, "saved:" + s.id));
    configListEl.appendChild(group);
  }
  if (recent.length) {
    const group = document.createElement("optgroup");
    group.label = "Recent";
    recent.forEach((c, i) => group.appendChild(new Option(summarize(c), "recent:" + i)));
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
generateBtn.addEventListener("click", () => {
  generate().catch((err) => setStatus(`Error: ${err.message}`, true));
});
controlsEl.addEventListener("submit", (e) => e.preventDefault());

densityEl.addEventListener("input", () => {
  densityValueEl.textContent = densityEl.value + "%";
});

clefEl.addEventListener("change", () => buildPitchDropdowns(clefEl.value));

playBtn.addEventListener("click", () => engine.play());
pauseBtn.addEventListener("click", () => engine.pause());
stopBtn.addEventListener("click", () => engine.stop());
tempoEl.addEventListener("input", () => {
  tempoValueEl.textContent = tempoEl.value;
  if (scoreLoaded) engine.setBpm(Number(tempoEl.value));
});

instrumentEl.addEventListener("change", () => {
  engine.setInstrument(instrumentEl.value as "piano" | "guitar" | "violin");
});
metronomeEl.addEventListener("change", () => { engine.metronome = metronomeEl.checked; });
countInEl.addEventListener("change", () => { engine.countIn = countInEl.checked; });

loadBtn.addEventListener("click", () => {
  const config = selectedConfig();
  if (!config) return;
  applyConfig(config);
  generate().catch((err) => setStatus(`Error: ${err.message}`, true));
});

saveBtn.addEventListener("click", () => {
  const name = (nameEl.value.trim() || prompt("Name this configuration:")?.trim()) ?? "";
  if (!name) return setStatus("Enter a name to save.", true);
  nameEl.value = name;
  store.save(name, readConfig());
  refreshLibrary();
  configListEl.value = "saved:" + name;
  setStatus(`Saved "${name}".`);
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
    engine.setInstrument(instrumentEl.value as "piano" | "guitar" | "violin");
    applyConfig(presets["EASY"] ?? DEFAULT_CONFIG);
    return generate();
  })
  .catch((err) => setStatus(`Error: ${err.message}`, true));
