import serial
import threading
import datalogger
import time
import config
import eep
import math
import traceback
import status
import datetime
import database

class Enocean:
    def __init__(self):
        self.__stopreading = False
        self.__thread = threading.Thread(target=self.__readThread, args=())
        self.__cb = list()
        self.configuration = config.config.getInstance()
        self.configuration.readconfig()
        self.eep = eep.eep.getInstance()
        self.eep.readeep()
        status.status.getInstance().connectionstatus = False
        self.ser = None





    def read(self):
        self.__thread.start()

    def __readThread(self):
        try:
            self.ser = serial.Serial(self.configuration.serialPort, self.configuration.baudrate)  # open serial port
            status.status.getInstance().connectionstatus = True
        except Exception as e:
            datalogger.logData("Can't connect to serial port " + str(traceback.format_exc()))
            time.sleep(0.5)
        while (not self.__stopreading):
            try:
                if not (status.status.getInstance().connectionstatus):
                    self.ser = serial.Serial(self.configuration.serialPort, self.configuration.baudrate)
                    status.status.getInstance().connectionstatus = True

                self.ser.timeout=0
                s = self.ser.read()          # read up to 1000 bytes (timeout)
                self.ser.timeout = 0.1       #According to the ESP3 Spec a timeout is 100ms (1.5.4)
                s = s+self.ser.read(1000)
                a = bytearray(s)
                printdata = str()
                if (len(a) > 0):
                    for i in range(0, len(a)):
                        printdata = printdata + str(hex(a[i])) + " "
                    if (a[0] == 0x55) & (len(a) > 13):          #Verify if the first byte is the "sync" Byte
                        if ( a[2] + (a[1]<<8) + a[3] + 7) == len(a):      #Verify the length, must be Optional length + data length +6

                            status.status.getInstance().hourcounter = status.status.getInstance().hourcounter + 1
                            status.status.getInstance().datetimehourcounter =  datetime.datetime.now()
                            datalogger.logData('Received Enocean Package: ' + printdata)
                            #Parse data
                            returndata = dict()
                            returndata['syncbyte'] = 0x55
                            returndata['datalength'] = a[2] + (a[1]<<8)
                            returndata['optionallength'] = a[3]
                            returndata['packettype'] = a[4]
                            returndata['crc8h'] = a[5]
                            returndata['rorg'] = a[6]

                            senderifoffset = 1      #This is the offset for RPS, 1BS, 4BS Telegram
                            if returndata['rorg'] == 0xD2:
                                senderifoffset = 1  #This is the offest for VLD Telegram




                            senderid = (str(hex(a[5 + returndata['datalength'] - (senderifoffset+3)]))).replace('0x', '')
                            senderid = '0' + senderid if (len(senderid) == 1) else senderid
                            returndata['senderid'] = senderid
                            senderid = (str(hex(a[5 + returndata['datalength'] - (senderifoffset+2)]))).replace('0x', '')
                            senderid = '0' + senderid if (len(senderid) == 1) else senderid
                            returndata['senderid'] = returndata['senderid'] + senderid
                            senderid = (str(hex(a[5 + returndata['datalength'] - (senderifoffset+1)]))).replace('0x', '')
                            senderid = '0' + senderid if (len(senderid) == 1) else senderid
                            returndata['senderid'] = returndata['senderid'] + senderid
                            senderid = (str(hex(a[5 + returndata['datalength'] - senderifoffset]))).replace('0x', '')
                            senderid = '0' + senderid if (len(senderid) == 1) else senderid
                            returndata['senderid'] = returndata['senderid'] + senderid

                            returndata['status'] = (a[5 + returndata['datalength'] - senderifoffset-1])
                            if (returndata['rorg'] == 246):
                                returndata['statusT21'] = (returndata['status'] >> 5)&0x1
                                returndata['statusNU'] = (returndata['status'] >> 4) & 0x1

                            returndata['payload'] = list()
                            for j in range(7, 7+returndata['datalength']- (senderifoffset+5)):
                                returndata['payload'].append((a[j]))

                            returndata['subtelnum'] = a[6+returndata['datalength']]
                            returndata['destinationid'] = (a[7 + returndata['datalength']] << 24) + (a[8 + returndata['datalength']] << 16) + (a[9 + returndata['datalength']] << 8) + (a[10 + returndata['datalength']])
                            returndata['dbm'] = a[11 + returndata['datalength']]
                            returndata['securitylevel'] = a[12 + returndata['datalength']]
                            returndata['crc8d'] = a[13 + returndata['datalength']]
                            datalogger.logData('Parsed packet: ' + str(returndata))
                            payloadasstring = str()
                            for j in range(0, len(returndata['payload'])):
                                payloadasstring = payloadasstring + str(hex(returndata['payload'][j])) + " "
                            datalogger.logData('Payload: ' + payloadasstring)
                            #notify listeners
                            for j in range(0, len(self.__cb)):
                                self.__cb[j](printdata)

                            #Search if the Device ID is in config.json
                            for j in range(0, len(self.configuration.devices)):
                                if (self.configuration.devices[j]['id'].lower()) ==returndata['senderid']:
                                    database.writedata(datetime.datetime.now(), str(returndata['senderid']), printdata)
                                    datalogger.logData('Device ID found in config with name: '+self.configuration.devices[j]['name']+' and eep: ' + self.configuration.devices[j]['eep'])

                                    #Search eep in eep.json
                                    rorg = int(self.configuration.devices[j]['eep'].split('-')[0],16)
                                    func = int(self.configuration.devices[j]['eep'].split('-')[1],16)
                                    type = int(self.configuration.devices[j]['eep'].split('-')[2],16)
                                    for k in range(0, len(self.eep.profiles)):
                                        if (self.eep.profiles[k]['rorg']==rorg) & (self.eep.profiles[k]['func']==func) & (self.eep.profiles[k]['type']==type):
                                            #If the Messge is from type RPS we also have to consider the T21 nd NU Filed
                                            if ('statusT21' in self.eep.profiles[k]) & ('statusNU' in self.eep.profiles[k]) & ('statusT21' in returndata)  & ('statusNU' in returndata):
                                                if (self.eep.profiles[k]['statusT21'] == returndata['statusT21']) & (self.eep.profiles[k]['statusNU'] == returndata['statusNU']):
                                                    pass
                                                else:
                                                    continue
                                            for l in range(0, len(self.eep.profiles[k]['datafield'])):
                                                value = 0
                                                digitcount = 0
                                                for m in range (self.eep.profiles[k]['datafield'][l]['offset'], (self.eep.profiles[k]['datafield'][l]['offset'] + self.eep.profiles[k]['datafield'][l]['size'])):
                                                    byte = m//8
                                                    bit = m%8
                                                    numberofbite=self.eep.profiles[k]['datafield'][l]['size']
                                                    value = value + int(((returndata['payload'][byte]>>(7-bit)) & 0x1) * math.pow(2,numberofbite-digitcount-1))
                                                    digitcount = digitcount + 1

                                                if ('validRangeMax' in self.eep.profiles[k]['datafield'][l]) & ('validRangeMin' in self.eep.profiles[k]['datafield'][l]) & ('scaleMin' in self.eep.profiles[k]['datafield'][l]) & ('scaleMax' in self.eep.profiles[k]['datafield'][l]):
                                                    rawvaluespan = (self.eep.profiles[k]['datafield'][l]['validRangeMax'] -
                                                                    self.eep.profiles[k]['datafield'][l]['validRangeMin'])
                                                    scalevaluespan = (self.eep.profiles[k]['datafield'][l]['scaleMax'] -
                                                                      self.eep.profiles[k]['datafield'][l]['scaleMin'])
                                                    scale = float(scalevaluespan) / float(rawvaluespan)
                                                    scaledvalue = value * scale + self.eep.profiles[k]['datafield'][l]['scaleMin']
                                                else:
                                                    scaledvalue = value

                                                #get enumeration value
                                                if ('enum' in self.eep.profiles[k]['datafield'][l]):
                                                    scaledvalue = self.eep.profiles[k]['datafield'][l]['enum'][scaledvalue]

                                                datalogger.logData(self.configuration.devices[j]['name'] + " " + self.eep.profiles[k]['datafield'][l]['data'] + ": " + str(scaledvalue))

                                            #In case of VLP we have to search for the matching command
                                            if (rorg == 210) & ('cmd' in self.eep.profiles[k]):
                                                for l in range(0, len(self.eep.profiles[k]['cmd'])):
                                                    if returndata['payload'][0] == self.eep.profiles[k]['cmd'][l]['id']:
                                                        for m in range(0, len(self.eep.profiles[k]['cmd'][l]['datafield'])):

                                                            value = 0
                                                            digitcount = 0
                                                            for o in range(self.eep.profiles[k]['cmd'][l]['datafield'][m]['offset'], (
                                                                            self.eep.profiles[k]['cmd'][l]['datafield'][m][
                                                                                'offset'] +
                                                                            self.eep.profiles[k]['cmd'][l]['datafield'][m][
                                                                                'size'])):
                                                                byte = o // 8
                                                                bit = o % 8
                                                                numberofbite = self.eep.profiles[k]['cmd'][l]['datafield'][m][
                                                                    'size']
                                                                value = value + int(((returndata['payload'][byte] >> (
                                                                            7 - bit)) & 0x1) * math.pow(2,
                                                                                                        numberofbite - digitcount - 1))
                                                                digitcount = digitcount + 1
                                                            datalogger.logData(self.configuration.devices[j]['name'] + " " +
                                                                               self.eep.profiles[k]['cmd'][l]['datafield'][m]['data'] + ": " + str(value))
                time.sleep(0.001)
            except Exception as e:
                status.status.getInstance().connectionstatus = False
                if isinstance(self.ser, serial.Serial):
                    self.ser.close()
                datalogger.logData("Exception Reading Enocean Messages " + str(traceback.format_exc()))
                time.sleep(0.001)

    def addMessageReceivedListener(self, cb):
        self.__cb.append(cb)



if __name__ == "__main__":
    def listener(received):
        print ('listener called ' + received)

    enocean = Enocean()
    enocean.read()
    enocean.addMessageReceivedListener(listener)





