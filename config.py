'''
Created on 14.01.2018

@author: Stefan Rossmann
'''
import json
from warnings import catch_warnings
import threading
from collections import OrderedDict
import copy
import datetime
import traceback
import os


class config(object):
    '''
    classdocs
    '''
    # Here will be the instance stored.
    __instance = None

    @staticmethod
    def getInstance():
        """ Static access method. """
        if config.__instance == None:
            config()
        return config.__instance

    def __init__(self):
        """ Virtually private constructor. """
        if config.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            config.__instance = self
        self.serialPort = 'COM12'
        self.baudrate = 57600
        self.pythonswversion = 'error'
        self.devices = list()

    def readconfig(self):
        with open('config.json') as json_data:
            d = json.load(json_data)
            self.baudrate = (d['baudrate'])
            self.serialPort = (d['serialPort'])
            if ('devices' in d):
                self.devices = (d['devices'])

    def readVersion(self):
        try:
            with open('version.json') as json_data:
                d = json.load(json_data)
                self.pythonswversion = (d['pythonswversion'])

        except Exception:
            self.pythonswversion = 'error'

    def writePythonSWVersion(self):
        try:
            with open('version.json', 'w') as f:
                data = OrderedDict()
                data['pythonswversion'] = '{0:%Y-%m-%d}'.format(datetime.datetime.now())
                json.dump(data, f, indent=2)
                f.write("\n")
        except Exception:
            pass