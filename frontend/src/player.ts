import * as Tone from "tone";
import type { Cursor, OpenSheetMusicDisplay } from "opensheetmusicdisplay";

export type PlayerState = "STOPPED" | "PLAYING" | "PAUSED";

interface TimedNote {
  freq: number; // Hz
  durQuarters: number;
}

interface Step {
  posQuarters: number;
  notes: TimedNote[];
}

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
  private synth: Tone.PolySynth;
  private steps: Step[] = [];
  private visualIndex = 0;
  state: PlayerState = "STOPPED";
  onStateChange?: (state: PlayerState) => void;

  constructor(private osmd: OpenSheetMusicDisplay) {
    this.synth = new Tone.PolySynth(Tone.Synth).toDestination();
    this.synth.volume.value = -6;
  }

  /** OSMD's cursor only exists after the first render(); may be undefined. */
  private get cursor(): Cursor | undefined {
    return this.osmd.cursor;
  }

  /** Read the rendered score into a flat step list. Call after osmd.render(). */
  load(): void {
    this.stop();
    this.steps = this.readSteps();
  }

  setBpm(bpm: number): void {
    Tone.Transport.bpm.value = bpm;
  }

  async play(): Promise<void> {
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

  pause(): void {
    if (this.state !== "PLAYING") return;
    Tone.Transport.pause();
    this.setState("PAUSED");
  }

  stop(): void {
    Tone.Transport.stop();
    Tone.Transport.cancel(0);
    Tone.Transport.position = 0;
    this.synth.releaseAll();
    this.resetCursor();
    this.setState("STOPPED");
  }

  private scheduleAll(): void {
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
      const endQ =
        last.posQuarters + Math.max(1, ...last.notes.map((n) => n.durQuarters));
      Tone.Transport.schedule((time) => {
        Tone.Draw.schedule(() => this.stop(), time);
      }, Math.round(endQ * ppq) + "i");
    }
  }

  private readSteps(): Step[] {
    const cursor = this.cursor;
    if (!cursor) return [];
    cursor.reset();
    const iter = cursor.iterator;
    const steps: Step[] = [];
    while (!iter.EndReached) {
      const notes: TimedNote[] = [];
      for (const entry of iter.CurrentVoiceEntries ?? []) {
        for (const note of entry.Notes) {
          if (note.isRest() || !note.Pitch) continue;
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

  private moveCursorTo(target: number): void {
    const cursor = this.cursor;
    if (!cursor) return;
    while (this.visualIndex < target) {
      cursor.next();
      this.visualIndex++;
    }
  }

  private resetCursor(): void {
    const cursor = this.cursor;
    if (!cursor) return;
    cursor.reset();
    cursor.show();
    this.visualIndex = 0;
  }

  private setState(state: PlayerState): void {
    this.state = state;
    this.onStateChange?.(state);
  }
}
