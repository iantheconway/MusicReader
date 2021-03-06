# This software is built using GNU Lilypond, and as such is provided under the GNU General Public License
"""WebReader
This program runs a small web server which will create a display a piece of sheet
music of varying complexity so that a musician can practice sight reading.
There are several modes of music generation that are supported.
The Easy, Medium and Hard modes are rule based with an element of randomness. They
support different keys and the option to be polyphonic. The Old Version setting is
another rule based algorithm that I came up with, but it does not support different keys
or polyphonic mode.
"""

import os
import subprocess
from subprocess import Popen, PIPE
import random
import datetime
import time

from flask import Flask, render_template, send_from_directory, send_file, request, url_for, redirect
import numpy as np
from magenta.music.melodies_lib import Melody

# Use Flask web server

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 1


def softmax(x):
    """Compute softmax values for each sets of scores in x."""
    return np.exp(x) / np.sum(np.exp(x), axis=0)


class Measure:
    """Class which represents a measure of music. Each measure has a chord,
    a set of notes, and a counter which represents how much of the measure
    has passed already during generation, so we don't try to fill it with
    too many notes. For the sake of this program, every measure will have
    only one chord.
    """
    def __init__(self):
        """Initialize the Measure"""
        self.counter = 0
        self.notes = []
        self.chord = None


class Chord:
    """Class to represent chord. The chord has a degree of the scale that
    it's based on, a plain text tonic, and it has a set of weights for
    each note, which represent the probability of that note being played
    over the chord.
    """
    def __init__(self):
        self.degree = None
        # Weights for each scale degree
        self.weights = [1.6, .3, 1.5, .6, 1.4, .4, .2]


class Note:
    """Class to represent a musical note, which can either be a pitch or
    a rest. The note has a rhythm value.
    """
    def __init__(self):
        self.rest = None
        self.rhythm = None
        self.pitch = None
        self.third = None


class RhythmValue:
    """Class to represent rhythm value of a note, along with the fraction of
    a measure; I.E an 8th not would be RhythmValue(8) and RhythmValue
    eight.fraction would be 0.125. We use the fraction for tallying up
    to an even measure.
    """
    def __init__(self, value):
        self.value = value
        self.fraction = 1.0 / value


class Difficulty:
    """Class to represent a difficulty level for a composition. For this
    program's purpose, the difficulty will be determined by the allowable
    RhythmValues and allowable syncopations.
    """
    def __init__(self, level):
        self.level = level
        self.rhythm_values = None
        self.sycopations = None
        self.min_beat = None
        self.rest_chance = None
        if self.level == "EASY":
            self.rhythm_values = []
            self.rhythm_values.append(RhythmValue(1))
            self.rhythm_values.append(RhythmValue(2))
            self.rhythm_values.append(RhythmValue(4))
            self.min_beat = 8
            self.sycopations = []
            self.sycopations.append(0)
            # self.sycopations.append(.5)
            self.rest_chance = 4
        elif self.level == "MEDIUM":
            self.rhythm_values = []
            self.rhythm_values.append(RhythmValue(1))
            self.rhythm_values.append(RhythmValue(2))
            self.rhythm_values.append(RhythmValue(4))
            self.rhythm_values.append(RhythmValue(8))
            self.min_beat = 8
            self.sycopations = []
            self.sycopations.append(0)
            # self.sycopations.append(.5)
            self.rest_chance = 4
        elif self.level == "HARD":
            self.rhythm_values = []
            self.rhythm_values.append(RhythmValue(1))
            self.rhythm_values.append(RhythmValue(2))
            self.rhythm_values.append(RhythmValue(4))
            self.rhythm_values.append(RhythmValue(8))
            self.rhythm_values.append(RhythmValue(16))
            self.min_beat = 16
            self.sycopations = []
            self.sycopations.append(0)
            self.sycopations.append(.5)
            # self.sycopations.append(.25) # Not sure about this
            self.rest_chance = 4


class Composition:
    """Class representing the composition, which has a difficulty, a key, and an array of measures."""
    def __init__(self, difficulty, key):
        self.difficulty = Difficulty(difficulty)
        self.key = key
        self.measures = []


class WebReader:
    """Class representing the Web Reader"""
    def __init__(self):
        self.MusicGenerator = MusicGenerator()

    def compose_music(self, difficulty):
        compostition = Composition(difficulty)


# TODO: use this
class Logger:
    """Logging class which writes messages to a file."""
    def __init__(self):
        self.file = open("log.txt", 'a')
        self.file.write("New session\n")
        self.file.write(datetime.datetime.now())
        self.file.write("\n")

    def log(self, message):
        self.file.write(message)


class Note:
    """Class representing a  note which has a pitch and rhythm value."""
    def __init__(self, rhythm_value, pitch):
        self.rhythm_value = rhythm_value
        self.pitch = pitch


class MusicGenerator:
    """Class representing a music generator which creates compositions using rules."""
    def __init__(self):
        # notes I like to read on guitar
        # TODO: Move these into a more appropriate place, and then work out
        # what to do for different keys.
        self.guitar_notes = ['e', 'f', 'g', 'a', 'b', 'c\'', 'd\'', 'e\'',
                             'f\'', 'g\'', 'a\'', 'b\'', 'c\'\'', 'd\'\'']
        self.chords = {
            #    C = c  e  g
            '1': [5, 7, 9],
            #   dm = d  f  a
            '2': [6, 8, 10],
            #   em = e  g  b
            '3': [7, 9, 11],
            #   F  = f  a  c
            '4': [1, 3, 5],
            #   G  = g  b  d
            '5': [2, 4, 6],
            #   am = a  c  e
            '6': [3, 5, 7],
            #   bd = b  d  f
            '7': [4, 6, 8]
        }

        self.chordname = {
            #    C
            '1': "c",
            #   dm
            '2': "d",
            #   em
            '3': "e",
            #   F
            '4': "f",
            #   G
            '5': "g",
            #   am
            '6': "a",
            #   bd
            '7': "b"
        }

    # Function to rotate a list
    @staticmethod
    def rotate(l, n):
        n = n % len(l)
        return l[-n:] + l[:-n]

    # Function which creates a composition.
    def compose_music(self, fname, difficulty, num_bars, key, multi, debug=False):
        if key == "C":
            # print self.guitar_notes
            pass
        # Alter the allowable notes
        elif key == "G":
            self.guitar_notes[1] = 'fis'
            self.guitar_notes[8] = 'fis\''
            self.guitar_notes = self.rotate(self.guitar_notes, 2)
            # print self.guitar_notes
        elif key == "D":
            self.guitar_notes[1] = 'fis'
            self.guitar_notes[8] = 'fis\''
            self.guitar_notes[5] = 'cis'
            self.guitar_notes[12] = 'cis\''
            self.guitar_notes = self.rotate(self.guitar_notes, -1)
            # print self.guitar_notes
        elif key == "A":
            self.guitar_notes[1] = 'fis'
            self.guitar_notes[8] = 'fis\''
            self.guitar_notes[5] = 'cis'
            self.guitar_notes[12] = 'cis\''
            self.guitar_notes[2] = 'gis'
            self.guitar_notes[9] = 'gis\''
            self.guitar_notes = self.rotate(self.guitar_notes, 2)
            # print self.guitar_notes
        composition = Composition(difficulty, key)
        for i in range(num_bars):
            if debug:
                print "Bar " + str(i)
            # Pick a scale degree at random and create a Chord object
            # Rooted on that degree.
            scale_degree = random.randint(1, 7)
            chord = Chord()
            chord.degree = scale_degree
            measure = Measure()
            measure.chord = chord
            if debug:
                print "Chord: " + str(chord.degree)
            carry_over = False
            while measure.counter < 1.0:
                rhythm_value = random.choice(difficulty.rhythm_values)
                # For easy difficulties, 8th notes are only allowed if
                # There are two in a row.
                if carry_over:
                    rhythm_value = carry_over
                    carry_over = False
                # print "rhythm_value: " + str(rhythm_value.value)
                note = Note(rhythm_value, None)
                if measure.counter + rhythm_value.fraction <= 1:
                    if debug:
                        print (measure.counter * 4)
                    if ((measure.counter + rhythm_value.fraction) * 4
                        ) % 1 in difficulty.sycopations:
                        measure.counter += rhythm_value.fraction
                        # "Coin flip" to decide if note will be rest
                    else:
                        measure.counter += rhythm_value.fraction
                        carry_over = note.rhythm_value

                    if debug:
                        print note.rhythm_value.value
                        print note.pitch

                    if random.randint(0, difficulty.rest_chance):
                        note.rest = True
                        note.rest = False
                        # Decide the pitch of the note
                        note_indicies = range(7)
                        note_index = np.random.choice(note_indicies,
                                                      p=softmax(chord.weights))
                        note.pitch = self.guitar_notes[
                            (4 + chord.degree + note_index)
                            % len(self.guitar_notes)]
                        note.third = self.guitar_notes[
                            (4 + chord.degree + note_index + 2)
                            % len(self.guitar_notes)]
                    else:
                        note.rest = True
                    measure.notes.append(note)

            composition.measures.append(measure)

        # Merge and sort rest notes
        # TODO: fix bug and implement this
        '''
        for j, measure in enumerate(composition.measures):
            for i, note in enumerate(measure.notes[1:]):
                last_note = measure.notes[i - 1]
                if note.rest == True and last_note.rest == True:
                    if note.rhythm_value == last_note.rhythm_value:
                        print j, i
                        print "yay!"
                        print measure.notes[i - 1].rhythm_value.value
                        print measure.notes[i].rhythm_value.value
                        measure.notes.pop(i)
                        measure.notes[i - 1].rhythm_value.value /= 2
                        print measure.notes[i - 1].rhythm_value.value
            composition.measures[j] = measure
        '''

        with open(fname, 'w') as file:
            file.write("\\absolute {")
            file.write("\n")
            for measure in composition.measures:
                for note in measure.notes:
                    if note.pitch:
                        if multi and (random.randint(0, 3) == 2):
                            file.write("<")
                            file.write(note.pitch)
                            file.write(" ")
                            file.write(note.third)
                            file.write(">")
                        else:
                            file.write(note.pitch)
                        file.write(str(note.rhythm_value.value))
                        file.write(" ")
                    else:
                        file.write("r")
                        file.write(str(note.rhythm_value.value))
                        file.write(" ")

            file.write("\n")
            file.write("}")


    def create_ly_old(self, fname, difficulty):
        """Old version of music generation algorithm."""
        # quarter note or eighth note.
        rhythm_values = ['4', '8']
        if difficulty == 'hard':
            rhythm_values = ['4', '8', '16']

        count = 0
        chord_list = []

        with open(fname, 'w') as file:
            file.write("\\absolute {")
            file.write("\n")
            # Create 12 measures
            for i in range(0, 12):
                # Choose the scale degree of the chord for this measure.
                # TODO: half measure chord changes
                scale_degree = random.randint(1, 7)
                chord_list.append(self.chordname[str(scale_degree)])
                chord_tones = self.chords[str(scale_degree)]
                for j in range(1, 5):
                    # There is a 1/4 chance we will use a neighboring note.
                    neighboring_note = random.randint(0, 4)
                    # There is a 1/4 chance we will use a 16th note walk up the scale.
                    walk = random.randint(0, 4)
                    chord_tone_index = random.randint(0, 2)
                    chord_tone_index_2 = random.randint(0, 2)
                    note_index = chord_tones[chord_tone_index]
                    note_index_2 = chord_tones[chord_tone_index_2]
                    rhythm_index = random.randint(0, (len(rhythm_values) - 1))
                    file.write(str(self.guitar_notes[note_index]))
                    file.write(str(rhythm_values[rhythm_index]))
                    file.write(" ")
                    if rhythm_index == 1:
                        if neighboring_note == 1:
                            file.write(str(self.guitar_notes[note_index + 1]))
                            file.write(rhythm_values[rhythm_index])
                        elif walk == 1:
                            file.write(str(self.guitar_notes[int(note_index) + 1]))
                            file.write("16 ")
                            file.write(str(self.guitar_notes[int(note_index) + 2]))
                            file.write("16 ")
                        else:
                            file.write(str(self.guitar_notes[note_index_2]))
                            file.write(" ")
            file.write("\n")
            file.write("}")
            file.write("\n")
            file.write("\\chords { ")
            count = 0
            for i in chord_list:
                file.write(i)
                if count == 0:
                    count += 1
                    file.write("1")
                file.write(" ")
            file.write("}")


@app.route('/')
def index():
    return 'This is the homepage!'


@app.route('/upload/<filename>')
def send_image(filename):
    # return send_file(filename)
    return send_from_directory("images", filename)


@app.route('/notereader', methods=['GET', 'POST'])
def note_reader():
    time_stamp = str(time.time())
    dif = Difficulty("EASY")
    key = "C"
    poly = False
    if request.method == "POST":
        if request.form["submit"] == "rule_based":
            dif = Difficulty(request.form['difficulty'])
            key = request.form['key']
            poly = request.form['poly']
            n_measures = request.form['n_measures']
            # Default number of measures to 16 if it cannot be cast to int
            try:
                n_measures = abs(int(n_measures))
                if n_measures > 32:
                    n_measures = 32

            except:
                n_measures = 16

            music_gen = MusicGenerator()

            # TODO: get directory name from os
            fname = "SomeRandomNotes" + time_stamp + ".ly"

            # TODO: Change to new version
            if poly == "POLY":
                poly = True

            else:
                poly = False

            if request.form['difficulty'] == "MED2":
                music_gen.create_ly_old(fname, "")
                p = subprocess.Popen([
                    "./LilyPond.app/"
                    "Contents/Resources/bin/lilypond",
                    "--png",
                    ("--output=./images/song" + time_stamp),
                    "best-midi.ly"
                ],
                    stdout=PIPE,
                    stderr=PIPE
                )

                p.wait()
                return render_template("main2.html", image_name=('song' + time_stamp + '.png'))
            else:
                # Use try statement in case user tampers with the form values.
                try:
                    music_gen.compose_music(fname, dif, n_measures, key, poly)
                except:
                    music_gen.compose_music(fname, Difficulty("EASY"), n_measures, "C", False)

                p = subprocess.Popen([
                    "./LilyPond.app/"
                    "Contents/Resources/bin/lilypond",
                    "--png",
                    ("--output=./images/song" + time_stamp),
                    fname
                ],
                    stdout=PIPE,
                    stderr=PIPE
                )

                p.wait()
                return render_template("main2.html", image_name=('song' + time_stamp + '.png'))

        # Magenta melody generation

        elif request.form["submit"] == "magenta":
            poly = request.form['poly']
            out_dir = os.path.join(os.path.curdir, 'midi')
            n_steps = 128
            # seed melodies
            # melody = '[60, -2, 60, -2, 67, -2, 67, -2]'
            melody = '[60, -2, 62, -2, 64, -2, 64, -2]'
            mag_path = ''
            if request.form['model'] == "basic_rnn":
                mag_path = os.path.join(os.path.curdir, 'models', 'basic_rnn.mag')
            elif request.form['model'] == "basic_rnn_beatles":
                mag_path = os.path.join(os.path.curdir, 'models', 'basic_rnn_beatles.mag')

            try:
                n_steps = int(request.form["n_steps"])
                if n_steps < 10:
                    n_steps = 10
            except:
                pass

            config = 'basic_rnn'

            # TODO: deal with this in a better way.
            interpreter = '/Users/ianconway/anaconda/envs/tf_env/bin/python'
            melody_gen_path = '/Users/ianconway/Desktop/Projects/magenta/magenta/models/melody_rnn/melody_rnn_generate.py'

            cmd = (
                "{} ".format(interpreter) +
                "{} ".format(melody_gen_path) +
                "--config='{}' ".format(config) +
                "--bundle_file='{}' ".format(mag_path) +
                "--output_dir='{}' ".format(out_dir) +
                "--num_outputs={} ".format(1) +
                "--num_steps={} ".format(n_steps) +
                "--primer_melody='{}'".format(melody)
            )

            print cmd

            p = subprocess.Popen([
                cmd
            ],
                stdout=PIPE,
                stderr=PIPE,
                shell=True
            )

            print p.communicate()
            print p.returncode

            p.wait()

            midi_file = os.listdir("midi")[0]

            midi_file = os.path.join(os.path.curdir, "midi", midi_file)

            subprocess.call("python "
                            "midi2ly.py "
                            "{} -o best-midi.ly".format(midi_file), shell=True)
            os.remove(midi_file)
            # Clean chords out if the mode is set to monophonic
            if poly == False:
                with open("best-midi.ly", "r") as f:
                    lily_lines = f.readlines()
                clear = False
                lines = []
                for line in lily_lines:
                    if line.rstrip() == "trackBchannelBvoiceB = \\relative c {":
                        clear = True
                        continue
                    if line.rstrip() == "trackBchannelBvoiceC = \\relative c {":
                        clear = True
                        continue
                    if not clear:
                        lines.append(line)
                    else:
                        if line.rstrip() == "}":
                            clear = False

                with open("best-midi.ly", "w") as f:
                    f.write(''.join([line for line in lines]))

            p = subprocess.Popen([
                "./LilyPond.app/"
                "Contents/Resources/bin/lilypond",
                "--png",
                ("--output=./images/song" + time_stamp),
                "best-midi.ly"
            ],
                stdout=PIPE,
                stderr=PIPE
            )

            p.wait()
            return render_template("main2.html", image_name=('song' + time_stamp + '.png'))

    else:
        return render_template("main2.html")


if __name__ == "__main__":

    app.run(debug=True, )
    # app.run(threaded=True )
