import pyaudio
import pyglet
from pyglet import clock
from mido import MidiFile, MidiTrack
import re

"""
- capture microphone audio
- detect sound's major frequency in real time
- create small audio-based game (e.g. karaoke)
"For example, it could be a karaoke
game in which players have to sing a certain (random, pre-defined, or MIDI) me-
lody, or a game to train playing, singing, or whistling musical notes or intervals."

3P - frequency detection works correctly and robustly
2P - playable (fun) game
1P - low latency btw input and detection
"""

# ----- SET UP ----- 
UNIT = 10 # of the coordinate system
WIDTH = 100 * UNIT
HEIGHT = 127 * UNIT 
window = pyglet.window.Window(WIDTH, HEIGHT)

tick = pyglet.media.load("drumsticks.mp3", streaming=False)
TICK_SPEED = 1

pyA = pyaudio.PyAudio()

# get info about audio devices
settings = pyglet.text.Label(text="<p>Test<p>", x=WIDTH/2, y=HEIGHT-40, anchor_x="center", anchor_y="center")


class Setting:
    """Select audio device"""
    devices = {} # { 0: "Mic"}
    has_settings = False
    stream = None

    def set_device_info():
        info = pyA.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')

        for i in range(0, num_devices):
            # via: audio-sample.py
            if (pyA.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                d = pyA.get_device_info_by_host_api_device_index(0, i).get('name')
                Setting.devices[i] = d
    
    def create_menu(): # TODO create formatted document to display possible devices
        settings.text = str(Setting.devices)
        settings.draw()

    def open_audio_stream(idx:int):
        if idx in Setting.devices:
            print(Setting.devices[idx])
            Setting.has_settings = True

            # create Stream
            Setting.stream = Stream.get_stream(idx)
            print(Setting.stream)

            # NOTE: start game

        else: print("No device with this id")

class Stream:
    # Set up audio stream
    # reduce chunk size and sampling rate for lower latency
    CHUNK_SIZE = 1024  # Number of audio frames per buffer
    FORMAT = pyaudio.paInt16  # Audio format
    CHANNELS = 1  # Mono audio
    RATE = 44100  # Audio sampling rate (Hz)

    def get_stream(device_id:int) -> pyaudio.Stream:
        stream = pyA.open(format=Stream.FORMAT,
                channels=Stream.CHANNELS,
                rate=Stream.RATE,
                input=True,
                frames_per_buffer=Stream.CHUNK_SIZE,
                input_device_index=device_id)
        return stream


class Metronome:
    line = pyglet.shapes.Line(0, 0, 0, HEIGHT, width=UNIT, color=(200, 0, 0))

    def tick(self):
        if Setting.has_settings:
            tick.play()

    def move_metronome(delta_time):
        # ?? Right speed?
        Metronome.line.x += UNIT * delta_time
        Metronome.line.draw()




class Midi_Notes:
    notes = []
    # https://www.twilio.com/en-us/blog/working-with-midi-data-in-python-using-mido
    # https://stackoverflow.com/questions/63105201/python-mido-how-to-get-note-starttime-stoptime-track-in-a-list
    # https://github.com/exeex/midi-visualization/tree/master

    def __init__(self) -> None:
        self.mido = MidiFile("../read_midi/freude.mid") # TODO: load both tracks
        self.batch = pyglet.graphics.Batch()
        # print(self.mido.tracks[0])
        # for msg in self.mido.tracks[0]:
            # get time from last msg -> note_off
            # print(msg)

    def create_notes(self):
        """Create an array of notes, parsed from the .mid file"""
        track = self.mido.tracks[0] # TODO: let user select

        # time = 0
        # print(len(track))
        # for i in range(0, len(track)):
        #     msg = track[i]
        # #     # print(msg)
        #     if msg.type == 'note_on':
        #         print(i, "on", msg.note, ":", msg.time)
        #         on = msg
        #         time += on.time
        #         # get the next note_off-msg with the same note
        #         for j in range(i, len(track)):
        #             msg = track[j]
        #             if msg.type == 'note_off' and msg.note == on.note:
        #                 print(j, "off", msg.note, ":", msg.time)
        #                 off = msg 
        #                 time += off.time
        #                 self.add_new_note(on, off, time)

        #                 break # continue with previous iteration

        # {note: 60, on: 103, off:161}
        # create dict from msg: 
            # if note_on  -> create new entry
            # if note_off -> close last entry without off:value
        notes = {} # { <note>: { "on": 103, "off":161, "time":235 } } 
        time = 0 # time when first turned on
        idx = 0

        for i in range(0, len(track)):
            msg = track[i]
            print(i, msg)

            # create an entry in the note dict, if a note "turns on"
            if msg.type == 'note_on':
                time += msg.time # ??
                notes[idx] = {"note": msg.note, "time": time, "on": msg.time}
                # print("turn on", idx, notes[idx])
                idx += 1

            # check the last entries of the same "turned on" note, and turn if "off" (if not yet done)
            if msg.type == 'note_off':
                off_msg = track[i]
                for j in range(idx-1, -1, -1): # check the last created notes
                    # print("j", notes[j])
                    if notes[j]["note"] == off_msg.note and "off" not in notes[j]:
                        notes[j]["off"] = off_msg.time # add an off key
                        time += off_msg.time
                        print("!!", j, notes[j]) 
                        break
                    # if "off" not in notes[j][off_msg.note]: # until it finds the same note, still open
                        # time += off_msg.time
                        # notes[off_msg.note]["off"] = off_msg.time # add an off key
                        # print("turn off", notes[off_msg.note])
                    #     break

        # create notes
        for n in notes:
            self.add_new_note(notes[n])

        # NOTE: might?? work (ヘ･_･)ヘ┳━┳ 

    # time = msg.time + msg.time + ...
    # for each note-on message, you have to find the corresponding note-off message, 
    # i.e., the next note-off message with the same note and channel.

    # def add_new_note(self, note_on, note_off, time):
    def add_new_note(self, note:dict):
        """Define the location and size of a note"""
        y =  note["note"] * UNIT  # ↑  
        x =  note["time"] / UNIT # → # (note["time"] + note["on"]) / UNIT 
        width = note["off"] / UNIT # (note["off"] - note["on"]) / UNIT # diff btw on off & on time stamp
        height = UNIT 
        color = (200, 0, 130)
        rect = pyglet.shapes.Rectangle(x, y, width, height, color, batch=self.batch)
        # print("rect", rect.x, rect.y, rect.width, rect.height)
        Midi_Notes.notes.append(rect)
        # y =  note_on.note * UNIT  # ↑  
        # x =  (time + note_on.time) / UNIT # → 
        # width = (note_off.time - note_on.time) / UNIT # diff btw on off & on time stamp
        # height = UNIT 
        # color = (200, 0, 130)
        # rect = pyglet.shapes.Rectangle(x, y, width, height, color, batch=self.batch)
        # print("rect", rect.x, rect.y, rect.width, rect.height)
        # Midi_Notes.notes.append(rect)

    def play_note(self):
        pass

notes = Midi_Notes()
# DRAW MIDI-Files using mido see read_midi.py
# note_on channel=0 note=62 velocity=72 time=0.058854166666666666

# ----- WINDOW INTERACTION ----- #
@window.event
def on_draw():
    window.clear()

    if not Setting.has_settings:
        Setting.create_menu()
    else:
    # Start the Game !!
        notes.batch.draw()
        Metronome.move_metronome(TICK_SPEED)

clock.schedule_interval(Metronome.tick, TICK_SPEED)
# i.e. "tick" the Metronome in a resonable interval


@window.event
def on_key_press(symbol, modifiers):
    if symbol == pyglet.window.key.ESCAPE:
        window.close()
    else: # check if number selected
        key = pyglet.window.key.symbol_string(symbol)
        if (re.match(r"_\d", key)):
            num = key.split("_")[1]
            Setting.open_audio_stream(int(num))
    # print(str(pyglet.window.key.symbol_string(symbol)))
    # _3 oder NUM_1
    


# @window.event
# def on_text(text):
#     # only user for series of keystrokes
#         print(text)




# ----- RUN GAME ----- #
if __name__ == '__main__':
    # init some stuff
    Setting.set_device_info()
    notes.create_notes()
    # print("notes", notes.notes)
    # run the game
    pyglet.app.run()
