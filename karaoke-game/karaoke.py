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

- [/] (3P) - frequency detection works correctly and robustly
- [/] (2P) - playable (fun) game
- [?] (1P) - low latency btw input and detection

https://timsainburg.com/noise-reduction-python.html
https://github.com/timsainb/noisereduce/issues/44
https://github.com/exeex/midi-visualization/blob/master/roll.py
Visualize WAVE FILE: https://youtu.be/oSQTBq1fdTE?si=84wsqSnMRPZXcFKP

"""

# ----- SET UP ----- 
UNIT = 10 # of the coordinate system
WIDTH = 300 * UNIT
HEIGHT = 127 * UNIT 
window = pyglet.window.Window(WIDTH, HEIGHT)

# tick = pyglet.media.load("drumsticks.mp3", streaming=False)
TICK_SPEED = 2 # 5 might be better

pyA = pyaudio.PyAudio()

# get info about audio devices
settings = pyglet.text.Label(text="<p>Test<p>", x=WIDTH/2, y=HEIGHT-40, anchor_x="center", anchor_y="center")


class Setting:
    """Select audio device"""
    devices = {} # { 0: "Mic"}
    has_settings = False
    stream = None

    labels = []
    songs = {0: "berge.mid", 1: "freude.mid"}
    select_count = 0
    notes = None

    def set_device_info():
        info = pyA.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')

        for i in range(0, num_devices):
            # via: audio-sample.py
            if (pyA.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                d = pyA.get_device_info_by_host_api_device_index(0, i).get('name')
                Setting.devices[i] = d
        Setting.init_info()
    
    def create_menu(): # TODO create formatted document to display possible devices
        # settings.text = str(Setting.devices)
        # settings.draw()
        for l in Setting.labels:
            # print(l)
            l.draw()

    def open_audio_stream(idx:int):
        if idx in Setting.devices:
            print(Setting.devices[idx])
            # Setting.has_settings = True
            # create Stream
            Setting.stream = Stream.get_stream(idx)
        else: print("No device with this id")

    def init_info():
        """Create an info text"""
        batch = pyglet.graphics.Batch()
        info = pyglet.text.Label("First select the id of your prefered audio device:", 
                                 x=10, y=HEIGHT-20, batch=batch)
        Setting.labels.append(info)
        for idx in Setting.devices:
            info_text = f"ID: {idx} - {Setting.devices[idx]}"
            label = pyglet.text.Label(info_text, x=10, y=HEIGHT-(idx*20)-40, batch=batch)
            Setting.labels.append(label)

        song = pyglet.text.Label("Then select the song you want to sing:",
                                 x=WIDTH/2, y=HEIGHT-20, batch=batch)
        Setting.labels.append(song)
        for idx in Setting.songs:
            info_text = f"ID: {idx} - {Setting.songs[idx]}"
            label = pyglet.text.Label(info_text, x=WIDTH/2, y=HEIGHT-(idx*20)-40, batch=batch)
            Setting.labels.append(label)

        start = pyglet.text.Label("", x=WIDTH/2, y=HEIGHT/2, anchor_x="center",batch=batch) # preload
        Setting.labels.append(start)

    def set_choice(idx:int):
        if Setting.select_count == 0: # set audio device
            Setting.open_audio_stream(idx)
            Setting.hightlight_choice(idx, 1) # 0 = info
            Setting.select_count += 1
        else: # set song
            track = Setting.songs[idx]
            notes.create_notes(track)
            Setting.hightlight_choice(idx, len(Setting.devices)+2)
            Setting.start_game()
            # Setting.has_settings = True

    def hightlight_choice(idx:int, offset):
        label = Setting.labels[idx+offset]
        print("l", label)
        label.color = (0, 255, 0)

    def start_game():
        Setting.labels[-1].text = 'Press "Enter" to start'

        
    
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
    """Create a visualisation of the midi notes"""
    notes = []
    # https://www.twilio.com/en-us/blog/working-with-midi-data-in-python-using-mido
    # https://stackoverflow.com/questions/63105201/python-mido-how-to-get-note-starttime-stoptime-track-in-a-list
    # https://github.com/exeex/midi-visualization/tree/master

    def __init__(self) -> None:
        # self.mido = MidiFile(f"../read_midi/{track_name}") 
        self.batch = pyglet.graphics.Batch()

    def create_notes(self, track_name:str):
        """Create an array of notes, parsed from the .mid file"""
        mido = MidiFile(f"../read_midi/{track_name}")
        track = mido.tracks[0]

        notes = {} # form: { <note>: { "on": 103, "off":161, "time":235 } } 
        time = 0 # track time
        idx = 0

        for i in range(0, len(track)):
            msg = track[i]
            # print(i, msg)

            # create an entry in the note dict, if a note "turns on"
            if msg.type == 'note_on':
                time += msg.time 
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

    def add_new_note(self, note:dict):
        """Define the location and size of a note"""
        y =  note["note"] * UNIT  # ↑  
        x =  note["time"] / UNIT # → # (note["time"] + note["on"]) / UNIT 
        width = note["off"] / UNIT # (note["off"] - note["on"]) / UNIT # diff btw on off & on time stamp
        height = UNIT 
        color = (200, 0, 130)
        rect = pyglet.shapes.Rectangle(x, y, width, height, color, batch=self.batch)
        Midi_Notes.notes.append(rect)
        print("m",note["note"], "->", y)

    def play_note(self):
        pass

notes = Midi_Notes()
# DRAW MIDI-Files using mido see read_midi.py
# note_on: channel=0 note=62 velocity=72 time=0.058854166666666666

# Set up audio stream
# reduce chunk size and sampling rate for lower latency
CHUNK_SIZE = 1024  # Number of audio frames per buffer
FORMAT = pyaudio.paInt16  # Audio format
CHANNELS = 1  # Mono audio
RATE = 30000 # 44100  # Audio sampling rate (Hz)
VOLUME_TRESHOLD = 150

class Sound_Wave:
    """Visualising the "sound wave" of the user-input"""
    # TODO: detect major frequency
    # draw a point for "every" new input
    wave_batch = pyglet.graphics.Batch()
    x = 0 # elongate with time
    default_y = HEIGHT / 2
    # y = freq_in_hertz
    prev_freq = 0

    wave = []
    rect = pyglet.shapes.Rectangle(x, prev_freq, UNIT, UNIT, (173, 186, 255), wave_batch)

    hits = []
    hit_color = (120, 255, 127, 100)

    def on_collision():
        """Check if the frequency matches the midi-notes"""
        current_x = Sound_Wave.rect.x 
        current_y = Sound_Wave.rect.y

        for n in notes.notes:
            if current_x > n.x and current_x < n.x + n.width + UNIT: # →
                if current_y > n.y and current_y < n.y + n.height + UNIT: # ↑
                    # draw a hit
                    hit = pyglet.shapes.Rectangle(current_x, current_y, UNIT, UNIT,
                                                Sound_Wave.hit_color, Sound_Wave.wave_batch)
                    Sound_Wave.hits.append(hit)
            # TODO: doesn't work on all, but on some??
        Sound_Wave.wave_batch.draw()   

    def update_wave():
        sound = Sound_Wave.get_input_frequency()

        if sound["amp"] > VOLUME_TRESHOLD:
            midi = Sound_Wave.map_freq_to_midi(sound["freq"])
            color = (173, 186, 255)

            Sound_Wave.rect.y = midi * UNIT # map to coordinates
            print("?", midi, "->", Sound_Wave.rect.y)
            Sound_Wave.rect.x += TICK_SPEED
            rect = pyglet.shapes.Rectangle(Sound_Wave.rect.x, midi*UNIT, UNIT, UNIT,
                                            color, Sound_Wave.wave_batch)
            Sound_Wave.wave.append(rect)
            Sound_Wave.on_collision()
            # draw sound + do collision
            pass
        else: # silence
            Sound_Wave.rect.x += TICK_SPEED # advance time

        Sound_Wave.wave_batch.draw()


    def map_freq_to_midi(freq: float):
        """Convert the frequency (in Hz) to a (midi) note.
        See: https://newt.phys.unsw.edu.au/jw/notes.html
        m  =  12*log2(fm/440 Hz) + 69"""
        midi = 12*np.log2(freq/440) + 69 # freq: 954HZ = 82.233 -> round to midi
        print("!", freq, "->", midi)
        # midi = round(midi)
        return midi 

    def get_input_frequency() -> dict: # partially from audio-sample.py
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

        # find the amplitude -> if high enough continue to find frequency
        # (see: https://stackoverflow.com/a/51436401 )
        amp = sum(np.abs(data))/len(data)
        print("amp", amp)

        # (see https://stackoverflow.com/a/3695448) (kinda)
        fft_data = np.fft.rfft(data) # get only positive
        peak = np.argmax(np.abs(fft_data)) # get the peak coeffiecients

        # TODO: only do this around max (see https://stackoverflow.com/a/2649540)
        freqs = np.fft.fftfreq(len(fft_data)) # get all frequencies
        freq = freqs[peak] # find peak frequency

        # convert to herz (see https://stackoverflow.com/a/3695448)
        freq_in_hertz = abs(freq * RATE)
        # else: freq_in_hertz = None

        return {"freq": freq_in_hertz, "amp": amp}
    

# ----- WINDOW INTERACTION ----- #
@window.event
def on_draw():
    window.clear()

    if not Setting.has_settings:
        Setting.create_menu()

    else: # Update the Game !!
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
    # notes.create_notes() # moved
    # print("notes", notes.notes)
    # run the game
    pyglet.app.run()
