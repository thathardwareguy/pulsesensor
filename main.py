from pulsesensor import Pulsesensor
import time

# Create a Pulsesensor instance with the desired settings
p = Pulsesensor(channel=0, ads1115_address=0x48)

# Start the BPM measurement in a separate thread
p.startAsyncBPM()

try:
    while True:
        bpm = p.BPM
        if bpm > 0:
            print("BPM: %d" % bpm)
        else:
            print("No Heartbeat found")
        time.sleep(1)
except KeyboardInterrupt:
    # Stop the BPM measurement when the program is terminated
    p.stopAsyncBPM()
