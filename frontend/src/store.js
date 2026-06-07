/** Persistence for configs: named saves + recent history in localStorage,
 *  plus JSON export/import. Storage-agnostic surface so a server-backed store
 *  could replace it later without touching callers. */
const SAVED_KEY = "musicreader.saved.v1";
const RECENT_KEY = "musicreader.recent.v1";
const RECENT_LIMIT = 10;
function read(key, fallback) {
    try {
        const raw = localStorage.getItem(key);
        return raw ? JSON.parse(raw) : fallback;
    }
    catch {
        return fallback;
    }
}
function write(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
}
/** Identity for de-duping recent history: the musical setup, ignoring
 *  cosmetic name and the (usually random) seed. */
function signature(config) {
    const { name: _name, seed: _seed, ...rest } = config;
    return JSON.stringify(rest);
}
export class ConfigStore {
    listSaved() {
        return read(SAVED_KEY, []);
    }
    save(name, config) {
        const others = this.listSaved().filter((s) => s.name !== name);
        others.unshift({ id: name, name, config: { ...config, name } });
        write(SAVED_KEY, others);
    }
    remove(id) {
        write(SAVED_KEY, this.listSaved().filter((s) => s.id !== id));
    }
    listRecent() {
        return read(RECENT_KEY, []);
    }
    pushRecent(config) {
        const key = signature(config);
        const recent = this.listRecent().filter((c) => signature(c) !== key);
        recent.unshift(config);
        write(RECENT_KEY, recent.slice(0, RECENT_LIMIT));
    }
    exportLibrary() {
        return JSON.stringify({ version: 1, saved: this.listSaved() }, null, 2);
    }
    /** Merge an exported library into the saved set (incoming wins on id clash). */
    importLibrary(json) {
        const data = JSON.parse(json);
        const incoming = data.saved ?? [];
        const byId = new Map(this.listSaved().map((s) => [s.id, s]));
        for (const item of incoming)
            byId.set(item.id, item);
        write(SAVED_KEY, [...byId.values()]);
        return incoming.length;
    }
}
