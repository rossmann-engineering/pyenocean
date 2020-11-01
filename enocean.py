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



    def connect(self):
        try:
            if (self.ser == None):
                self.ser = serial.Serial(self.configuration.serialPort, self.configuration.baudrate)  # open serial port
            status.status.getInstance().connectionstatus = True
        except Exception as e:
            datalogger.logData("Can't connect to serial port " + str(traceback.format_exc()))
            time.sleep(0.5)

    def read(self):
        self.__thread.start()

    def __readThread(self):

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
                time.sleep(1)

    def addMessageReceivedListener(self, cb):
        self.__cb.append(cb)


    def sendMessage(self, name, data, commandId = 0):
        if (self.ser == None):
            self.ser = serial.Serial(self.configuration.serialPort, self.configuration.baudrate)  # open serial port

        configuration = config.config.getInstance()
        eep = ""
        if (not isinstance(data, dict)):
            raise TypeError('Parameter "data" should be dict')
        if (not isinstance(name, str)):
            raise TypeError('Parameter "name" should be string')
        if (not isinstance(commandId, int)):
            raise TypeError('Parameter "commandId" should be int')

        #Search for the eep profile in the config.json
        for i in range(0, len(configuration.devices)):
            if (name == configuration.devices[i]['name']):
                eep = configuration.devices[i]['eep']
                datalengthMSB = 0
                datalengthLSB = 0x7
                optionallength = 0x07
                packettype = 0x01
                data = bytearray(
                    [datalengthMSB, datalengthLSB, optionallength, packettype])
                crc8h = calculatecrc(self, data)
                rorg = 0xF6
                dataelement = 0x00


                senderid1 = 0x00
                senderid2 = 0x30
                senderid3 = 0xE4
                senderid4 = 0xA3

                status = 0x20

                subtelegram = 0x01


                destinationid1 = 0xff
                destinationid2 = 0xff
                destinationid3 = 0xff
                destinationid4 = 0xff

                dbm = 0x2d

                securitylevel = 0x00

                data = bytearray(
                    [rorg,dataelement,senderid1,senderid2,senderid3,senderid4,status,subtelegram, destinationid1, destinationid2, destinationid3, destinationid4, dbm, securitylevel])

                crc8d = calculatecrc(self,data)

                data = bytearray(
                    [0x55, datalengthMSB, datalengthLSB, optionallength, packettype, crc8h, rorg, dataelement, senderid1, senderid2, senderid3, senderid4, status, subtelegram, destinationid1, destinationid2, destinationid3, destinationid4, dbm, securitylevel, crc8d])

                printdata = ""
                for i in range(0, len(data)):
                    printdata = printdata + str(hex(data[i])) + " "
                datalogger.logData('Send Data: ' + printdata)
                while (1):
                    self.ser.write(data)







if __name__ == "__main__":
    def listener(received):
        print ('listener called ' + received)

    enocean = Enocean()
    enocean.read()
    enocean.addMessageReceivedListener(listener)


def proccrc8(self, u8CRC, u8Data):
    U8CRCTABLE = bytearray([
        0x00, 0x07, 0x0e, 0x09, 0x1c, 0x1b, 0x12, 0x15, 0x38, 0x3f, 0x36, 0x31, 0x24, 0x23, 0x2a, 0x2d, 0x70, 0x77,
        0x7e, 0x79, 0x6c, 0x6b, 0x62, 0x65, 0x48, 0x4f, 0x46, 0x41, 0x54, 0x53, 0x5a, 0x5d, 0xe0, 0xe7, 0xee, 0xe9,
        0xfc, 0xfb, 0xf2, 0xf5, 0xd8, 0xdf, 0xd6, 0xd1, 0xc4, 0xc3, 0xca, 0xcd, 0x90, 0x97, 0x9e, 0x99, 0x8c, 0x8b,
        0x82, 0x85, 0xa8, 0xaf, 0xa6, 0xa1, 0xb4, 0xb3, 0xba, 0xbd, 0xc7, 0xc0, 0xc9, 0xce, 0xdb, 0xdc, 0xd5, 0xd2,
        0xff, 0xf8, 0xf1, 0xf6, 0xe3, 0xe4, 0xed, 0xea, 0xb7, 0xb0, 0xb9, 0xbe, 0xab, 0xac, 0xa5, 0xa2, 0x8f, 0x88,
        0x81, 0x86, 0x93, 0x94, 0x9d, 0x9a, 0x27, 0x20, 0x29, 0x2e, 0x3b, 0x3c, 0x35, 0x32, 0x1f, 0x18, 0x11, 0x16,
        0x03, 0x04, 0x0d, 0x0a, 0x57, 0x50, 0x59, 0x5e, 0x4b, 0x4c, 0x45, 0x42, 0x6f, 0x68, 0x61, 0x66, 0x73, 0x74,
        0x7d, 0x7a, 0x89, 0x8e, 0x87, 0x80, 0x95, 0x92, 0x9b, 0x9c, 0xb1, 0xb6, 0xbf, 0xb8, 0xad, 0xaa, 0xa3, 0xa4,
        0xf9, 0xfe, 0xf7, 0xf0, 0xe5, 0xe2, 0xeb, 0xec, 0xc1, 0xc6, 0xcf, 0xc8, 0xdd, 0xda, 0xd3, 0xd4, 0x69, 0x6e,
        0x67, 0x60, 0x75, 0x72, 0x7b, 0x7c, 0x51, 0x56, 0x5f, 0x58, 0x4d, 0x4a, 0x43, 0x44, 0x19, 0x1e, 0x17, 0x10,
        0x05, 0x02, 0x0b, 0x0c, 0x21, 0x26, 0x2f, 0x28, 0x3d, 0x3a, 0x33, 0x34, 0x4e, 0x49, 0x40, 0x47, 0x52, 0x55,
        0x5c, 0x5b, 0x76, 0x71, 0x78, 0x7f, 0x6A, 0x6d, 0x64, 0x63, 0x3e, 0x39, 0x30, 0x37, 0x22, 0x25, 0x2c, 0x2b,
        0x06, 0x01, 0x08, 0x0f, 0x1a, 0x1d, 0x14, 0x13, 0xae, 0xa9, 0xa0, 0xa7, 0xb2, 0xb5, 0xbc, 0xbb, 0x96, 0x91,
        0x98, 0x9f, 0x8a, 0x8D, 0x84, 0x83, 0xde, 0xd9, 0xd0, 0xd7, 0xc2, 0xc5, 0xcc, 0xcb, 0xe6, 0xe1, 0xe8, 0xef,
        0xfa, 0xfd, 0xf4, 0xf3]);
    return U8CRCTABLE[(u8CRC ^ u8Data)]

def calculatecrc(self, data):
    u8crc = 0
    for i in range(0, len(data)):
        u8crc = proccrc8(self,u8crc, data[i])
    return u8crc


