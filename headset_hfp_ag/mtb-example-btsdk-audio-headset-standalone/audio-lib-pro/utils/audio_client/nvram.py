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
import logging
import json
import base64

class nvram:
    def __init__(self):
        self.filename = 'nvram.json'
        if os.path.isfile(self.filename):
            with open(self.filename, 'r') as f:
                self.key_info = json.load(f)
        else:
            self.key_info = {}

    def close(self):
        self.file.close()

    def write(self, id, data):
        new_data = {id: base64.b64encode(data).decode("ascii")}
        self.key_info.update(new_data)
        with open(self.filename, 'w+') as f:
            json.dump(self.key_info, f)

    def read(self, id):
        with open(self.filename, 'r') as f:
            self.key_info = json.load(f)
            s = self.key_info[str(id)]
            data = base64.b64decode(s)
        return data

    def delete(self, id):
        if (self.key_info.get(id) != None):
            self.key_info.pop(str(id))
            with open(self.filename, 'w+') as f:
                json.dump(self.key_info, f)

    def ids(self):
        return self.key_info.keys()

    def print(self):
        for i, (id, s) in enumerate(self.key_info.items()):
            key = base64.b64decode(s)
            print ("{}:{}:".format(id, s) + " ".join(format(b, '02x') for b in key))
