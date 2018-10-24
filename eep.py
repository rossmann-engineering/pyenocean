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


class eep(object):
    '''
    classdocs
    '''
    # Here will be the instance stored.
    __instance = None

    @staticmethod
    def getInstance():
        """ Static access method. """
        if eep.__instance == None:
            eep()
        return eep.__instance

    def __init__(self):
        """ Virtually private constructor. """
        if eep.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            eep.__instance = self
        self.profiles = list()

    def readeep(self):
        with open('eep.json') as json_data:
            d = json.load(json_data)
            if ('profiles' in d):
                self.profiles = (d['profiles'])

class eepdevice():
    def __init__(self):
        self.deviceid = str()
        self.devicename = str()
        self.deviceeep = str()

class eepdataa():
    def __init__(self):
        self.name = str()
        self.shortcut = str()
        self.description = str()
        self.value