import numpy as np
import pyaudio
import pyglet
from pynput.keyboard import Key, Controller
import re

# ----- SET UP ----- #

WIDTH = 500
HEIGHT = 500 
window = pyglet.window.Window(WIDTH, HEIGHT)
key_label = pyglet.text.Label("Pressed:", x=10, y=HEIGHT-20)

keyboard = Controller()

# Set up audio stream
# reduce chunk size and sampling rate for lower latency
CHUNK_SIZE = 1024  # Number of audio frames per buffer
FORMAT = pyaudio.paInt16  # Audio format
CHANNELS = 1  # Mono audio
# RATE = 44100  # Audio sampling rate (Hz)
RATE = 10000
p = pyaudio.PyAudio()

# Thresholds for frequency detection and processing
THRESHOLD = 150
CHIRP_LEN = 3
CHIRP_THRESHOLD = 200
VOLUME_THRESHOLD = 30


# ----- DETECTION & INTERACTION ----- #

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

        Menu.init_info()

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
        data = np.frombuffer(data, dtype=np.int16)
        data = data * np.hamming(len(data))

        amp = sum(np.abs(data))/len(data)

        fft_data = np.fft.rfft(data) # get only 1 dimension -> seems to works bettern than fft in this case
        peak = np.argmax(np.abs(fft_data)) # get the peak coeffiecients

        freqs = np.fft.fftfreq(len(fft_data)) # get all frequencies
        freq = freqs[peak] # find peak frequency

        freq_in_hertz = abs(freq * RATE)
        return {"freq": round(freq_in_hertz), "amp": amp}


class Detector:
    prev_freq = 0 # default value
    chirps = []

    # TODO: make robuster
    # NOTE: chirp ↑ ~ 1969 to 3353 // chirp ↓ ~ 3372 to 1988 (diff off ~ 1000)
    def find_chirps():
        input = Stream.get_input_frequency()
        freq = input["freq"]
        amp = input["amp"]
        print(freq)

        if amp < VOLUME_THRESHOLD:
            Detector.reset()

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
                            Key_Trigger.press_down_key()
                    elif Detector.chirps[0] < freq: # ↑
                        diff = freq - Detector.chirps[0]
                        if diff > CHIRP_THRESHOLD:
                            print("↑", Detector.chirps, freq) 
                            Menu.navigate_menu(1)
                            Key_Trigger.press_up_key()
                            # sim keypress
                    print("...", Detector.chirps)
                    Detector.reset()

            else: # reset
                Detector.reset()
                Detector.prev_freq = freq

        else: # init
            Detector.prev_freq = freq
            print("i", freq)

    def reset():
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
    label_batch = pyglet.graphics.Batch()
    labels = []

    def init_info():
        batch = pyglet.graphics.Batch()
        info = pyglet.text.Label("Select the id of your prefered audio device:", 
                                 x=10, y=HEIGHT-20, batch=batch)
        Menu.labels.append(info)
        for idx in Stream.devices:
            info_text = f"ID: {idx} - {Stream.devices[idx]}"
            label = pyglet.text.Label(info_text, x=10, y=HEIGHT-(idx*20)-40, batch=batch)
            Menu.labels.append(label)

        # info_text = "Select the id of your prefered audio device: <br>"
        # for idx in Stream.devices:
        #     info_text += f"<b>ID: {idx} <b> - {Stream.devices[idx]}<br>"
        # # print("info", info_text)
        # document = pyglet.text.decode_html(info_text)
        # layout = pyglet.text.layout.TextLayout(document, x=WIDTH-10, y=HEIGHT-10, 
        #                                     width=WIDTH, height=HEIGHT, batch=batch)
        # Menu.labels.append(layout)
        # NOTE: layout doesn't show up for some reason
    
    def draw_info():
        for l in Menu.labels:
            l.draw()

    def init_menu():
        for i in range(0, Menu.length+1):
            Menu.create_menu_item(i)

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
        print(direction)
        old = Menu.items[Menu.selected_id]

        if direction == 1: # up
            if Menu.selected_id != 1: # 0 is of screen (TODO: fix)
                Menu.selected_id -= 1 # [0] is highest
                Menu.update_colors(old)
        elif direction == 0: # down
            if Menu.selected_id < Menu.length:
                Menu.selected_id += 1
                Menu.update_colors(old)
    

    def update_colors(old):
        old.color = Menu.unselected
        new = Menu.items[Menu.selected_id]
        new.color = Menu.selected


class Key_Trigger:
    """Triggers a key press"""

    def press_up_key():
        keyboard.press(Key.up)
        keyboard.release(Key.up)

    def press_down_key():
        keyboard.press(Key.down)
        keyboard.release(Key.down)


# ----- PYGLET WINDOW ----- #

@window.event
def on_draw():
    window.clear()

    if Stream.stream != None:
        Detector.find_chirps()
        Menu.draw_menu()
        key_label.draw()
    else:
        Menu.draw_info()


@window.event
def on_key_press(symbol, modifiers):
    key = pyglet.window.key.symbol_string(symbol)

    if symbol == pyglet.window.key.ESCAPE:
        window.close()
    # react to simulated key presses
    elif symbol == pyglet.window.key.UP:
        key_label.text = f"Pressed {key}"
        # Menu.navigate_menu(1) # for debug
    elif symbol == pyglet.window.key.DOWN:
        key_label.text = f"Pressed {key}"
        # Menu.navigate_menu(0) # for debug

    # get audio index input
    if (re.match(r"_\d", key)):
        num = key.split("_")[1]
        Stream.open_audio_stream(int(num))


# ----- RUN APPLICATION ----- #

if __name__ == '__main__':
    # init some stuff
    Stream.set_device_info()
    Menu.init_menu()
    # run the game
    pyglet.app.run()