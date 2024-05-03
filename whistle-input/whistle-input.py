

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