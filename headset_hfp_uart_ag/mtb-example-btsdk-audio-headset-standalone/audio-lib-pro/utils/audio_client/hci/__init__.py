#
# Copyright 2016-2024, Cypress Semiconductor Corporation (an Infineon company) or
# an affiliate of Cypress Semiconductor Corporation.  All rights reserved.
#
# This software, including source code, documentation and related
# materials ("Software") is owned by Cypress Semiconductor Corporation
# or one of its affiliates ("Cypress") and is protected by and subject to
# worldwide patent protection (United States and foreign),
# United States copyright laws and international treaty provisions.
# Therefore, you may use this Software only as provided in the license
# agreement accompanying the software package from which you
# obtained this Software ("EULA").
# If no EULA applies, Cypress hereby grants you a personal, non-exclusive,
# non-transferable license to copy, modify, and compile the Software
# source code solely for use in connection with Cypress's
# integrated circuit products.  Any reproduction, modification, translation,
# compilation, or representation of this Software except as specified
# above is prohibited without the express written permission of Cypress.
#
# Disclaimer: THIS SOFTWARE IS PROVIDED AS-IS, WITH NO WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, NONINFRINGEMENT, IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. Cypress
# reserves the right to make changes to the Software without notice. Cypress
# does not assume any liability arising out of the application or use of the
# Software or any product or circuit described in the Software. Cypress does
# not authorize its products for use in any products where a malfunction or
# failure of the Cypress product may reasonably be expected to result in
# significant property damage, injury or death ("High Risk Product"). By
# including Cypress's product in a High Risk Product, the manufacturer
# of such system or application assumes all risk of such use and in doing
# so agrees to indemnify Cypress against all liability.
#

import logging
import traceback

import re
import sys
import time
from enum import Enum, IntEnum
from struct import pack, unpack

import serial
import serial.threaded
from threading import Thread

import queue
from _struct import Struct

#logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add log level VERBOSE
logging.VERBOSE = 5
logging.addLevelName(logging.VERBOSE, "VERBOSE")
def verbose(self, message, *args, **kws):
    if self.isEnabledFor(logging.VERBOSE):
        self._log(logging.VERBOSE, message, args, **kws)
logging.Logger.verbose = verbose


# HCI header
HCI_PACKET_INDICATOR_BTHCI = 0x01
HCI_PACKET_INDICATOR_EVENT = 0x04
HCI_PACKET_INDICATOR_WICED = 0x19

HCI_EVENT_VENDOR_SPECIFIC_CODE = 0xFF
HCI_EVENT_COMMAND_COMPLETED = 0x0E

HCI_EVENT_VS_DBFW_DUMP = 0x1B


class WicedResult(IntEnum):
    SUCCESS = 0
    PARTIAL_RESULTS = 3
    BADARG = 5
    BADOPTION = 6
    OUT_OF_HEAP_SPACE = 8
    UNKNOWN_EVENT = 8029
    LIST_EMPTY = 8010
    ITEM_NOT_IN_LIST = 8011
    PACKET_DATA_OVERFLOW = 8012
    PACKET_POOL_EXHAUSTED = 8013
    PACKET_POOL_FATAL_ERROR = 8014
    UNKNOWN_PACKET = 8015
    PACKET_WRONG_OWNER = 8016
    BUS_UNINITIALISED = 8017
    MPAF_UNINITIALISED = 8018
    RFCOMM_UNINITIALISED = 8019
    STACK_UNINITIALISED = 8020
    SMARTBRIDGE_UNINITIALISED = 8021
    ATT_CACHE_UNINITIALISED = 8022
    MAX_CONNECTIONS_REACHED = 8023
    SOCKET_IN_USE = 8024
    SOCKET_NOT_CONNECTED = 8025
    ENCRYPTION_FAILED = 8026
    SCAN_IN_PROGRESS = 8027
    CONNECT_IN_PROGRESS = 8028
    DISCONNECT_IN_PROGRESS = 8029
    DISCOVER_IN_PROGRESS = 8030
    GATT_TIMEOUT = 8031
    ATTRIBUTE_VALUE_TOO_LONG = 8032
    PENDING = 8100
    BUSY = 8101
    NO_RESOURCES = 8102
    UNSUPPORTED = 8103
    ILLEGAL_VALUE = 8104
    WRONG_MODE = 8105
    UNKNOWN_ADDR = 8106
    TIMEOUT = 8107
    BAD_VALUE_RET = 8108
    ERROR = 8109
    NOT_AUTHORIZED = 8110
    DEV_RESET = 8111
    CMD_STORED = 8112
    ILLEGAL_ACTION = 8113
    DELAY_CHECK = 8114
    SCO_BAD_LENGTH = 8115
    SUCCESS_NO_SECURITY = 8116
    FAILED_ON_SECURITY = 8117
    REPEATED_ATTEMPTS = 8118
    MODE4_LEVEL4_NOT_SUPPORTED = 8119
    USE_DEFAULT_SECURITY = 8120
    KEY_MISSING = 8121
    ENCRYPT_DISABLED = 8122


GROUP_DEVICE = 0x00
GROUP_SCRIPT = 0x25
GROUP_HCI_AUDIO = 0x29
GROUP_AUDIO_SINK = 0x14

BTHCI_CMD_OGF_LINK_CONTROL = 0x01
BTHCI_CMD_OGF_LINK_POLICY = 0x02
BTHCI_CMD_OGF_CONTROLLER_AND_BASEBAND = 0x03
BTHCI_CMD_OGF_INFO_PARAMS = 0x04
BTHCI_CMD_OGF_STATUS_PARAMS = 0x06
BTHCI_CMD_OGF_LE_CONTROL = 0x08
BTHCI_CMD_OGF_VENDOR_SPECIFIC = 0x3F

class CommandID(IntEnum):
    SCRIPT_EXECUTE = (GROUP_SCRIPT << 8) | 0x01
    RECORD_DATA = (GROUP_HCI_AUDIO << 8) | 0x02
    PUSH_NVRAM = (GROUP_HCI_AUDIO << 8) | 0x03
    BT_START = (GROUP_HCI_AUDIO << 8) | 0x04
    BUTTON = (GROUP_HCI_AUDIO << 8) | 0x30

class EventID(Enum):
    DEVICE_STARTED = (GROUP_DEVICE << 8) | 0x05
    SCRIPT_RET_CODE = (GROUP_SCRIPT << 8) | 0x01
    SCRIPT_UNKNOWN_CMD = (GROUP_SCRIPT << 8) | 0x02
    SCRIPT_CALLBACK = (GROUP_SCRIPT << 8) | 0x03
    AUDIO_DATA = (GROUP_AUDIO_SINK << 8) | 0x0a
    SCO_DATA = (GROUP_HCI_AUDIO << 8) | 0x02
    STREAM_START = (GROUP_HCI_AUDIO << 8) | 0x03
    STREAM_STOP = (GROUP_HCI_AUDIO << 8) | 0x04
    STREAM_CONFIG = (GROUP_HCI_AUDIO << 8 ) | 0x05
    STREAM_VOLUME = (GROUP_HCI_AUDIO << 8 ) | 0x06
    STREAM_MIC_GAIN = (GROUP_HCI_AUDIO << 8 ) | 0x07
    WRITE_NVRAM_DATA = (GROUP_HCI_AUDIO << 8 ) | 0x08
    DELETE_NVRAM_DATA = (GROUP_HCI_AUDIO << 8 ) | 0x09
    COMMAND_COMPLETED = 0x0E

class BthciCmdCBB(IntEnum):
    RESET = BTHCI_CMD_OGF_CONTROLLER_AND_BASEBAND << 10 | 0x003
    UPDATE_BAUD_RATE = BTHCI_CMD_OGF_VENDOR_SPECIFIC << 10 | 0x018
    DOWNLOAD_MINIDRIVER = BTHCI_CMD_OGF_VENDOR_SPECIFIC << 10 | 0x02E
    WRITE_RAM = BTHCI_CMD_OGF_VENDOR_SPECIFIC << 10 | 0x04C
    LAUNCH_RAM = BTHCI_CMD_OGF_VENDOR_SPECIFIC << 10 | 0x04E


def version_check(module, min_version):
    def normalize(v):
        return [int(x) for x in re.sub(r"(\.0+)*$", "", v).split(".")]

    if normalize(module.__version__) < normalize(min_version):
        logger.critical(
            "Require minimum version of module `"
            + module.__name__
            + "' is: "
            + min_version
            + ", but the installed version is "
            + module.__version__
        )
        sys.exit(1)


version_check(serial, "2.5")


class Error(Exception):
    result = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args)

        if "result" in kwargs:
            self.result = kwargs["result"]

    def __str__(self):
        return super().__str__() + " Result: {0!s})".format(self.result)


class Controller:
    def __init__(self, port, baudrate):
        self.event_queue = queue.Queue()
        self.command_result_event_queue = queue.Queue()
        self.audio_queue = queue.Queue()

        logger.info("Opening {0} at {1:,} bps ...".format(port, baudrate))
        try:
            self.serial_instance = serial.Serial(
                port=port,
                baudrate=baudrate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                rtscts=True,
            )
            # Wait the device initialized
            time.sleep(0.1)
            self.read_thread = serial.threaded.ReaderThread(
                self.serial_instance, WicedHciProtocol
            )
            self.read_thread.start()
            protocol = self.read_thread.connect()[1]
            protocol.event_received = self.event_received
        except (ValueError, serial.SerialException) as exc:
            self.read_thread = None
            logger.error("Failed to open HCI: %s", exc)
            raise Error("Failed to open {0} at {1:,} bps".format(port, baudrate))

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        self.close()

    def close(self):
        if self.read_thread:
            logger.info("Closing %s ...", self.read_thread.serial.port)
            self.read_thread.close()
            self.read_thread = None
    def flush(self):
        self.serial_instance.flush()

    def event_received(self, indicator, event_id, payload):
        if indicator == HCI_PACKET_INDICATOR_EVENT:
            self.event_queue.put((event_id, payload))
        elif (event_id == EventID.AUDIO_DATA or \
              event_id == EventID.SCO_DATA or \
              event_id == EventID.STREAM_START or \
              event_id == EventID.STREAM_STOP or \
              event_id == EventID.STREAM_CONFIG or \
              event_id == EventID.STREAM_VOLUME or \
              event_id == EventID.STREAM_MIC_GAIN or \
              event_id == EventID.WRITE_NVRAM_DATA or \
              event_id == EventID.DELETE_NVRAM_DATA):
            self.audio_queue.put((event_id.value, payload))
        elif (event_id == EventID.SCRIPT_RET_CODE or event_id == EventID.SCRIPT_UNKNOWN_CMD):
            logger.debug("Received %s, length: %s, %s", event_id, len(payload), payload)
            self.command_result_event_queue.put((event_id, payload))
        elif event_id == EventID.SCRIPT_CALLBACK:
            self.callback_event_received(event_id, payload)
        elif event_id == EventID.DEVICE_STARTED:
            logger.debug("Received %s", event_id)
            self.event_queue.put((event_id, payload))
        else:
            logger.warning(
                "Skip event: 0x{0:04x}, length: {1}, {2}".format(
                    event_id, len(payload), payload
                )
            )

    def callback_event_received(self, event_id, payload):
        logger.warning("Unhandled event: %s, %s", event_id, payload)

    def write(self, command, payload):
        data = pack("<BHH", HCI_PACKET_INDICATOR_WICED, command, len(payload)) + payload
        logger.verbose("UART TX[%s]:" + " %02x" * len(data), len(data), *data)
        self.read_thread.write(data)

    def read_event(self, t):
        try:
            event, payload = self.event_queue.get(timeout=t)
            logger.debug("event=%s", event)
        except queue.Empty:
            return None, None
        return event, payload

    def bthci_write(self, command, payload=b""):
        data = pack("<BHB", HCI_PACKET_INDICATOR_BTHCI, command, len(payload)) + payload
        logger.verbose("UART TX[%s]:" + " %02x" * len(data), len(data), *data)
        self.read_thread.write(data)
        try:
            event, payload = self.event_queue.get(timeout=1)
            logger.verbose("event=%s", event)
            if event == EventID.SCRIPT_UNKNOWN_CMD:
                raise Error("The device cannot recognize command {!r}".format(command))
            elif event == HCI_EVENT_COMMAND_COMPLETED:
                opcode, status = unpack("<HB", payload[1:]);
                logger.debug("CC Payload[%s]:" + " %02x" * len(payload), len(payload), *payload)
                logger.debug("CommandCompleted:opcode=0x%04x, status=%d", opcode, status)
                if (opcode != command or status != 0):
                    raise Error("opcode {:04x} != command {:04x}".format(opcode, command))
        except queue.Empty:
            while not self.event_queue.empty():
                event, payload = self.event_queue.get_nowait()
                self.handle_event(event, payload)
            logger.debug("Timeout to read the result event.")
            raise

    def command_execute(self, command, data=b""):
        logger.debug("Send %s", command)
        self.write(CommandID.SCRIPT_EXECUTE, pack("<L", command) + data)
        try:
            event, payload = self.command_result_event_queue.get(timeout=1)
            if event == EventID.SCRIPT_UNKNOWN_CMD:
                raise Error("The device cannot recognize command {!r}".format(command))
            return payload
        except queue.Empty:
            while not self.event_queue.empty():
                event, payload = self.event_queue.get_nowait()
                self.handle_event(event, payload)
            logger.exception("Timeout to read the result event.")
            raise

    def handle_event(self, event, payload):
        logger.debug("event=%s", event)
        if event == HCI_EVENT_VENDOR_SPECIFIC_CODE:
            self.handle_vendor_specific_event(payload)
        elif event == HCI_EVENT_COMMAND_COMPLETED:
            logger.info("CommandComplete Payload[%s]:" + " %02x" * len(payload), len(payload), *payload)
        else:
            logger.warning(
                "Skip event: 0x{0:02x}, payload length: {1}, payload: {2}".format(
                    event, len(payload), payload
                )
            )

    def handle_vendor_specific_event(self, payload):
        sub_code = payload[0]
        if sub_code == HCI_EVENT_VS_DBFW_DUMP:
            dbfw.process_dump(payload[1:])
        else:
            logger.warning("Skip vendor specific event: 0x{0:02x}".format(sub_code))

    def update_baud_rate(self, rate):
        self.bthci_write(BthciCmdCBB.UPDATE_BAUD_RATE, pack('<HL', 0, rate))
        self.serial_instance.baudrate = rate

    def write_ram(self, addr, data):
        payload = pack("<L%dB" % len(data), addr, *data)
        self.bthci_write(BthciCmdCBB.WRITE_RAM, payload)

    def launch_ram(self):
        self.bthci_write(BthciCmdCBB.LAUNCH_RAM, bytearray.fromhex('ffffffff'))

    def read_audio(self):
        try:
            event_id, payload = self.audio_queue.get(timeout=1)
        except queue.Empty:
            return b'\xFF\xFF', b''
        except KeyboardInterrupt:
            raise
        return event_id, payload

    def send_sco(self, data):
        self.write(CommandID.RECORD_DATA, data)

    def send_button(self, data):
        self.write(CommandID.BUTTON, data)

    def push_nvram(self, id, data):
        payload = payload = pack("<H%dB" % len(data), int(id), *data)
        self.write(CommandID.PUSH_NVRAM, payload)

    def start_bt(self):
        self.write(CommandID.BT_START, b'')


class WicedHciProtocol(serial.threaded.Protocol):
    def __init__(self):
        self._data_buffer = bytearray()
        self._event_received = None

    @property
    def event_received(self):
        return self._event_received

    @event_received.setter
    def event_received(self, handler):
        self._event_received = handler

    def connection_made(self, transport):
        pass

    def data_received(self, data):
        logger.verbose("UART RX[%s]:" + " %02x" * len(data), len(data), *data)
        self._data_buffer += data

        if not self._event_received:
            return

        while len(self._data_buffer):
            try:
                indicator, event, payload = self.parse_event()
            except (Error, ValueError):
                # Handle packet lost, find the next valid header
                i = self._data_buffer.find(b'\x19')
                if i >= 0:
                    self._data_buffer = self._data_buffer[i:]
                    continue
                else:
                    break
            except:
                traceback.print_exc()
                raise

            if event:
                self._event_received(indicator, event, payload)
            else:
                break

    def connection_lost(self, exc):
        logger.debug("connection_lost:exc={}".format(exc))

    def parse_event(self):
        indicator = self._data_buffer[0]
        if indicator == HCI_PACKET_INDICATOR_EVENT:
            header_length = 3
            unpack_format = "<BB"
        elif indicator == HCI_PACKET_INDICATOR_WICED:
            header_length = 5
            unpack_format = "<HH"
        else:
            raise Error("Invalid header indicator: 0x{0:02x}".format(indicator))

        if len(self._data_buffer) < header_length:
            return indicator, None, None

        event_id, payload_length = unpack(
            unpack_format, self._data_buffer[1:header_length]
        )
        #logger.debug("event_id=%02x", event_id)

        if len(self._data_buffer) - header_length < payload_length:
            return indicator, None, None

        total_length = header_length + payload_length
        payload = self._data_buffer[header_length:total_length]
        self._data_buffer = self._data_buffer[total_length:]

        #logger.debug("Payload[%s]:" + " %02x" * len(payload), len(payload), *payload)
        return indicator, EventID(event_id), payload
