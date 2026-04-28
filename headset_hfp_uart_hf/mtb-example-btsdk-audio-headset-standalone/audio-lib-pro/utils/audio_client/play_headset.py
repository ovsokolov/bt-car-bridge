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
import os
import sys
import hci
import logging
import struct
import queue
import pyaudio
import traceback
import signal
import time
from fw_dl import fw_download
import pynput
from pynput import keyboard
from hci import EventID
from nvram import nvram
import base64
import threading

# Debug level
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Button ID and Button Event
button_id_mapping = {
    "PLAY":  0x00,
    "PAUSE": 0x00,
    "VOL+":  0x01,
    "VOL-":  0x02,
    "NEXT":  0x01,
    "PRE":   0x02,
    "VREC":  0x03
}

button_event_mapping = {
    "CLICK":           1 << 0,
    "SHORT":           1 << 1,
    "MEDIUM":          1 << 2,
    "LONG":            1 << 3,
    "VERY_LONG":       1 << 4,
    "DOUBLE_CLICK":    1 << 5,
    "HOLDING":         1 << 6
}

button_state_mapping = {
    "HELD":       0,
    "RELEASED":   1
}

# Stream type mapping
stream_type_mapping = {
    "A2DP": 0,
    "HFP":  1
}

# Stream volume level
stream_volume_level = {
    "HIGH": 10,
    "LOW":  0
}

# Signal Ctrl + C
def keyboardInterruptHandler(signal, frame):
    logger.debug("KeyboardInterrupt (ID: {}) has been caught.".format(signal))
    pynput.keyboard.Listener.stop
    exit(0)
signal.signal(signal.SIGINT, keyboardInterruptHandler)

# Serial number included in audio data frame
audio_sn_included = 1

# FW Download
is_fw_download = True
if (len(sys.argv) == 4):
    com_port = sys.argv[1]
    hcd_path = sys.argv[2]
    audio_sn_included = sys.argv[3]
elif (len(sys.argv) == 3):
    com_port = sys.argv[1]
    audio_sn_included = sys.argv[2]
    is_fw_download = False
elif (len(sys.argv) == 2):
    com_port = sys.argv[1]
    is_fw_download = False
else:
    basename = os.path.basename(sys.argv[0])
    print("Usage:")
    print("         {} <com_port> <hcd file> <is_audio_sn_included>".format(basename))
    print("\n         OR\n")
    print("         {} <com_port> <is_audio_sn_included>".format(basename))
    print("         {} <com_port>       : Run without downloading firmware".format(basename))
    exit(1)

if (is_fw_download):
    if (os.path.exists(hcd_path) != True):
        print("Cannot open file: {}.".format(hcd_path))
        exit(1)

    status, control = fw_download(com_port, hcd_path)
    if (status != True):
        print("FW download failed")
        exit(1)
    is_device_started = False
    for i in range(3):
        event, payload = control.read_event(2)
        if (event == hci.EventID.DEVICE_STARTED):
            is_device_started = True
            break
    if (is_device_started == False):
        print("DEVICE_STARTED timeout")
        exit(1)
else:
    # Default speed: 115200 bps
    baud_rate = 3000000
    control = hci.Controller(com_port, baud_rate)

nv = nvram()
for id in nv.ids():
    key = nv.read(id)
    control.push_nvram(id, key)

control.start_bt()

# PyAudio
p = pyaudio.PyAudio()
callback_finished = threading.Event()
callback_stop_stream = threading.Event()
def rec_callback(in_data, frame_count, time_info, status):
    if callback_stop_stream.is_set():
        print("[Python] enter callback when in the stop stream process")
        return (b'', pyaudio.paContinue)

    callback_finished.clear()  # flag set when sending sco to controller
    control.send_sco(in_data)
    callback_finished.set()
    return (b'', pyaudio.paContinue)

def stream_stop():
    if 'play_stream' in globals():
        if play_stream.is_active():
            play_stream.stop_stream()
            play_stream.close()
            del globals()['play_stream']

    if 'rec_stream' in globals():
        if (rec_stream.is_active()):
            callback_stop_stream.set()  # set stop stream flag
            if callback_finished.is_set() is False:
                print("[Python] Found callback is not finished")

            callback_finished.wait()  # wait callback finish
            print("[Python] Waiting callback finished")

            if control.serial_instance.out_waiting > 0:  # if it's in writing process
                control.serial_instance.flush()          # blocking wait for serial write finish
                time.sleep(0.1)

            rec_stream.stop_stream()
            rec_stream.close()
            del globals()['rec_stream']
            callback_stop_stream.clear()

# Kayboard handling
play_state = False
def on_press(key):
    try:
        pass
    except AttributeError:
        pass

def on_release(key):
    global play_state

    if key == keyboard.Key.f1:
        print('Button Allow Pairing')
        data = struct.pack("3b", button_id_mapping["PLAY"], button_event_mapping["VERY_LONG"], button_state_mapping["HELD"])
        control.send_button(data)
    elif key == keyboard.Key.f2:
        print('Button Play/Pause')
        if (play_state == True):
            data = struct.pack("3b", button_id_mapping["PAUSE"], button_event_mapping["CLICK"], button_state_mapping["RELEASED"])
            play_state = False
        else:
            data = struct.pack("3b", button_id_mapping["PLAY"], button_event_mapping["CLICK"], button_state_mapping["RELEASED"])
            play_state = True
        control.send_button(data)
    elif key == keyboard.Key.f3:
        print('Button Prev')
        data = struct.pack("3b", button_id_mapping["PRE"], button_event_mapping["VERY_LONG"], button_state_mapping["RELEASED"])
        control.send_button(data)
    elif key == keyboard.Key.f4:
        print('Button Next')
        data = struct.pack("3b", button_id_mapping["NEXT"], button_event_mapping["VERY_LONG"], button_state_mapping["RELEASED"])
        control.send_button(data)

listener = keyboard.Listener(
    on_press=on_press,
    on_release=on_release)
listener.start()

skip_count = 0
last_sn = -1
print('Headset control is starting. Press Ctrl+C to stop')
print('F1: Allow Pairing, HFP Decline')
print('F2: A2DP Play/Pause, HFP Answer/Hang up')
print('F3: Prev')
print('F4: Next')

"""
Set default value for streaming
"""
sample_format = pyaudio.paInt16
channels = 2
sample_rate = 44100
chunk = 120
volume = 8

try:
    while (1):
        event_id, payload = control.read_audio()

        if event_id == EventID.STREAM_START.value:  # Streaming starts
            # Check payload length
            if (len(payload) != 1):
                continue

            # Read stream type
            stream_type = payload[0]

            if (stream_type != stream_type_mapping["A2DP"] and
                stream_type != stream_type_mapping["HFP"]):
                continue

            if stream_type == stream_type_mapping["A2DP"]: # A2DP
                play_state = True
                last_sn = -1
            elif stream_type == stream_type_mapping["HFP"]: # HFP
                rec_stream = p.open(format = sample_format,
                                    channels = channels,
                                    rate = sample_rate,
                                    frames_per_buffer = chunk,
                                    input = True,
                                    stream_callback = rec_callback)

                rec_stream.start_stream()

            play_stream = p.open(format = sample_format,
                                 channels = channels,
                                 rate = sample_rate,
                                 output = True)
            play_stream.start_stream()
            skip_count = 3  # skip frames to avoid overflow
        elif event_id == EventID.STREAM_STOP.value: # Stream stops
            # Check payload length
            if (len(payload) != 1):
                continue

            stream_stop()
            play_state = False
        elif event_id == EventID.STREAM_CONFIG.value: # Stream configure
            # Check payload length
            if (len(payload) != 7):
                continue;

            # Read configuration
            sample_rate, samples, channels, volume = struct.unpack("<i3B", payload[0:])

        elif event_id == EventID.STREAM_VOLUME.value: # Stream volume
            # Check payload length
            if (len(payload) != struct.calcsize("i")):
                continue

            # Abstract volume value
            volume = int.from_bytes(payload[0:struct.calcsize("i")], byteorder = 'little', signed = False)

            # Check volume value
            if (volume < stream_volume_level["LOW"] or volume > stream_volume_level["HIGH"]):
                continue

            print("Set volume level: ", volume);
            # Transporm the volume to system 100% level - todo

        elif (event_id == EventID.AUDIO_DATA.value or \
              event_id == EventID.SCO_DATA.value):
            if 'stream_type' in locals() and 'play_stream' in globals():
                if (stream_type != stream_type_mapping["A2DP"] and
                    stream_type != stream_type_mapping["HFP"]):
                    continue

                if (skip_count > 0):
                    skip_count = skip_count - 1
                    continue

                if stream_type == stream_type_mapping["A2DP"]: # A2DP
                    if audio_sn_included == 1:
                        # Check payload length
                        if (len(payload) <= struct.calcsize("HH")):
                            continue
                        audio_type, sn = struct.unpack_from("<HH", payload)
                        # serial number check
                        if (last_sn != -1 and sn != (last_sn + 1) & 0xffff):
                            print("Warning: serial number jumps {} to {}".format(last_sn, sn))
                        last_sn = sn
                        pcm_data = payload[struct.calcsize("HH"):]
                    else:
                        pcm_data = payload;
                elif stream_type == stream_type_mapping["HFP"]: # HFP
                    # Check payload length
                    if (len(payload) <= 0):
                        continue
                    pcm_data = payload
                play_stream.write(bytes(pcm_data))
        elif (event_id == EventID.WRITE_NVRAM_DATA.value):
            vs_id = int.from_bytes(payload[0:struct.calcsize("H")], byteorder = 'little', signed = False)
            key = payload[struct.calcsize("H"):]
            nv.write(str(vs_id), key)

        elif (event_id == EventID.DELETE_NVRAM_DATA.value):
            # Check payload length
            if (len(payload) != struct.calcsize("H")):
                continue

            vs_id = int.from_bytes(payload[0:struct.calcsize("H")], byteorder = 'little', signed = False)
            nv.delete(str(vs_id))

        if (listener.running == False):
            break

except SystemExit:
    exit(0)
except:
    traceback.print_exc()
    exit(1)
finally:
    print('Headset control stopped')
    stream_stop()
    p.terminate()
    control.close()
    listener.stop()

exit(0)
