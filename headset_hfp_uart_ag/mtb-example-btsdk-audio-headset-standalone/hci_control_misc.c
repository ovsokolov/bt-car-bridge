/*
 * Copyright 2016-2024, Cypress Semiconductor Corporation (an Infineon company) or
 * an affiliate of Cypress Semiconductor Corporation.  All rights reserved.
 *
 * This software, including source code, documentation and related
 * materials ("Software") is owned by Cypress Semiconductor Corporation
 * or one of its affiliates ("Cypress") and is protected by and subject to
 * worldwide patent protection (United States and foreign),
 * United States copyright laws and international treaty provisions.
 * Therefore, you may use this Software only as provided in the license
 * agreement accompanying the software package from which you
 * obtained this Software ("EULA").
 * If no EULA applies, Cypress hereby grants you a personal, non-exclusive,
 * non-transferable license to copy, modify, and compile the Software
 * source code solely for use in connection with Cypress's
 * integrated circuit products.  Any reproduction, modification, translation,
 * compilation, or representation of this Software except as specified
 * above is prohibited without the express written permission of Cypress.
 *
 * Disclaimer: THIS SOFTWARE IS PROVIDED AS-IS, WITH NO WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, NONINFRINGEMENT, IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. Cypress
 * reserves the right to make changes to the Software without notice. Cypress
 * does not assume any liability arising out of the application or use of the
 * Software or any product or circuit described in the Software. Cypress does
 * not authorize its products for use in any products where a malfunction or
 * failure of the Cypress product may reasonably be expected to result in
 * significant property damage, injury or death ("High Risk Product"). By
 * including Cypress's product in a High Risk Product, the manufacturer
 * of such system or application assumes all risk of such use and in doing
 * so agrees to indemnify Cypress against all liability.
 */

/** @file
 *
 * This file implements the Miscellaneous Commands controlled over UART. Please refer to
 * the WICED HCI Control Protocol Software User Manual (WICED-SWUM10x-R) for additional
 * details on the HCI UART control protocol
 */

#include "wiced_bt_cfg.h"
#include "hci_control_api.h"
#include "hci_control.h"
#include "hci_control_audio.h"
#include "wiced_app_cfg.h"
#include "wiced_memory.h"
#include "wiced_transport.h"
#include <string.h>

#define BCM920706 20706
#define BCM920707 20707

/******************************************************************************
 *                          Constants
 ******************************************************************************/

/******************************************************************************
 *                          Function Declarations
 ******************************************************************************/
void hci_control_misc_handle_get_version( void );
static void hci_control_misc_send_identity(void);
static void hci_control_misc_send_profile_summary(void);
static void hci_control_misc_send_audio_diag(void);
static char *hci_control_misc_append_text(char *dst, char *end, const char *text);
static char *hci_control_misc_append_sep(char *dst, char *end, uint8_t *first_item);
static char *hci_control_misc_append_audio_role(char *dst, char *end, uint8_t role, uint8_t *first_item);

extern uint8_t ag_startup_stage;
extern uint8_t ag_audio_init_result;
extern uint32_t ag_audio_free_before;
extern uint32_t ag_audio_free_after;

#define HCI_CONTROL_MISC_EVENT_AG_AUDIO_INIT_DIAG   ((HCI_CONTROL_GROUP_MISC << 8) | 0x23)
#define HCI_CONTROL_MISC_EVENT_PROFILE_SUMMARY      ((HCI_CONTROL_GROUP_MISC << 8) | 0x24)
static const char bridge_identity_base[] = "NavTool-CarConnect-AGTEST63";

/******************************************************************************
 *                          Variable Definitions
 ******************************************************************************/

/******************************************************************************
 *                          Function Definitions
 ******************************************************************************/
void hci_control_misc_handle_command( uint16_t cmd_opcode, uint8_t* p_data, uint32_t data_len )
{
    switch( cmd_opcode )
    {
    case HCI_CONTROL_MISC_COMMAND_PING:
        wiced_transport_send_data( HCI_CONTROL_MISC_EVENT_PING_REPLY, p_data, data_len );
        break;

    case HCI_CONTROL_MISC_COMMAND_GET_VERSION:
        hci_control_misc_handle_get_version();
        break;

    default:
        WICED_BT_TRACE( "unknown miscellaneous command\n");
        break;
    }
}

void hci_control_misc_handle_get_version( void )
{
    uint8_t   tx_buf[20];
    uint8_t   cmd = 0;

// If this is 20819 or 20820, we do detect the device from hardware
#define RADIO_ID    0x006007c0
#define RADIO_20820 0x80
#define CHIP_20820  20820
#define CHIP_20819  20819
#if (CHIP==CHIP_20819) || (CHIP==CHIP_20820)
    uint32_t chip = CHIP_20819;
    if (*(UINT32*) RADIO_ID & RADIO_20820)
    {
        chip = CHIP_20820;
    }
#else
    uint32_t  chip = CHIP;
#endif

    tx_buf[cmd++] = WICED_SDK_MAJOR_VER;
    tx_buf[cmd++] = WICED_SDK_MINOR_VER;
    tx_buf[cmd++] = WICED_SDK_REV_NUMBER;
    tx_buf[cmd++] = WICED_SDK_BUILD_NUMBER & 0xFF;
    tx_buf[cmd++] = (WICED_SDK_BUILD_NUMBER>>8) & 0xFF;
    tx_buf[cmd++] = chip & 0xFF;
    tx_buf[cmd++] = (chip>>8) & 0xFF;
    tx_buf[cmd++] = (chip>>24) & 0xFF;
    tx_buf[cmd++] = 0; // not used

    /* Send MCU app the supported features */
#ifdef WICED_APP_LE_INCLUDED
    tx_buf[cmd++] = HCI_CONTROL_GROUP_GATT;
#endif
#ifdef WICED_APP_AUDIO_SRC_INCLUDED
    tx_buf[cmd++] = HCI_CONTROL_GROUP_AUDIO;
#endif
#ifdef WICED_APP_ANCS_INCLUDED
    tx_buf[cmd++] = HCI_CONTROL_GROUP_ANCS;
#endif
#ifdef WICED_APP_AUDIO_RC_CT_INCLUDED
    tx_buf[cmd++] = HCI_CONTROL_GROUP_AVRC_CONTROLLER;
#endif
#ifdef WICED_APP_AMS_INCLUDED
    tx_buf[cmd++] = HCI_CONTROL_GROUP_AMS;
#endif
#ifdef WICED_APP_AUDIO_RC_TG_INCLUDED
    tx_buf[cmd++] = HCI_CONTROL_GROUP_AVRC_TARGET;
#endif
#ifdef WICED_APP_HFP_AG_INCLUDED
    tx_buf[cmd++] = HCI_CONTROL_GROUP_AG;
#endif
#ifdef WICED_APP_HFP_HF_INCLUDED
    tx_buf[cmd++] = HCI_CONTROL_GROUP_HF;
#endif

#ifdef WICED_APP_PANU_INCLUDED
    tx_buf[cmd++] = HCI_CONTROL_GROUP_PANU;
#endif
    wiced_transport_send_data( HCI_CONTROL_MISC_EVENT_VERSION, tx_buf, cmd );
    hci_control_misc_send_identity();
    hci_control_misc_send_profile_summary();
    hci_control_misc_send_audio_diag();

    hci_control_audio_support_features_send();
}

static void hci_control_misc_send_identity(void)
{
    char identity[64];
    static const char hex[] = "0123456789ABCDEF";
    uint16_t len = (uint16_t)strlen(bridge_identity_base);

    if ((len + 8U) >= sizeof(identity))
    {
        return;
    }

    memcpy(identity, bridge_identity_base, len);
    identity[len++] = '-';
    identity[len++] = 'S';
    identity[len++] = (char)('0' + (ag_startup_stage % 10U));
    identity[len++] = '-';
    identity[len++] = 'A';
    identity[len++] = 'I';
    identity[len++] = hex[(ag_audio_init_result >> 4) & 0x0F];
    identity[len++] = hex[ag_audio_init_result & 0x0F];
    identity[len] = '\0';

    wiced_transport_send_data(HCI_CONTROL_MISC_EVENT_BRIDGE_IDENTITY, (uint8_t *)identity, len);
}

static void hci_control_misc_send_profile_summary(void)
{
    char summary[128];
    char *p = summary;
    char *end = summary + sizeof(summary) - 1;
    uint8_t first_profile = 1;
    uint8_t first_role = 1;

    p = hci_control_misc_append_text(p, end, "profiles=");

#ifdef WICED_APP_LE_INCLUDED
    p = hci_control_misc_append_sep(p, end, &first_profile);
    p = hci_control_misc_append_text(p, end, "LE");
#endif
#ifdef WICED_APP_AUDIO_SRC_INCLUDED
    p = hci_control_misc_append_sep(p, end, &first_profile);
    p = hci_control_misc_append_text(p, end, "A2DP_SRC");
#endif
#ifdef WICED_APP_AUDIO_RC_CT_INCLUDED
    p = hci_control_misc_append_sep(p, end, &first_profile);
    p = hci_control_misc_append_text(p, end, "AVRCP_CT");
#endif
#ifdef WICED_APP_AUDIO_RC_TG_INCLUDED
    p = hci_control_misc_append_sep(p, end, &first_profile);
    p = hci_control_misc_append_text(p, end, "AVRCP_TG");
#endif
#ifdef WICED_APP_HFP_AG_INCLUDED
    p = hci_control_misc_append_sep(p, end, &first_profile);
    p = hci_control_misc_append_text(p, end, "HFP_AG");
#endif
#ifdef WICED_APP_HFP_HF_INCLUDED
    p = hci_control_misc_append_sep(p, end, &first_profile);
    p = hci_control_misc_append_text(p, end, "HFP_HF");
#endif

    p = hci_control_misc_append_text(p, end, " audio_role=");
    p = hci_control_misc_append_audio_role(p, end, (uint8_t)wiced_bt_audio_buf_config.role, &first_role);
    if (first_role)
    {
        p = hci_control_misc_append_text(p, end, "NONE");
    }

    *p = '\0';

    wiced_transport_send_data(HCI_CONTROL_MISC_EVENT_PROFILE_SUMMARY,
                              (uint8_t *)summary,
                              (uint16_t)strlen(summary));
}

static void hci_control_misc_send_audio_diag(void)
{
    uint8_t payload[23] = { 0 };
    uint32_t free_before = ag_audio_free_before;
    uint32_t free_after = ag_audio_free_after;
    uint32_t tx_size = wiced_bt_audio_buf_config.audio_tx_buffer_size;
    uint32_t codec_size = wiced_bt_audio_buf_config.audio_codec_buffer_size;

    if ((free_before == 0U) && (free_after == 0U))
    {
        free_before = wiced_memory_get_free_bytes();
        free_after = free_before;
    }

    payload[0] = (uint8_t)wiced_bt_audio_buf_config.role;
    payload[1] = ag_audio_init_result;
    payload[2] = (uint8_t)(free_before & 0xFF);
    payload[3] = (uint8_t)((free_before >> 8) & 0xFF);
    payload[4] = (uint8_t)((free_before >> 16) & 0xFF);
    payload[5] = (uint8_t)((free_before >> 24) & 0xFF);
    payload[6] = (uint8_t)(free_after & 0xFF);
    payload[7] = (uint8_t)((free_after >> 8) & 0xFF);
    payload[8] = (uint8_t)((free_after >> 16) & 0xFF);
    payload[9] = (uint8_t)((free_after >> 24) & 0xFF);
    payload[14] = (uint8_t)(tx_size & 0xFF);
    payload[15] = (uint8_t)((tx_size >> 8) & 0xFF);
    payload[16] = (uint8_t)((tx_size >> 16) & 0xFF);
    payload[17] = (uint8_t)((tx_size >> 24) & 0xFF);
    payload[18] = (uint8_t)(codec_size & 0xFF);
    payload[19] = (uint8_t)((codec_size >> 8) & 0xFF);
    payload[20] = (uint8_t)((codec_size >> 16) & 0xFF);
    payload[21] = (uint8_t)((codec_size >> 24) & 0xFF);
    payload[22] = ag_startup_stage;

    wiced_transport_send_data(HCI_CONTROL_MISC_EVENT_AG_AUDIO_INIT_DIAG, payload, sizeof(payload));
}

static char *hci_control_misc_append_text(char *dst, char *end, const char *text)
{
    while ((dst < end) && (*text != '\0'))
    {
        *dst++ = *text++;
    }
    return dst;
}

static char *hci_control_misc_append_sep(char *dst, char *end, uint8_t *first_item)
{
    if (!(*first_item))
    {
        dst = hci_control_misc_append_text(dst, end, "+");
    }
    else
    {
        *first_item = 0;
    }
    return dst;
}

static char *hci_control_misc_append_audio_role(char *dst, char *end, uint8_t role, uint8_t *first_item)
{
    if (role & WICED_AUDIO_SOURCE_ROLE)
    {
        dst = hci_control_misc_append_sep(dst, end, first_item);
        dst = hci_control_misc_append_text(dst, end, "A2DP_SRC");
    }
    if (role & WICED_AUDIO_SINK_ROLE)
    {
        dst = hci_control_misc_append_sep(dst, end, first_item);
        dst = hci_control_misc_append_text(dst, end, "A2DP_SINK");
    }
    if (role & WICED_HF_ROLE)
    {
        dst = hci_control_misc_append_sep(dst, end, first_item);
        dst = hci_control_misc_append_text(dst, end, "HF");
    }
    return dst;
}
