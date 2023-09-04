import time
import threading
from ADS1115 import ADS1115  # Import the ADS1115 library here

class Pulsesensor:
    def __init__(self, channel=0, ads1115_address=0x48):
        self.channel = channel
        self.BPM = 0
        self.ads1115 = ADS1115(address=ads1115_address)
        self.thread = None

    def getBPMLoop(self):
        # Rest of the getBPMLoop code here...
        rate = [0] * 10         # Array to hold the last 10 IBI values
        sampleCounter = 0       # Used to determine pulse timing
        lastBeatTime = 0        # Used to find IBI
        P = 512                 # Used to find peak in pulse wave, seeded
        T = 512                 # Used to find trough in pulse wave, seeded
        thresh = 525            # Used to find the instant moment of a heartbeat, seeded
        amp = 100               # Used to hold amplitude of pulse waveform, seeded
        firstBeat = True        # Used to seed the rate array, so we start up with a reasonable BPM
        secondBeat = False      # Used to seed the rate array, so we start up with a reasonable BPM

        IBI = 600               # Int that holds the time interval between beats! Must be seeded!
        Pulse = False           # "True" when a live heartbeat is detected. "False" when not a "live beat". 
        lastTime = int(time.time() * 1000)
        
        while not self.thread.stopped:
            Signal = self.ads1115.read(self.channel)
            currentTime = int(time.time() * 1000)
            
            sampleCounter += currentTime - lastTime
            lastTime = currentTime
            
            N = sampleCounter - lastBeatTime

            # Find the peak and trough of the pulse wave
            if Signal < thresh and N > (IBI / 5.0) * 3:  # Avoid dichrotic noise by waiting 3/5 of last IBI
                if Signal < T:                          # T is the trough
                    T = Signal                          # Keep track of the lowest point in pulse wave 

            if Signal > thresh and Signal > P:
                P = Signal

            # Signal surges up in value every time there is a pulse
            if N > 250:                                 # Avoid high-frequency noise
                if Signal > thresh and Pulse == False and N > (IBI / 5.0) * 3:       
                    Pulse = True                        # Set the Pulse flag when we think there is a pulse
                    IBI = sampleCounter - lastBeatTime  # Measure time between beats in ms
                    lastBeatTime = sampleCounter        # Keep track of time for the next pulse

                    if secondBeat:                      # If this is the second beat, if secondBeat == TRUE
                        secondBeat = False              # Clear secondBeat flag
                        for i in range(len(rate)):      # Seed the running total to get a realistic BPM at startup
                            rate[i] = IBI

                    if firstBeat:                       # If it's the first time we found a beat, if firstBeat == TRUE
                        firstBeat = False               # Clear firstBeat flag
                        secondBeat = True               # Set the second beat flag
                        continue

                    # Keep a running total of the last 10 IBI values  
                    rate[:-1] = rate[1:]                # Shift data in the rate array
                    rate[-1] = IBI                      # Add the latest IBI to the rate array
                    runningTotal = sum(rate)            # Add up the oldest IBI values

                    runningTotal /= len(rate)           # Average the IBI values 
                    self.BPM = 60000 / runningTotal     # How many beats can fit into a minute? That's BPM!

            if Signal < thresh and Pulse == True:       # When the values are going down, the beat is over
                Pulse = False                           # Reset the Pulse flag so we can do it again
                amp = P - T                             # Get the amplitude of the pulse wave
                thresh = amp / 2 + T                    # Set thresh at 50% of the amplitude
                P = thresh                              # Reset these for the next time
                T = thresh

            if N > 2500:                                # If 2.5 seconds go by without a beat
                thresh = 512                            # Set thresh default
                P = 512                                 # Set P default
                T = 512                                 # Set T default
                lastBeatTime = sampleCounter            # Bring the lastBeatTime up to date        
                firstBeat = True                        # Set these to avoid noise
                secondBeat = False                      # When we get the heartbeat back
                self.BPM = 0

            time.sleep(0.005)

    def startAsyncBPM(self):
        self.thread = threading.Thread(target=self.getBPMLoop)
        self.thread.stopped = False
        self.thread.start()
        return

    def stopAsyncBPM(self):
        self.thread.stopped = True
        self.BPM = 0
        return
