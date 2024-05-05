import numpy as np
import pyaudio
import pyglet
import pynput
import re

"""
- detect and react to whistled frequency chirps in real time
    "Frequency chirps are signals that change their
frequency over time, for example “ooouuuiii” for an upwards chirp and “iiiuuuooo”
for a downwards chirp."
- use chirps to navigate (up and down) a list
    - pyglet: 2D application that displays stack of rects -> visuall selection
    - whiste up = up movement
- generalize technique to other applications
    - pynput: trigger key presses (up/down) to nagivate in arbitrary GUI menus by whistling

- [/] (3P) - upwards and downwards whistling are detected correctly and robustly
- [x] (2P) - detection is robust against background noise 
- [ ] (1P) - low latency between input and detection
- [ ] (1P) - the pyglet test program works
- [ ] (1P) - triggered key events work 
"""

WIDTH = 500
HEIGHT = 500 
window = pyglet.window.Window(WIDTH, HEIGHT)

# Set up audio stream
# reduce chunk size and sampling rate for lower latency
CHUNK_SIZE = 1024  # Number of audio frames per buffer
FORMAT = pyaudio.paInt16  # Audio format
CHANNELS = 1  # Mono audio
# RATE = 44100  # Audio sampling rate (Hz)
RATE = 10000
p = pyaudio.PyAudio()

class Stream:
    devices = {}
    stream:pyaudio.Stream = None

    def set_device_info():
        info = p.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')

        for i in range(0, num_devices):
            # via: audio-sample.py
            if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                d = p.get_device_info_by_host_api_device_index(0, i).get('name')
                print(d)
                Stream.devices[i] = d

    def open_audio_stream(idx:int):
        if idx in Stream.devices:
            print(Stream.devices[idx])
            Stream.has_settings = True
            Stream.stream = Stream.get_stream(idx)
            print("strema", Stream.stream)
        else: print("No device with this id")

    def get_stream(device_id:int) -> pyaudio.Stream:
        stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
                input_device_index=device_id)
        return stream
    
    def get_input_frequency(): # see: karaoke.py
        data = Stream.stream.read(CHUNK_SIZE)

        # Convert audio data to numpy array
        data = np.frombuffer(data, dtype=np.int16)

        # from dsp.ipynb
        data = data * np.hamming(len(data)) # ??

        fft_data = np.fft.rfft(data) # get only positive
        peak = np.argmax(np.abs(fft_data)) # get the peak coeffiecients

        freqs = np.fft.fftfreq(len(fft_data)) # get all frequencies
        freq = freqs[peak] # find peak frequency

        freq_in_hertz = abs(freq * RATE)
        return round(freq_in_hertz)


THRESHOLD = 150
CHIRP_LEN = 3
CHIRP_THRESHOLD = 500
class Detector:
    prev_freq = 0 # default value
    chirps = []
    counter = 0

    # TODO: make robuster
    # NOTE: chirp ↑ ~ 1969 to 3353 // chirp ↓ ~ 3372 to 1988 (diff off ~ 1000)
    def find_chirps():
        freq = Stream.get_input_frequency()

        if Detector.prev_freq != 0:
            if freq > Detector.prev_freq + THRESHOLD or freq < Detector.prev_freq - THRESHOLD:
                # print("??", freq)
                if len(Detector.chirps) < CHIRP_LEN:
                    Detector.chirps.append(freq)
                    # print("++")

                elif len(Detector.chirps) >= CHIRP_LEN:
                    # compare first and last
                    if Detector.chirps[0] > freq: # ↓
                        diff = Detector.chirps[0] - freq
                        if diff > CHIRP_THRESHOLD:
                            print("↓", Detector.chirps, freq)
                            Menu.navigate_menu(0)
                    elif Detector.chirps[0] < freq: # ↑
                        diff = freq - Detector.chirps[0]
                        if diff > CHIRP_THRESHOLD:
                            print("↑", Detector.chirps, freq) 
                            Menu.navigate_menu(1)
                    print("...", Detector.chirps)
                    Detector.reset()

                Detector.counter += 1

            else: # reset
                Detector.reset()
                Detector.prev_freq = freq

        else: # init
            Detector.prev_freq = freq
            print("i", freq)

    def reset():
        Detector.counter = 0
        Detector.chirps = []
        Detector.prev_freq = 0
    
    # get input_frequency
    # when change from "silence" -> save freq as previous
    # detect change in frequency -> difference needs to be above threshold
    # chirp = lower to higher or higher to lower

class Menu:
    """A dummy menu"""
    width = 200
    height = 50
    length = 5
    items = []
    unselected = (221, 219, 219)
    selected = (143, 252, 43)
    selected_id = 3

    batch = pyglet.graphics.Batch()

    # def __init__(self) -> None:
    #     self.batch = pyglet.graphics.Batch()
    #     pass

    def init_info():
        pass

    def init_menu():
        for i in range(0, Menu.length+1):
            Menu.create_menu_item(i)
        # Menu.draw_menu()

    def create_menu_item(idx):
        x = Menu.width - 30
        y = HEIGHT - (idx * (HEIGHT/Menu.length) ) + 30 # ↑

        if idx == Menu.selected_id:
            color = Menu.selected
        else: color = Menu.unselected

        rect = pyglet.shapes.Rectangle(x, y, Menu.width, Menu.height,
                                       color, batch=Menu.batch)
        Menu.items.append(rect)

    def draw_menu():
        Menu.batch.draw()

    def navigate_menu(direction):
        old = Menu.items[Menu.selected_id]
        old.color = Menu.unselected

        if direction == 0: # down
            if Menu.selected_id < Menu.length:
                Menu.selected_id += 1
        elif direction == 1: # up
            if Menu.selected_id > 0:
                Menu.selected_id -= 1
        
        # change selection color
        new = Menu.items[Menu.selected_id]
        new.color = Menu.selected

    pass 


# ----- WINDOW INTERACTION ----- #
@window.event
def on_draw():
    window.clear()

    if Stream.stream != None:
        Detector.find_chirps()
        Menu.draw_menu()


@window.event
def on_key_press(symbol, modifiers):
    if symbol == pyglet.window.key.ESCAPE:
        window.close()
    key = pyglet.window.key.symbol_string(symbol)
    if (re.match(r"_\d", key)):
        num = key.split("_")[1]
        Stream.open_audio_stream(int(num))

# ----- RUN GAME ----- #
if __name__ == '__main__':
    # init some stuff
    Stream.set_device_info()
    Menu.init_menu()
    # print("notes", notes.notes)
    # run the game
    pyglet.app.run()