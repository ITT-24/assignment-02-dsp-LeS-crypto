import pyaudio
import pyglet
from pyglet import clock
from mido import MidiFile, MidiTrack
import re
import numpy as np

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
TICK_SPEED = 2 # 5 might be better

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
        pass # for now
        # if Setting.has_settings:
        #     tick.play()

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

    def create_notes(self):
        """Create an array of notes, parsed from the .mid file"""
        track = self.mido.tracks[0] # TODO: let user select

        notes = {} # { <note>: { "on": 103, "off":161, "time":235 } } 
        time = 0 # time when first turned on
        idx = 0

        for i in range(0, len(track)):
            msg = track[i]
            # print(i, msg)

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
                    if notes[j]["note"] == off_msg.note and "off" not in notes[j]:
                        notes[j]["off"] = off_msg.time # add an off key
                        time += off_msg.time
                        # print("!!", j, notes[j]) 
                        break

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
        Midi_Notes.notes.append(rect)

    def play_note(self):
        pass

notes = Midi_Notes()
# DRAW MIDI-Files using mido see read_midi.py
# note_on channel=0 note=62 velocity=72 time=0.058854166666666666


# Set up audio stream
# reduce chunk size and sampling rate for lower latency
CHUNK_SIZE = 1024  # Number of audio frames per buffer
FORMAT = pyaudio.paInt16  # Audio format
CHANNELS = 1  # Mono audio
# RATE = 44100  # Audio sampling rate (Hz)
RATE = 30000 

class Sound_Wave:
    """Visualising the sound wave of the user-input"""
    # TODO: detect major frequency
    # draw a point for "every" new input
    wave_batch = pyglet.graphics.Batch()
    x = 0 # elongate with time
    default_y = HEIGHT / 2
    # y = freq_in_hertz
    prev_freq = 0

    wave = []
    rect = pyglet.shapes.Rectangle(x, prev_freq, UNIT, UNIT, (173, 186, 255), wave_batch)
    # BUG: redraws this i think
    # line = pyglet.shapes.Line(x, default_y, 0, default_y, width=UNIT,
    #                               color=(198, 24, 232), batch=wave_batch)

    hits = []
    hit_color = (120, 255, 127, 80)

    def on_collision():
        """Check if the frequency matches the midi-notes"""
        current_x = Sound_Wave.rect.x 
        current_y = Sound_Wave.rect.y

        for n in notes.notes:
            if current_x > n.x and current_x < n.x + n.width + UNIT:
                if current_y > n.y and current_y < n.y + n.height + UNIT: # ↑
                    hit = pyglet.shapes.Rectangle(current_x-UNIT, current_y-UNIT, UNIT, UNIT,
                                                Sound_Wave.hit_color, Sound_Wave.wave_batch)
                    Sound_Wave.hits.append(hit)
        Sound_Wave.wave_batch.draw()   

    def update_wave(): # TEMP + kinda works
        midi = Sound_Wave.map_freq_to_midi(Sound_Wave.get_input_frequency())
        if midi != Sound_Wave.prev_freq: # only redraw, when frequency changes
            Sound_Wave.rect.y = midi * UNIT 
            Sound_Wave.rect.x += TICK_SPEED

            rect = pyglet.shapes.Rectangle(Sound_Wave.rect.x, midi*UNIT, UNIT, UNIT,
                                                (173, 186, 255, 80), Sound_Wave.wave_batch)
            Sound_Wave.wave.append(rect)
            # Sound_Wave.create_line(midi)
            Sound_Wave.wave_batch.draw()
        Sound_Wave.on_collision()

    # def create_line(midi):
    #     line = pyglet.shapes.Line(Sound_Wave.x, Sound_Wave.prev_freq, 0, midi, width=UNIT,
    #                               color=(98, 24, 132), batch=Sound_Wave.wave_batch)
    #     # print(line)
    #     line.draw()
    #     Sound_Wave.x += TICK_SPEED

    def map_freq_to_midi(freq: float):
        """Convert the frequency (in Hz) to a (midi) note.
        See: https://newt.phys.unsw.edu.au/jw/notes.html
        m  =  12*log2(fm/440 Hz) + 69"""
        midi = 12*np.log2(freq/440) + 69 # freq: 954HZ = 82.233 -> round to midi
        midi = round(midi, None)
        print(midi)
        return midi 

    def get_input_frequency():
        # from audio-sample.py
        # Read audio data from stream
        data = Setting.stream.read(CHUNK_SIZE)

        # Convert audio data to numpy array
        data = np.frombuffer(data, dtype=np.int16)

        # from dsp.ipynb
        data = data * np.hamming(len(data)) # ??

        # TODO: filter out background noise
            # -> if loud enough
            # https://stackoverflow.com/a/25871132
            # https://gist.github.com/PandaWhoCodes/9f3dc05faee761149842e43b56e6ee8c

        # from sof:365448 (kinda)
        fft_data = np.fft.rfft(data) # get only positive
        peak = np.argmax(np.abs(fft_data)) # get the peak coeffiecients

        # TODO: only do this around max like sof:2649540
        freqs = np.fft.fftfreq(len(fft_data)) # get all frequencies
        freq = freqs[peak] # find peak frequency

        # convert to herz (like sof:365448)
        freq_in_hertz = abs(freq * RATE)
        # print(freq_in_hertz)
        return freq_in_hertz
        

"""via: audio-sample.py
line, = ax.plot(np.zeros(CHUNK_SIZE))

# continuously capture and plot audio singal
while True:
    # Read audio data from stream
    data = stream.read(CHUNK_SIZE)

    # Convert audio data to numpy array
    data = np.frombuffer(data, dtype=np.int16)
    line.set_ydata(data)
"""


# ----- WINDOW INTERACTION ----- #
@window.event
def on_draw():
    window.clear()

    if not Setting.has_settings:
        Setting.create_menu()
    else:
    # Start the Game !!
    # TODO: give start timer
        notes.batch.draw() 
        Sound_Wave.update_wave()
        # Metronome.move_metronome(TICK_SPEED)
        # Sound_Wave.get_input_frequency()
        # Sound_Wave.map_freq_to_midi(945*2)
        

clock.schedule_interval(Metronome.tick, TICK_SPEED)
# i.e. "tick" the Metronome in a resonable interval


@window.event
def on_key_press(symbol, modifiers):
    if symbol == pyglet.window.key.ESCAPE:
        window.close()
        Setting.stream.close()
        pyA.terminate()
    elif not Setting.has_settings: # check if number selected
        key = pyglet.window.key.symbol_string(symbol)
        if (re.match(r"_\d", key)):
            num = key.split("_")[1]
            Setting.open_audio_stream(int(num))
        # _3 oder NUM_1
    


# ----- RUN GAME ----- #
if __name__ == '__main__':
    # init some stuff
    Setting.set_device_info()
    notes.create_notes()
    # print("notes", notes.notes)
    # run the game
    pyglet.app.run()
