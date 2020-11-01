from flask import Flask, flash, redirect, render_template, request, session, abort
import os
import json
import time
import config
import datalogger
import status
import database
import datetime

app = Flask(__name__)


#----------------------This is the Main Page
@app.route('/', methods=['GET', 'POST'])
def index():
    parameter = dict()
    configuration = config.config.getInstance()
    configuration.readVersion()

    parameter['swversion'] = configuration.pythonswversion
    parameter['connectionstatus'] = status.status.getInstance().connectionstatus
    parameter['eventcounter'] = database.geteventcountertotal()
    parameter['eventcounterhour'] = database.geteventcounterlasthour()
    showcontentlogfile = 1000;
    return render_template('index.html', parameter = parameter)

#----------------------This is the Log-File Page
@app.route('/logfile', methods=['GET', 'POST'])
def logfile():
    showcontentlogfile = 1000;
    with open("logdata.txt", "r") as f:
        content = f.read()
        contentsplitline = content.splitlines()
        content = ""
        if (showcontentlogfile > len(contentsplitline)):
            showcontentlogfile = len(contentsplitline)
        for i in range(0, showcontentlogfile):
            content = content + str(contentsplitline[len(contentsplitline) - i - 1]) + '\n'
    return render_template('logfile.html', content=content)


@app.route('/statistics', methods=['GET', 'POST'])
def statistics():

    parameter = database.geteventcounterdeviceid()
    parameter['currenthour'] = datetime.datetime.now().hour
    parameter['eventcountercurrenthour'] = database.geteventcounterlasthour()
    parameter['eventcountercurrenthourminus1'] = database.geteventcounter(datetime.datetime.now().hour-1) if (datetime.datetime.now().hour-1>=0) else database.geteventcounter(24-(datetime.datetime.now().hour-1))
    parameter['eventcountercurrenthourminus2'] = database.geteventcounter(datetime.datetime.now().hour-2) if (datetime.datetime.now().hour-2>=0) else database.geteventcounter(24-(datetime.datetime.now().hour-2))
    parameter['eventcountercurrenthourminus3'] = database.geteventcounter(datetime.datetime.now().hour-3) if (datetime.datetime.now().hour-3>=0) else database.geteventcounter(24-(datetime.datetime.now().hour-3))
    parameter['eventcountercurrenthourminus4'] = database.geteventcounter(datetime.datetime.now().hour-4) if (datetime.datetime.now().hour-4>=0) else database.geteventcounter(24-(datetime.datetime.now().hour-4))
    parameter['eventcountercurrenthourminus5'] = database.geteventcounter(datetime.datetime.now().hour-5) if (datetime.datetime.now().hour-5>=0) else database.geteventcounter(24-(datetime.datetime.now().hour-5))
    parameter['eventcountercurrenthourminus6'] = database.geteventcounter(datetime.datetime.now().hour-6) if (datetime.datetime.now().hour-6>=0) else database.geteventcounter(24-(datetime.datetime.now().hour-6))
    return render_template('statistics.html', parameter = parameter)


def start():
    app.run()


stop = False
def askstop():
    global stop
    if stop:
        datalogger.logData('Thread Webserver stopped')
