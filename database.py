import os,sys, sqlite3
import datetime

def writedata(datetime,deviceid, packet):
        if not (os.path.exists("receive.db")):
            connection = sqlite3.connect("receive.db")
            cursor = connection.cursor()
            sql = 'CREATE TABLE receive(datetime STRING, deviceid STRING, packet STRING)'
            cursor.execute(sql)
        else:
            connection = sqlite3.connect("receive.db")
            cursor = connection.cursor()
        sql = 'INSERT INTO receive VALUES("' + str(datetime) + '", "' +str(deviceid)+ '", "' + str(packet) + '");'
        cursor.execute(sql)
        connection.commit()
        connection.close()

def readdata():
    if (os.path.exists("receive.db")):
        connection = sqlite3.connect("receive.db")
        cursor = connection.cursor()
        sql = 'SELECT * FROM receive'
        cursor.execute(sql)
        connection.close()

def geteventcountertotal():
    if (os.path.exists("receive.db")):
        connection = sqlite3.connect("receive.db")
        cursor = connection.cursor()
        sql = 'SELECT * FROM receive'
        cursor.execute(sql)
        returnvalue = (len(cursor.fetchall()))
        connection.close()
        return returnvalue

def geteventcounterlasthour():
    returnvalue = 0
    if (os.path.exists("receive.db")):
        connection = sqlite3.connect("receive.db")
        cursor = connection.cursor()
        sql = 'SELECT * FROM receive ORDER BY datetime DESC'
        cursor.execute(sql)
        for entry in cursor:
            dt = datetime.datetime.strptime(entry[0], "%Y-%m-%d %H:%M:%S.%f")
            if (dt.hour == datetime.datetime.now().hour):
                returnvalue = returnvalue + 1
            else:
                break
    return returnvalue

def geteventcounter(hour):
    returnvalue = 0
    if (os.path.exists("receive.db")):
        connection = sqlite3.connect("receive.db")
        cursor = connection.cursor()
        sql = 'SELECT * FROM receive ORDER BY datetime DESC'
        cursor.execute(sql)
        for entry in cursor:
            dt = datetime.datetime.strptime(entry[0], "%Y-%m-%d %H:%M:%S.%f")
            if (dt.hour == hour):
                returnvalue = returnvalue + 1
            if (dt.hour < hour):
                break
    return returnvalue

def geteventcounterdeviceid():
    eventcounters = dict()
    if (os.path.exists("receive.db")):
        connection = sqlite3.connect("receive.db")
        cursor = connection.cursor()
        sql = 'SELECT * FROM receive ORDER BY deviceid DESC'
        cursor.execute(sql)
        for entry in cursor:
            if not ('deviceid'+str(entry[1]) in eventcounters):
                eventcounters['deviceid'+entry[1]] = int()
            eventcounters['deviceid'+entry[1]] = eventcounters['deviceid'+entry[1]]+1
    return eventcounters
