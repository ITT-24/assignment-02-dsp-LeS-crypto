import numpy as np
import pyaudio
import pyglet
import pynput

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

(3P) - upwards and downwards whistling are detected correctly and robustly
(2P) - detection is robust against background noise
(1P) - low latency between input and detection
(1P) - the pyglet test program works
(1P) - triggered key events work 
"""

# make window
# make rect
# get chirps
# move rect up + down

# Set up audio stream
# reduce chunk size and sampling rate for lower latency
CHUNK_SIZE = 1024  # Number of audio frames per buffer
FORMAT = pyaudio.paInt16  # Audio format
CHANNELS = 1  # Mono audio
# RATE = 44100  # Audio sampling rate (Hz)
RATE = 10000
p = pyaudio.PyAudio()

# print info about audio devices
# let user select audio device
info = p.get_host_api_info_by_index(0)
numdevices = info.get('deviceCount')

for i in range(0, numdevices):
    if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
        print("Input Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))

print('select audio device:')
input_device = int(input())

# open audio input stream
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
                input_device_index=input_device)


def get_input_frequency(): # see: karaoke.py
    data = stream.read(CHUNK_SIZE)

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
CHIRP_LEN = 2
CHIRP_THRESHOLD = 500
class Detector:
    prev_freq = 0 # default value
    chirps = []
    counter = 0

    # NOTE: chirp ↑ ~ 1969 to 3353 // chirp ↓ ~ 3372 to 1988 (diff off ~ 1000)
    def find_chirps():
        freq = get_input_frequency()

        if Detector.prev_freq != 0:
            if freq > Detector.prev_freq + THRESHOLD or freq < Detector.prev_freq - THRESHOLD:
                print("??", freq)
                if len(Detector.chirps) < CHIRP_LEN:
                    Detector.chirps.append(freq)
                    print("++")

                elif len(Detector.chirps) >= CHIRP_LEN:
                    # compare first and last
                    if Detector.chirps[0] > freq: # ↓
                        diff = Detector.chirps[0] - freq
                        if diff > CHIRP_THRESHOLD:
                            print("↓", Detector.chirps, freq)
                    elif Detector.chirps[0] < freq: # ↑
                        diff = freq - Detector.chirps[0]
                        if diff > CHIRP_THRESHOLD:
                            print("↑", Detector.chirps, freq) 
                    print("...", Detector.chirps)
                    Detector.reset()

                Detector.counter += 1

            else: # reset
                Detector.reset()
                Detector.prev_freq = freq

        else: # init
            Detector.prev_freq = freq
            print("i", freq)

        # print("f", freq)

    def reset():
        Detector.counter = 0
        Detector.chirps = []
        Detector.prev_freq = 0

        # if change in freq from previous is big enough apppend to chirps
        # if len(chirps) > 10: compair first and last entry
            # if 0 > n -> down
            # if 0 < n -> up
            # check if distance big enoug
        # reset if too long without changes

        # if Detector.prev_freq < freq - THRESHOLD:
        #     print("d", freq)
        #     Detector.prev_freq = freq
        #     pass
        # elif Detector.prev_freq > freq + THRESHOLD:
        #     print("u", freq)
        #     Detector.prev_freq = freq
        # else: print("p", freq)

        # Detector.prev_freq = freq
        # print("f", freq)

        # if  Detector.prev_freq > freq - THRESHOLD:
        #     if len(Detector.downs) < 10:
        #         Detector.downs.append(freq)
        #     else:
        #         if Detector.downs[0] > 
        #         # check first and last entry
        #     # print("d -> ", Chirp_Detector.prev_freq)
        #     pass
        # elif freq > Detector.prev_freq + THRESHOLD:
        #     print("u -> ", Detector.prev_freq)
        # else: print("n")
        # Detector.prev_freq = freq
        # PREV_FREQ = freq
        # print(Chirp_Detector.prev_freq, freq)
    
    # get input_frequency
    # when change from silence -> save freq as previous
    # detect change in frequency -> difference needs to be above threshold (1000/2000?)
    # chirp = lower to higher or higher to lower
    pass

# continuously capture and plot audio singal
while True:
    # Read audio data from stream
    data = stream.read(CHUNK_SIZE)

    # Convert audio data to numpy array
    data = np.frombuffer(data, dtype=np.int16)

    # print(get_input_frequency())
    Detector.find_chirps()

