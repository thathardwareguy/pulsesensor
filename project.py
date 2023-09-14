# Import necessary modules
import requests
from RPLCD import CharLCD
from RPi import GPIO
import os
import time
import glob
import Adafruit_ADS1x15
import random

rate = [0]*10
amp = 100
GAIN = 2/3  
curState = 0
stateChanged = 0
GPIO.setwarnings(False)
lcd = CharLCD(numbering_mode=GPIO.BOARD,cols=16, rows=2, pin_rs=40, pin_e=37, pins_data=[35, 33, 31, 29])

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

#API KEY
API_KEY = '95YDYPR7T8KSEOW0'

# Variable for pulse
firstBeat = True
secondBeat = False
sampleCounter = 0
lastBeatTime = 0
lastTime = int(time.time()*1000)
th = 525
P = 512
T = 512
IBI = 600
Pulse = False
adc = Adafruit_ADS1x15.ADS1015()

#ECG
prevtime = time.time()
sentUpSpike = False

def send_to_thingspeak(queries):
    # Send the request to ThingSpeak
    r = requests.get('https://api.thingspeak.com/update', params=queries)
    
    # Verify that ThingSpeak recived our data
    if r.status_code == requests.codes.ok:
        print("Data Received!")
    else:
        print("Error Code: " + str(r.status_code))


# Definition to read sensor data and send it to ThingSpeak
def read_and_send(): 
	# Read temperature, pulse and ECG then set the query string
    temp_c = read_temp_c()
    temp_f = read_temp_f()
    pulse = read_pulse()
    ecg = read_ecg()

    #display result
    display_lcd(temp_c, temp_f)

    queries = {"api_key": API_KEY}

    if temp_c:
        queries['field1'] = temp_c    
    if pulse:
        queries['field2'] = pulse
    if ecg:
        queries['field3'] = ecg
    
    send_to_thingspeak(queries)
    
def display_lcd(temp_c, temp_f):
    lcd.cursor_pos = (0, 0)
    lcd.write_string("Temp: " + temp_c + chr(223) + "C")
    lcd.cursor_pos = (1, 0)
    lcd.write_string("Temp: " + temp_f + chr(223) + "F")

def read_temp_raw():
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines

#CELSIUS CALCULATION
def read_temp_c():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = int(temp_string) / 1000.0 # TEMP_STRING IS THE SENSOR OUTPUT, MAKE SURE IT'S AN INTEGER TO DO THE MATH
        temp_c = str(round(temp_c, 1)) # ROUND THE RESULT TO 1 PLACE AFTER THE DECIMAL, THEN CONVERT IT TO A STRING
        return temp_c

#FAHRENHEIT CALCULATION
def read_temp_f():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_f = (int(temp_string) / 1000.0) * 9.0 / 5.0 + 32.0 # TEMP_STRING IS THE SENSOR OUTPUT, MAKE SURE IT'S AN INTEGER TO DO THE MATH
        temp_f = str(round(temp_f, 1)) # ROUND THE RESULT TO 1 PLACE AFTER THE DECIMAL, THEN CONVERT IT TO A STRING
        return temp_f

#PULSE CALCULATION
def read_pulse(sampleCounter=sampleCounter, lastTime = lastTime, 
               lastBeatTime = lastBeatTime, th = th, secondBeat = secondBeat,
               firstBeat = firstBeat, P = P, T = T, IBI = IBI, Pulse=Pulse):  
    i = 0
    while i < 1000:
        i += 1
        Signal = adc.read_adc(1, gain=GAIN)   
        curTime = int(time.time()*1000)
        sampleCounter += curTime - lastTime
        lastTime = curTime
        N = sampleCounter - lastBeatTime

        if Signal > th and  Signal > P:          
            P = Signal
        
        if Signal < th and N > (IBI/5.0)*3.0 :  
            if Signal < T :                      
                T = Signal                                                 
        
        if N > 250 :                              
            if  (Signal > th) and  (Pulse == False) and  (N > (IBI/5.0)*3.0)  :
                Pulse = 1;                       
                IBI = sampleCounter - lastBeatTime
                lastBeatTime = sampleCounter       

                if secondBeat :                     
                    secondBeat = 0;               
                    for i in range(0,10):             
                        rate[i] = IBI                      

                if firstBeat :                        
                    firstBeat = 0                  
                    secondBeat = 1                  
                    continue                            

                runningTotal = 0;               
                for i in range(0,9):            
                    rate[i] = rate[i+1]       
                    runningTotal += rate[i]      

                rate[9] = IBI;                  
                runningTotal += rate[9]        
                runningTotal /= 10;             
                BPM = 60000/runningTotal       
                print("BPM:" + str(BPM))
                return BPM

        if Signal < th and Pulse == 1 :                    
            amp = P - T                   
            th = amp/2 + T
            T = th
            P = th
            Pulse = 0 
            
        if N > 2500 :
            th = 512
            T = th                  
            P = th                                              
            lastBeatTime = sampleCounter
            firstBeat = 0                     
            secondBeat = 0                   
            print("no beats found")


# ECG
def read_ecg(prevtime = prevtime):
    currtime = time.time()
    
    if (currtime - prevtime >= 5) and sentUpSpike == False:
        up_spike = random.uniform(200,300)
        return up_spike
    
    if (currtime - prevtime >= 5) and sentUpSpike == True:
        down_spike = random.uniform(-100, -200)
        prevtime = currtime
        return down_spike
    
    val = random.randrange(30,80)

    return val

if __name__ == '__main__':
    while True:
        read_and_send()