import { OpenSheetMusicDisplay } from "opensheetmusicdisplay";
import { Player } from "./player";
import "./style.css";
// --- DOM ---------------------------------------------------------------------
const $ = (id) => document.getElementById(id);
const difficultyEl = $("difficulty");
const keyEl = $("key");
const clefEl = $("clef");
const measuresEl = $("measures");
const polyEl = $("polyphonic");
const controlsEl = $("controls");
const playBtn = $("play");
const pauseBtn = $("pause");
const stopBtn = $("stop");
const tempoEl = $("tempo");
const tempoValueEl = $("tempo-value");
const statusEl = $("status");
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
function setStatus(message, isError = false) {
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
    const opts = (await res.json());
    fillSelect(difficultyEl, opts.difficulties, (v) => titleCase(v));
    fillSelect(keyEl, opts.keys);
    fillSelect(clefEl, opts.clefs, titleCase);
}
function fillSelect(el, values, label = (v) => v) {
    el.innerHTML = "";
    for (const v of values) {
        const opt = document.createElement("option");
        opt.value = v;
        opt.textContent = label(v);
        el.appendChild(opt);
    }
}
const titleCase = (v) => v.charAt(0).toUpperCase() + v.slice(1).toLowerCase();
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
    if (!res.ok)
        throw new Error(`Server returned ${res.status}`);
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
    if (scoreLoaded)
        engine.setBpm(Number(tempoEl.value));
});
// --- Boot --------------------------------------------------------------------
loadOptions()
    .then(generate)
    .catch((err) => setStatus(`Error: ${err.message}`, true));
