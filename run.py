import threading
import webserver
import enocean
import sys
import config
import threading
import datetime
import status

#Write Softwareversion (commandline argument "writeswversion"
if (len(sys.argv) > 1):
    for i in range(1, len(sys.argv)):
        if (sys.argv[i] == 'writeswversion'):
            config.config.getInstance().writePythonSWVersion()

thread2 = threading.Thread(target=webserver.start, args=())
thread2.start()

enocean = enocean.Enocean()
enocean.connect()
enocean.read()

datatosend = dict()

enocean.sendMessage("Smart Plug", datatosend, 1)

def timerfunction():
    #Check the counter if the hour has changed
    if (datetime.datetime.now().hour <> status.status.getInstance().datetimehourcounter):
        status.status.getInstance().hourcounter = 0

t = threading.Timer(600, timerfunction)


