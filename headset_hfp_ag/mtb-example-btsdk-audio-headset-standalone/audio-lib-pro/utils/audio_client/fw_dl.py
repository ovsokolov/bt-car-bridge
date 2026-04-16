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
import queue
import logging
from struct import pack, unpack, calcsize
from pathlib import Path
import hci
import hcd

# Debug level
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fw_download(port, hcd_path):
    baud_rate = 115200
    com_port = port
    hcd_filename = Path(hcd_path)
    hcd_file = hcd.HCD_File(Path(hcd_filename))

    # Open COM port
    try:
        control = hci.Controller(com_port, baud_rate)
    except:
        logger.error("Cannot open port {}".format(com_port))
        control.close()
        return False, None

    # Try 115200 bps
    try:
        control.bthci_write(hci.BthciCmdCBB.RESET)
    except queue.Empty:
        # if no response, try to update baud rate to 3M
        control.close()
        baud_rate = 3000000
        control = hci.Controller(com_port, baud_rate)
        control.bthci_write(hci.BthciCmdCBB.RESET)
    except:
        logger.error("Cannot open port {}".format(com_port))
        control.close()
        return False, None

    # Change buad rate to 3000000 bps
    try:
        if (baud_rate != 3000000):
            control.update_baud_rate(3000000)
            control.bthci_write(hci.BthciCmdCBB.RESET)
    except:
        logger.error("Cannot open port {}".format(com_port))
        control.close()
        return False, None

    control.bthci_write(hci.BthciCmdCBB.DOWNLOAD_MINIDRIVER)

    dl_ok = False
    while (1):
        addr, rec_size, data_buffer, launch = hcd_file.ReadNextHCDRecord()
        try:
            control.write_ram(addr, data_buffer)
        except:
            return False, None
        if (launch):
            logger.info("Download file success")
            dl_ok = True
            break

    if dl_ok != True:
        logger.info("Download file failed")
        hcd_file.close()
        control.close()
        return False, None

    logger.info("Launch RAM")
    control.launch_ram()
    hcd_file.close()
    return True, control
