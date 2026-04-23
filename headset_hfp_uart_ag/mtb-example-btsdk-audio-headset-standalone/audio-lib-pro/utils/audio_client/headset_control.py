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
import getopt
import traceback
import struct

import hci
from ctypes.wintypes import CHAR

BUTTON_VALUE_INVALID = 0xFF

"""
Button ID and Button Event
"""
button_id_mapping = [{"id":"PLAY",  "value":0x00},
                     {"id":"PAUSE", "value":0x00},
                     {"id":"VOL+",  "value":0x01},
                     {"id":"VOL-",  "value":0x02},
                     {"id":"NEXT",  "value":0x01},
                     {"id":"PRE",   "value":0x02},
                     {"id":"VREC",  "value":0x03}];

button_event_mapping = [{"event":"CLICK",           "value":1 << 0},
                        {"event":"SHORT",           "value":1 << 1},
                        {"event":"MEDIUM",          "value":1 << 2},
                        {"event":"LONG",            "value":1 << 3},
                        {"event":"VERY_LONG",       "value":1 << 4},
                        {"event":"DOUBLE_CLICK",    "value":1 << 5},
                        {"event":"HOLDING",         "value":1 << 6}];

button_state_mapping = [{"state": "HELD",       "value":0},
                        {"state": "RELEASED",   "value":1}];

"""
Utilities
"""
# Usage
def print_usage():
    print("Usage: headset_control.py");
    print("           -d <COMPORT>");
    print("           -b <BAUDRATE>");
    print("           -f <FILE>: file to be download");
    print("           -button_id <BUTTON>: available values are PLAY, PAUSE, VOL+, VOL-, NEXT, PRE, VREC");
    print("           -button_event <BUTTON_EVENT>: available values are CLICK, SHORT, MEDIUM, LONG, VERY_LONG, DOUBLE_CLICK, HOLDING");
    print("           -button_state <BUTTON_STATE>: available values are HELD, RELEASED");

# Check the parameters (passed on the Command Line)
def check_parameter(param):
    try:
        sys.argv.index(param);
        return True;
    except:
        return False;

# Send button event to target
def button_event_send():
    if 'button_id' in globals() or 'button_event' in globals():
        if 'button_id' in globals() and 'button_event' in globals():
            # Check variable
            button_id_value = BUTTON_VALUE_INVALID;
            for entry in button_id_mapping:
                if (entry["id"] == button_id):
                    button_id_value = entry["value"];

            if (button_id_value == BUTTON_VALUE_INVALID):
                print("Error: invalid button id");
                return;

            button_event_value = BUTTON_VALUE_INVALID;
            for entry in button_event_mapping:
                if (entry["event"] == button_event):
                    button_event_value = entry["value"];

            if (button_event_value == BUTTON_VALUE_INVALID):
                print("Error: invalid button event");
                return;

            button_state_value = BUTTON_VALUE_INVALID;
            for entry in button_state_mapping:
                if (entry["state"] == button_state):
                    button_state_value = entry["value"];

            if (button_state_value == BUTTON_VALUE_INVALID):
                print("Error: invalid button state");
                return;

            # Transmit data to target board
            data = struct.pack("3b", button_id_value, button_event_value, button_state_value);
            print(data);
            controller.send_button(data);
        else:
            print("Error: button_id, button_event, and button_state shall be used together");
            return;

"""
Program Starts
"""
# Check parameters
if len(sys.argv) < 3:
    print_usage();
    sys.exit(2);

# Read parameters
if check_parameter('-b'):
    baudrate = sys.argv[sys.argv.index('-b')+1];
else:
    print_usage();
    sys.exit();

if check_parameter('-d'):
    serialport = sys.argv[sys.argv.index('-d')+1];
else:
    print_usage();
    sys.exit();

if check_parameter("-f"):
    file = sys.argv[sys.argv.index('-f')+1];

if check_parameter("-button_id"):
    button_id = sys.argv[sys.argv.index('-button_id')+1];

if check_parameter("-button_event"):
    button_event = sys.argv[sys.argv.index('-button_event')+1];

if check_parameter("-button_state"):
    button_state = sys.argv[sys.argv.index('-button_state')+1];

# Download file to target board
if 'file' in locals():
    command = 'py fw_download.py ' + serialport + ' ' + file;
    print(command);
    os.system(command);
    sys.exit();

# Open COM port
try:
    controller = hci.Controller(serialport, int(baudrate))
except:
    traceback.print_exc();
    sys.exit();

# Send button event to target
button_event_send();

# Close COM port
controller.close();
