import pyaudio
import pyglet
from mido import MidiFile
import re
import numpy as np

# ----- SET UP ----- 
UNIT = 10 # of the coordinate system
WIDTH = 200 * UNIT
HEIGHT = 127 * UNIT 
window = pyglet.window.Window(WIDTH, HEIGHT)
LAYOUT_OFFSET = 40
LINE_HEIGHT = 20

# Colors
HIT_COLOR = (0, 255, 0) # green
MIDI_COLOR = (200, 0, 130) # pink
WAVE_COLOR = (173, 186, 255) # blueish

TICK_SPEED = 5 # 5 might be better
VOLUME_TRESHOLD = 50

pyA = pyaudio.PyAudio()

# get info about audio devices
settings = pyglet.text.Label(text="<p>Test<p>", x=WIDTH/2, y=HEIGHT-40, anchor_x="center", anchor_y="center")

# ----- SETTINGS, DETECTION & VISUALISATION  ----- #

class Setting:
    """Select audio device"""
    devices = {} # { 0: "Mic"}
    has_settings = False
    stream = None

    labels = []
    songs = {0: "berge.mid", 1: "freude.mid"}
    select_count = 0
    notes = None

    selected_track = None

    def set_device_info():
        info = pyA.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')

        for i in range(0, num_devices):
            # via: audio-sample.py
            if (pyA.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                d = pyA.get_device_info_by_host_api_device_index(0, i).get('name')
                Setting.devices[i] = d
        Setting.init_info()
    
    def create_menu():

        for label in Setting.labels:
            label.draw()

    def open_audio_stream(idx:int):
        if idx in Setting.devices:
            print(Setting.devices[idx])
            # create Stream
            Setting.stream = Stream.get_stream(idx)
        else: print("No device with this id")

    def init_info():
        """Create an info text menu thing"""
        batch = pyglet.graphics.Batch()
        info = pyglet.text.Label("First select the id of your prefered audio device:", 
                                 x=UNIT, y=HEIGHT-20, batch=batch)
        Setting.labels.append(info)
        for idx in Setting.devices:
            info_text = f"ID: {idx} - {Setting.devices[idx]}"
            label = pyglet.text.Label(info_text, x=UNIT, y=HEIGHT-(idx*LINE_HEIGHT)-LAYOUT_OFFSET, batch=batch)
            Setting.labels.append(label)

        song = pyglet.text.Label("Then select the song you want to sing:",
                                 x=WIDTH/2, y=HEIGHT-20, batch=batch)
        Setting.labels.append(song)
        for idx in Setting.songs:
            info_text = f"ID: {idx} - {Setting.songs[idx]}"
            label = pyglet.text.Label(info_text, x=WIDTH/2, y=HEIGHT-(idx*LINE_HEIGHT)-LAYOUT_OFFSET, batch=batch)
            Setting.labels.append(label)

        start = pyglet.text.Label("", x=WIDTH/2, y=HEIGHT/2, anchor_x="center",batch=batch) # preload
        Setting.labels.append(start)

    def set_choice(idx:int):
        if Setting.select_count == 0: # set audio device
            Setting.open_audio_stream(idx)
            Setting.hightlight_choice(idx, 1) # 0 = info
            Setting.select_count += 1
        else: # set song
            Setting.selected_track = Setting.songs[idx]
            Notes.create_notes(Setting.selected_track)
            Setting.hightlight_choice(idx, len(Setting.devices)+2)
            Setting.start_game()

    def hightlight_choice(idx:int, offset):
        label = Setting.labels[idx+offset]
        print("l", label)
        label.color = HIT_COLOR

    def start_game():
        Setting.labels[-1].text = 'Press "Enter" to start'

    def get_end_label() -> pyglet.text.Label:
        points = len(Sound_Wave.hits)
        end_text = f"{points} point! Good job :D ... now press ESC to quit."
        return pyglet.text.Label(end_text, x=WIDTH/2, y=HEIGHT/2, 
                                      anchor_x="center", anchor_y="center")
    
    
class Stream:
    # Set up audio stream
    # reduce chunk size and sampling rate for lower latency
    CHUNK_SIZE = 1024  # Number of audio frames per buffer
    FORMAT = pyaudio.paInt16  # Audio format
    CHANNELS = 1  # Mono audio
    RATE = 30000 # 44100  # Audio sampling rate (Hz)

    def get_stream(device_id:int) -> pyaudio.Stream:
        stream = pyA.open(format=Stream.FORMAT,
                channels=Stream.CHANNELS,
                rate=Stream.RATE,
                input=True,
                frames_per_buffer=Stream.CHUNK_SIZE,
                input_device_index=device_id)
        return stream


class Midi_Notes:
    """Create a visualisation of the midi notes"""
    notes = {} # form: { <note>: { "on": 103, "off":161, "time":235 } }
    game_notes = []

    def __init__(self) -> None: 
        self.batch = pyglet.graphics.Batch()

    def create_notes(self, track_name:str):
        """Create an array of notes, parsed from the .mid file"""
        mido = MidiFile(f"../read_midi/{track_name}")
        # -> note_on: channel=0 note=62 velocity=72 time=0.058854166666666666
        track = mido.tracks[0]
        time = 0 # track time
        idx = 0

        for i in range(0, len(track)):
            msg = track[i]

            # create an entry in the note dict, if a note "turns on"
            if msg.type == 'note_on':
                time += msg.time 
                Midi_Notes.notes[idx] = {"note": msg.note, "time": time, "on": msg.time}
                # print("turn on", idx, notes[idx])
                idx += 1

            # check the last entries of the same "turned on" note, and turn if "off" (if not yet done)
            if msg.type == 'note_off':
                off_msg = track[i]
                for j in range(idx-1, -1, -1): # check the last created notes
                    if Midi_Notes.notes[j]["note"] == off_msg.note and "off" not in Midi_Notes.notes[j]:
                        Midi_Notes.notes[j]["off"] = off_msg.time # add an off key
                        time += off_msg.time
                        # print("!!", j, notes[j]) 
                        break

        # create notes
        for n in Midi_Notes.notes:
            self.add_new_note(Midi_Notes.notes[n])
    # time = msg.time + msg.time + ...
    # for each note-on message, you have to find the corresponding note-off message, 
    # i.e., the next note-off message with the same note and channel.

    def add_new_note(self, note:dict):
        """Define the location and size of a note"""  
        x =  note["time"] / UNIT # → # (note["time"] + note["on"]) / UNIT 
        y =  note["note"] * UNIT  # ↑
        width = note["off"] / UNIT # (note["off"] - note["on"]) / UNIT # diff btw on off & on time stamp
        height = UNIT 
        rect = pyglet.shapes.Rectangle(x, y, width, height, MIDI_COLOR, batch=self.batch)
        Midi_Notes.game_notes.append(rect)
        # print("m",note["note"], "->", y)

Notes = Midi_Notes() # refactor?


class Sound_Wave:
    """Visualising the "sound wave" of the user-input as a Rectangle"""

    wave = []
    wave_batch = pyglet.graphics.Batch()
    
    x = 0 # elongate with time
    y = 0
    default_y = HEIGHT / 2
    rect = pyglet.shapes.Rectangle(x, y, UNIT, UNIT, WAVE_COLOR, wave_batch)

    hits = []

    def on_collision():
        """Check if the frequency matches the midi-notes"""
        current_x = Sound_Wave.rect.x 
        current_y = Sound_Wave.rect.y

        for n in Midi_Notes.notes:
            midi = Midi_Notes.notes[n]
            # check if the right note is hit at the right time
            if current_x > midi["time"]/UNIT and current_x < (midi["time"] + midi["off"])/UNIT:
                if current_y >= ((midi["note"]*UNIT)) and current_y < ((midi["note"]*UNIT)+UNIT):
                    # # draw a hit
                    # print(current_y <= ((midi["note"]+UNIT)*UNIT) and current_y >= ((midi["note"]-UNIT)*UNIT))
                    # print(f"{((midi["note"]*UNIT))} > {current_y} < {((midi["note"]*UNIT)+UNIT)}")
                    hit = pyglet.shapes.Rectangle(current_x, current_y, UNIT, UNIT,
                                                    HIT_COLOR, Sound_Wave.wave_batch)
                    Sound_Wave.hits.append(hit)
    
        Sound_Wave.wave_batch.draw()   

    def update_wave():
        sound = Sound_Wave.get_input_frequency()

        if sound["amp"] > VOLUME_TRESHOLD: # only update if sound high enough
            midi = Sound_Wave.map_freq_to_midi(sound["freq"])
            Sound_Wave.rect.y = midi * UNIT # map to coordinates
            Sound_Wave.rect.x += TICK_SPEED # advance time
            rect = pyglet.shapes.Rectangle(Sound_Wave.rect.x, midi*UNIT, UNIT, UNIT,
                                            WAVE_COLOR, Sound_Wave.wave_batch)
            Sound_Wave.wave.append(rect)
            Sound_Wave.on_collision()
            pass
        else: # silence
            Sound_Wave.rect.x += TICK_SPEED # advance time

        Sound_Wave.wave_batch.draw()


    def map_freq_to_midi(freq: float):
        """Convert the frequency (in Hz) to a (midi) note. See: https://newt.phys.unsw.edu.au/jw/notes.html
        m  =  12*log2(fm/440 Hz) + 69."""
        midi = 12*np.log2(freq/440) + 69 # freq: 954HZ = 82.233 -> round to midi
        midi = round(midi)
        # print("!", freq , "hrz", "->", midi)
        return midi 

    def get_input_frequency() -> dict: # partially from audio-sample.py
        # Read audio data from stream
        data = Setting.stream.read(Stream.CHUNK_SIZE)

        # Convert audio data to numpy array
        data = np.frombuffer(data, dtype=np.int16)

        # from dsp.ipynb
        data = data * np.hamming(len(data))

        # find the amplitude -> later used in update_wave())
        # (see: https://stackoverflow.com/a/51436401 )
        amp = sum(np.abs(data))/len(data)
        # print("amp", amp)

        # (see https://stackoverflow.com/a/3695448) (kinda)
        fft_data = np.fft.fft(data)
        peak = np.argmax(np.abs(fft_data)) # get the peak coeffiecients

        # (see https://stackoverflow.com/a/2649540)
        freqs = np.fft.fftfreq(len(fft_data)) # get all frequencies
        freq = freqs[peak] # find peak frequency

        # convert to herz (see https://stackoverflow.com/a/3695448)
        freq_in_hertz = abs(freq * Stream.RATE)

        return {"freq": freq_in_hertz, "amp": amp}
    

# ----- WINDOW INTERACTION ----- #

@window.event
def on_draw():
    window.clear()

    if not Setting.has_settings:
        Setting.create_menu()

    else: # Update the Game !!
        if Sound_Wave.rect.x < WIDTH:
            Notes.batch.draw()
            Sound_Wave.update_wave()
        else:
            label = Setting.get_end_label()
            label.draw()


@window.event
def on_key_press(symbol, modifiers):
    if symbol == pyglet.window.key.ESCAPE:
        window.close()
        pyA.terminate()
    elif not Setting.has_settings: # check if number selected
        key = pyglet.window.key.symbol_string(symbol)
        if (re.match(r"_\d", key)):
            num = key.split("_")[1] # syntax: _3 oder NUM_1
            Setting.set_choice(int(num))

        elif symbol == pyglet.window.key.ENTER:
            # start the game
            Setting.has_settings = True
    


# ----- RUN GAME ----- #
if __name__ == '__main__':
    # init some stuff
    Setting.set_device_info()
    pyglet.app.run()


""" old collision detection
        # for n in Midi_Notes.game_notes:
        #     if current_x + Sound_Wave.rect.width > n.x and current_x < n.x + n.width:
        #         if current_y + Sound_Wave.rect.height > n.x and current_y < n.y + n.height:
            # if current_x > n.x and current_x < n.x + n.width + UNIT: # →
            #     if current_y > n.y and current_y < n.y + n.height + UNIT: # ↑
"""