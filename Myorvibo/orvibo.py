#!/usr/bin/python3

# @file orvibo.py
# @author cherezov.pavel@gmail.com

# Change log:
#   1.0 Initial stable version
#   1.1 Mac and type arguments introduced for fast control known devices
#   1.2 Python3 discover bug fixed
#   1.3 ip argument is now optional in case of mac and type are passed
#   1.4 keep connection functionality implemented
#   1.4.1 Learn/Emit logging improved
#   1.5 Learn/Emit Orvibo SmartSwitch RF433 MHz signal support added
__version__ = "1.5"

from contextlib import contextmanager
import logging
import struct
import select
import random
import socket
import binascii
import time
import sys
import os

py3 = sys.version_info[0] == 3

BROADCAST = '255.255.255.255'
PORT = 10000

MAGIC = b'\x68\x64'
SPACES_6 = b'\x20\x20\x20\x20\x20\x20'
ZEROS_4 = b'\x00\x00\x00\x00'

ON = b'\x01'
OFF = b'\x00'

# CMD CODES
DISCOVER = b'\x71\x61'
DISCOVER_RESP = DISCOVER

SUBSCRIBE = b'\x63\x6c'
SUBSCRIBE_RESP = SUBSCRIBE

CONTROL = b'\x64\x63'
CONTROL_RESP = CONTROL

SOCKET_EVENT = b'\x73\x66' # something happend with socket

LEARN_IR = b'\x6c\x73'
LEARN_IR_RESP = LEARN_IR

BLAST_IR = b'\x69\x63'

BLAST_RF433 = CONTROL
LEARN_RF433 = CONTROL

class OrviboException(Exception):
    """ Module level exception class.
    """
    def __init__(self, msg):
        super(OrviboException, self).__init__(msg)

def _reverse_bytes(mac):
    """ Helper method to reverse bytes order.

    mac -- bytes to reverse
    """
    ba = bytearray(mac)
    ba.reverse()
    return bytes(ba)

def _random_byte():
    """ Generates random single byte.
    """
    return bytes([int(256 * random.random())])

def _random_n_bytes(n):
    res = b''
    for n in range(n):
        res += _random_byte()
    return res

def _packet_id():
    return _random_n_bytes(2)

_placeholders = ['MAGIC', 'SPACES_6', 'ZEROS_4', 'CONTROL', 'CONTROL_RESP', 'SUBSCRIBE', 'LEARN_IR', 'BLAST_RF433', 'BLAST_IR', 'DISCOVER', 'DISCOVER_RESP' ]
def _debug_data(data):
    data = binascii.hexlify(bytearray(data))
    for s in _placeholders:
        p = binascii.hexlify(bytearray( globals()[s]))
        data = data.replace(p, b" + " + s.encode() + b" + ")
    return data[3:]

def _parse_discover_response(response):
    """ Extracts MAC address and Type of the device from response.

    response -- dicover response, format:
                MAGIC + LENGTH + DISCOVER_RESP + b'\x00' + MAC + SPACES_6 + REV_MAC + ... TYPE
    """
    header_len = len(MAGIC + DISCOVER_RESP) + 2 + 1  # 2 length bytes, and 0x00
    mac_len = 6
    spaces_len = len(SPACES_6)

    mac_start = header_len
    mac_end = mac_start + mac_len
    mac = response[mac_start:mac_end]

    type = None
    if b'SOC' in response:
        type = Orvibo.TYPE_SOCKET

    elif b'IRD' in response:
        type = Orvibo.TYPE_IRDA

    return (type, mac)

def _create_orvibo_socket(ip=''):
    """ Creates socket to talk with Orvibo devices.

    Arguments:
    ip - ip address of the Orvibo device or empty string in case of broadcasting discover packet.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for opt in [socket.SO_BROADCAST, socket.SO_REUSEADDR, socket.SO_BROADCAST]:
        sock.setsockopt(socket.SOL_SOCKET, opt, 1)
    if ip:
        sock.connect((ip, PORT))
    else:
        sock.bind((ip, PORT))
    return sock

@contextmanager
def _orvibo_socket(external_socket = None):
    sock = _create_orvibo_socket() if external_socket is None else external_socket

    yield sock

    if external_socket is None:
        sock.close()
    else:
        pass

class Packet:
    """ Represents response sender/recepient address and binary data.
    """

    Request = 'request'
    Response = 'response'

    def __init__(self, ip = BROADCAST, data = None, type = Request):
        self.ip = ip
        self.data = data
        self.type = type

    def __repr__(self):
        return 'Packet {} {}: {}'.format('to' if self.type == self.Request else 'from', self.ip, _debug_data(self.data))

    @property
    def cmd(self):
        """ 2 bytes command of the orvibo packet
        """
        if self.data is None:
            return b''
        return self.data[4:6]

    @property
    def length(self):
        """ 2 bytes command of the orvibo packet
        """
        if self.data is None:
            return b''
        return self.data[2:4]


    def send(self, sock, timeout = 10):
        """ Sends binary packet via socket.

        Arguments:
        sock -- socket to send through
        packet -- byte string to send
        timeout -- number of seconds to wait for sending operation
        """
        if self.data is None:
            # Nothing to send
            return

        for i in range(timeout):
            r, w, x = select.select([], [sock], [sock], 1)
            if sock in w:
                sock.sendto(bytearray(self.data), (self.ip, PORT))
            elif sock in x:
                raise OrviboException("Failed while sending packet.")
            else:
                # nothing to send
                break

    @staticmethod
    def recv(sock, expectResponseType = None, timeout = 10):
        """ Receive first packet from socket of given type

        Arguments:
        sock -- socket to listen to
        expectResponseType -- 2 bytes packet command type to filter result data
        timeout -- number of seconds to wait for response
        """
        response = None
        for i in range(10):
            r, w, x = select.select([sock], [], [sock], 1)
            if sock in r:
                data, addr = sock.recvfrom(1024)

                if expectResponseType is not None and data[4:6] != expectResponseType:
                    continue

                response = Packet(addr[0], data, Packet.Response)
                break
            elif sock in x:
                raise OrviboException('Getting response failed')
            else:
                # Nothing to read
                break

        return response

    @staticmethod
    def recv_all(sock, expectResponseType = None, timeout = 10):
       res = None
       while True:
           resp = Packet.recv(sock, expectResponseType, timeout)
           if resp is None:
                break
           res = resp
       return res

    def compile(self, *args):
        """ Assemblies packet to send to orvibo device.

        *args -- number of bytes strings that will be concatenated, and prefixed with MAGIC heaer and packet length.
        """

        length = len(MAGIC) + 2 # len itself
        packet = b''
        for a in args:
            length += len(a)
            packet += a

        msg_len_2 = struct.pack('>h', length)
        self.data = MAGIC + msg_len_2 + packet
        return self

class Orvibo(object):
    """ Represents Orvibo device, such as wifi socket (TYPE_SOCKET) or AllOne IR blaster (TYPE_IRDA)
    """

    TYPE_SOCKET = 'socket'
    TYPE_IRDA = 'irda'

    def __init__(self, ip, mac = None, type = 'Unknown'):
        self.ip = ip
        self.type = type
        self.__last_subscr_time = time.time() - 1 # Orvibo doesn't like subscriptions frequently that 1 in 0.1sec
        self.__logger = logging.getLogger('{}@{}'.format(self.__class__.__name__, ip))
        self.__socket = None
        self.mac = mac

        # TODO: make this tricky code clear
        if py3 and isinstance(mac, str):
            self.mac = binascii.unhexlify(mac)
        else:
            try:
                self.mac = binascii.unhexlify(mac)
            except:
                pass

        if mac is None:
            self.__logger.debug('MAC address is not provided. Discovering..')
            d = Orvibo.discover(self.ip)
            self.mac = d.mac
            self.type = d.type

    def __del__(self):
        self.close()

    def close(self):
        if self.__socket is not None:
            try:
                self.__socket.close()
            except socket.error:
                # socket seems not alive
                pass
            self.__socket = None

    @property
    def keep_connection(self):
        """ Keeps connection to the Orvibo device.
        """
        return self.__socket is not None

    @keep_connection.setter
    def keep_connection(self, value):
        """ Keeps connection to the Orvibo device.
        """
        # Close connection if alive
        self.close()

        if value:
            self.__socket = _create_orvibo_socket(self.ip)
            if self.__subscribe(self.__socket) is None:
                raise OrviboException('Connection subscription error.')
        else:
            self.close()

    def __repr__(self):
        mac = binascii.hexlify(bytearray(self.mac))
        return "Orvibo[type={}, ip={}, mac={}]".format(self.type, 'Unknown' if self.ip == BROADCAST else self.ip, mac.decode('utf-8') if py3 else mac)

    @staticmethod
    def discover(ip = None):
        """ Discover all/exact devices in the local network

        Arguments:
        ip -- ip address of the discovered device

        returns -- map {ip : (ip, mac, type)} of all discovered devices if ip argument is None
                   Orvibo object that represents device at address ip.
        raises -- OrviboException if requested ip not found
        """
        devices = {}
        with _orvibo_socket() as s:
            logger = logging.getLogger(Orvibo.__class__.__name__)
            logger.debug('Discovering Orvibo devices')
            discover_packet = Packet(BROADCAST)
            discover_packet.compile(DISCOVER)
            discover_packet.send(s)

            for indx in range(512): # supposer there are less then 512 devices in the network
                p = discover_packet.recv(s)
                if p is None:
                    # No more packets in the socket
                    break

                orvibo_type, orvibo_mac = _parse_discover_response(p.data)
                logger.debug('Discovered values: type={}, mac={}'.format(orvibo_type, orvibo_mac));

                if not orvibo_mac:
                    # Filter ghosts devices
                    continue

                devices[p.ip] = (p.ip, orvibo_mac, orvibo_type)

        if ip is None:
            return devices

        if ip not in devices.keys():
            raise OrviboException('Device ip={} not found in {}.'.format(ip, devices.keys()))

        return Orvibo(*devices[ip])

    def subscribe(self):
        """ Subscribe to device.

        returns -- last response byte, which represents device state
        """
        with _orvibo_socket(self.__socket) as s:
            return self.__subscribe(s)

    def __subscribe(self, s):
        """ Required action after connection to device before sending any requests

        Arguments:
        s -- socket to use for subscribing

        returns -- last response byte, which represents device state
        """

        if time.time() - self.__last_subscr_time < 0.1:
            time.sleep(0.1)

        subscr_packet = Packet(self.ip)
        subscr_packet.compile(SUBSCRIBE, self.mac, SPACES_6, _reverse_bytes(self.mac), SPACES_6)
        subscr_packet.send(s)
        response = subscr_packet.recv_all(s, SUBSCRIBE_RESP)

        self.__last_subscr_time = time.time()
        return response.data[-1] if response is not None else None

    def learn(self,touch=None ,timeout = 15):

        """ Read signal using your remote for future emit
            Supports IR and RF 433MHz remotes

        Arguments:
        fname -- [optional] file name to store IR/RF433 signal to
        timeout -- number of seconds to wait for IR/RF433 signal from remote

        returns -- byte string with IR/RD433 signal
        """

        with _orvibo_socket(self.__socket) as s:
            if self.__subscribe(s) is None:
                self.__logger.warn('Subscription failed while entering to Learning IR/RF433 mode')
                return

            if self.type != Orvibo.TYPE_IRDA:
                self.__logger.warn('Attempt to enter to Learning IR/RF433 mode for device with type {}'.format(self.type))
                return

            self.__logger.debug('Entering to Learning IR/RF433 mode')

            learn_packet = Packet(self.ip).compile(LEARN_IR, self.mac, SPACES_6, b'\x01\x00', ZEROS_4)
            learn_packet.send(s)
            if learn_packet.recv(s, LEARN_IR_RESP) is None:
                self.__logger.warn('Failed to enter to Learning IR/RF433 mode')
                return

            self.__logger.info('Waiting {} sec for IR/RF433 signal...'.format(timeout))


            # LEARN_IR responses with such length will be skipped
            EMPTY_LEARN_IR = b'\x00\x18'

            start_time = time.time()
            while True:
                elapsed_time = time.time() - start_time
                if elapsed_time > timeout:
                    self.__logger.warn('Nothing happend during {} sec'.format(timeout))
                    return

                packet_with_signal = learn_packet.recv(s, timeout=1)
                if packet_with_signal is None:
                    self.__logger.info('The rest time: {} sec'.format(int(timeout - elapsed_time)))
                    continue

                if packet_with_signal.length == EMPTY_LEARN_IR:
                    self.__logger.debug('Skipped:\nEmpty packet = {}'.format(_debug_data(packet_with_signal.data)))
                    continue

                if packet_with_signal.cmd == LEARN_IR:
                    self.__logger.debug('SUCCESS:\n{}'.format(_debug_data(packet_with_signal.data)))
                    break

                self.__logger.debug('Skipped:\nUnexpected packet = {}'.format(_debug_data(packet_with_signal.data)))

            signal_split = packet_with_signal.data.split(self.mac + SPACES_6, 1)
            signal = signal_split[1][6:]

            if touch is not None:
                APP_ROOT = os.path.dirname(os.path.realpath(__file__))
                IR=APP_ROOT+'/ir'
                action = os.path.join(IR, touch)
                with open(action, 'wb') as f:
                    f.write(signal)
                self.__logger.info('IR/RF433 signal got successfuly and saved to "{}" file'.format(touch+'.ir'))
            else:
                self.__logger.info('IR/RF433 signal got successfuly')
            print(signal)
            return signal



    def emit(self, touch):
        """ Emit IR signal

        Arguments:
        signal -- raw signal got with learn method or file name with ir signal to emit

        returns -- True if emit successs, otherwise False
        """
        signal=''
        with _orvibo_socket(self.__socket) as s:
            if self.__subscribe(s) is None:
                self.__logger.warn('Subscription failed while emiting IR signal')
                return False

            if self.type != Orvibo.TYPE_IRDA:
                self.__logger.warn('Attempt to emit IR signal for device with type {}'.format(self.type))
                return False

            if isinstance(touch, str):
                # Read IR code from file
                self.__logger.debug('Reading IR signal from file "{}"'.format(signal))
                APP_ROOT = os.path.dirname(os.path.realpath(__file__))
                IR=APP_ROOT+'/ir'
                action = os.path.join(IR, touch)
                with open(action, 'rb') as f:
                    signal = f.read()
                signal_packet = Packet(self.ip).compile(BLAST_IR, self.mac, SPACES_6, b'\x65\x00\x00\x00', _packet_id(), signal)
                signal_packet.send(s)
                signal_packet.recv_all(s)
            else:
                for i in touch:
                    # Read IR code from file
                    self.__logger.debug('Reading IR signal from file "{}"'.format(signal))
                    APP_ROOT = os.path.dirname(os.path.realpath(__file__))
                    IR=APP_ROOT+'/ir'
                    action = os.path.join(IR, i)
                    with open(action, 'rb') as f:
                        signal = f.read()
                    signal_packet = Packet(self.ip).compile(BLAST_IR, self.mac, SPACES_6, b'\x65\x00\x00\x00', _packet_id(), signal)
                    signal_packet.send(s)
                    signal_packet.recv_all(s)

            self.__logger.info('IR signal emit successfuly')
            return True


def discover():
    for d in Orvibo.discover().values():
        ip=d[0]
        mac=d[1]
        name=ip
        if (ip!=''):
            return ip
            break
        else:
            return None
            break


def search (ip=None):
    otype='irda'
    if (ip==None ) :
        try:
            d=Orvibo.discover(discover())
        except OrviboException as e:
            print (e)
    elif (ip!=None) :
        try:
            d = Orvibo.discover(ip)
        except OrviboException as e:
            print(e)
    try:
        print(d)
        name=ip
    except ValueError as t:
        print(t)
        return False
    else:
        return ip

def send(ip=None,touch=''):
    otype='irda'
    if (ip!=None and touch!=None ):
        try:
            d = Orvibo.discover(ip)
            print(d)
        except OrviboExeption as e:
            print(e)

    if (ip==None and touch!=None ):
        try:
            d = Orvibo.discover(discover())
            print(d)
        except OrviboExeption as e:
            print(e)

        # It is required to wake up AllOne
    try:
        d.emit(touch)
        print('Emit IR done.')
    except OrviboException as msg:
        print (msg)
        return False
    else:
        return True

def learn(ip=None,touch='unknow'):
    otype='irda'
    if (ip!=None and touch!=None ):
        try:
            d = Orvibo.discover(ip)
            print(d)
        except OrviboExeption as e:
            print(e)

    elif (ip==None and touch!=None ):

        try:
            d = Orvibo.discover(discover())
            print(d)
        except OrviboExeption as e:
            print(e)
    try:
        signal = d.learn(touch)
        if(signal==None):
            return False
        else:
            return True
        #print('Teach IR done')
    except ValueError as t:
        print(t)
        return False

if __name__ == '__main__':
    #send(ip="192.168.0.16",touch='tv_v-')
    learn(touch='tv_p-.ir')

