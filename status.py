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


class status(object):
    '''
    classdocs
    '''
    # Here will be the instance stored.
    __instance = None

    @staticmethod
    def getInstance():
        """ Static access method. """
        if status.__instance == None:
            status()
        return status.__instance

    def __init__(self):
        """ Virtually private constructor. """
        if status.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            status.__instance = self
        self.connectionstatus = False
        self.hourcounter = 0
        self.datetimehourcounter = None

