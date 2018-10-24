'''
Created on 12.01.2018

@author: Stefan Rossmann
'''
import csv
import logging
from logging.handlers import RotatingFileHandler
import os
import traceback
import datetime

LOG_FILENAME = 'logdata.txt'

my_logger1 = logging.getLogger('MyLogger')
my_logger1.setLevel(logging.DEBUG)
my_logger1.propagate = False

# Add the log message handler to the logger
handler1 = logging.handlers.RotatingFileHandler(
LOG_FILENAME, maxBytes=20000000, backupCount=5)
formatter1 = logging.Formatter("%(asctime)s;%(message)s",
                                      "%Y-%m-%d %H:%M:%S")
handler1.setFormatter(formatter1)
my_logger1.addHandler(handler1)

def logData(dataToWrite):
    try:
        # Set up a specific logger with our desired output level

        my_logger1.debug(dataToWrite)

        print (dataToWrite)

    except:
        pass



