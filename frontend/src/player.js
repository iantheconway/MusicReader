import * as Tone from "tone";
/**
 * Plays back an OSMD score with Tone.js and keeps OSMD's cursor in sync.
 *
 * The score is flattened into a list of timed steps (one per cursor position).
 * Events are scheduled on Tone's Transport in *ticks*, so changing
 * `Transport.bpm` rescales everything — letting tempo change live during
 * playback. The visual cursor is advanced from `Tone.Draw` callbacks so it
 * stays aligned with the audio without blocking it.
 */
export class Player {
    constructor(osmd) {
        this.osmd = osmd;
        this.steps = [];
        this.visualIndex = 0;
        this.state = "STOPPED";
        this.synth = new Tone.PolySynth(Tone.Synth).toDestination();
        this.synth.volume.value = -6;
    }
    /** OSMD's cursor only exists after the first render(); may be undefined. */
    get cursor() {
        return this.osmd.cursor;
    }
    /** Read the rendered score into a flat step list. Call after osmd.render(). */
    load() {
        this.stop();
        this.steps = this.readSteps();
    }
    setBpm(bpm) {
        Tone.Transport.bpm.value = bpm;
    }
    async play() {
        if (this.state === "PAUSED") {
            Tone.Transport.start();
            this.setState("PLAYING");
            return;
        }
        await Tone.start(); // unlock AudioContext (must be from a user gesture)
        this.scheduleAll();
        Tone.Transport.position = 0;
        this.resetCursor();
        Tone.Transport.start();
        this.setState("PLAYING");
    }
    pause() {
        if (this.state !== "PLAYING")
            return;
        Tone.Transport.pause();
        this.setState("PAUSED");
    }
    stop() {
        Tone.Transport.stop();
        Tone.Transport.cancel(0);
        Tone.Transport.position = 0;
        this.synth.releaseAll();
        this.resetCursor();
        this.setState("STOPPED");
    }
    scheduleAll() {
        Tone.Transport.cancel(0);
        const ppq = Tone.Transport.PPQ;
        this.steps.forEach((step, i) => {
            const at = Math.round(step.posQuarters * ppq) + "i";
            Tone.Transport.schedule((time) => {
                for (const n of step.notes) {
                    const dur = Math.max(1, Math.round(n.durQuarters * ppq)) + "i";
                    this.synth.triggerAttackRelease(n.freq, dur, time);
                }
                Tone.Draw.schedule(() => this.moveCursorTo(i), time);
            }, at);
        });
        const last = this.steps[this.steps.length - 1];
        if (last) {
            const endQ = last.posQuarters + Math.max(1, ...last.notes.map((n) => n.durQuarters));
            Tone.Transport.schedule((time) => {
                Tone.Draw.schedule(() => this.stop(), time);
            }, Math.round(endQ * ppq) + "i");
        }
    }
    readSteps() {
        const cursor = this.cursor;
        if (!cursor)
            return [];
        cursor.reset();
        const iter = cursor.iterator;
        const steps = [];
        while (!iter.EndReached) {
            const notes = [];
            for (const entry of iter.CurrentVoiceEntries ?? []) {
                for (const note of entry.Notes) {
                    if (note.isRest() || !note.Pitch)
                        continue;
                    notes.push({
                        freq: note.Pitch.Frequency,
                        durQuarters: note.Length.RealValue * 4,
                    });
                }
            }
            steps.push({ posQuarters: iter.currentTimeStamp.RealValue * 4, notes });
            iter.moveToNext();
        }
        this.resetCursor();
        return steps;
    }
    moveCursorTo(target) {
        const cursor = this.cursor;
        if (!cursor)
            return;
        while (this.visualIndex < target) {
            cursor.next();
            this.visualIndex++;
        }
    }
    resetCursor() {
        const cursor = this.cursor;
        if (!cursor)
            return;
        cursor.reset();
        cursor.show();
        this.visualIndex = 0;
    }
    setState(state) {
        this.state = state;
        this.onStateChange?.(state);
    }
}
