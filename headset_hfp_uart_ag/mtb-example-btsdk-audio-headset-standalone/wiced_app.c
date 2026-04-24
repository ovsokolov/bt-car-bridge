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
 * This file implements the entry point of the Wiced Application
 */
#include <sparcommon.h>
#ifdef WICED_APP_AMS_INCLUDED
#include <wiced_bt_ams.h>
#endif
#ifdef WICED_APP_HFP_AG_INCLUDED
#include "hci_control_hfp_ag.h"
#include <wiced_bt_hfp_ag.h>
#endif
#ifdef WICED_APP_HFP_HF_INCLUDED
#include "hci_control_hfp_hf.h"
#include "wiced_bt_hfp_hf_int.h"
#endif
#include <wiced_bt_stack.h>
#include <wiced_bt_trace.h>
#include <wiced_bt_l2c.h>
#include <wiced_memory.h>
#include <wiced_timer.h>
#if (defined(CYW20721B2) || defined(CYW43012C0))
#include <wiced_utilities.h>
#endif
#include <wiced_platform.h>
#include <wiced_hal_gpio.h>
#include <wiced_hal_puart.h>
#if ( defined(CYW20706A2) || defined(CYW20719B1) || defined(CYW20721B1) || defined(CYW43012C0) )
#include <wiced_bt_app_common.h>
#endif
#include "hci_control.h"
#include "hci_control_audio.h"
#include "hci_control_le.h"
#include "hci_control_rc_controller.h"
#include "hci_control_rc_target.h"
#include "le_peripheral.h"
#include "wiced_app_cfg.h"
#include "wiced_app.h"
#ifdef CYW9BT_AUDIO
#include <wiced_audio_manager.h>
#endif

#ifdef CYW43012C0
#include "wiced_memory.h"

static wiced_bt_buffer_pool_t* watch_app_pool_big = NULL;
static wiced_bt_buffer_pool_t* watch_app_pool_small = NULL;
#endif

#define WICED_HS_EIR_BUF_MAX_SIZE 264


static void write_eir(void);
static wiced_result_t btm_enabled_event_handler(wiced_bt_dev_enabled_t *event_data);
static void delayed_bond_dump(TIMER_PARAM_TYPE arg);
static void log_bond_state(void);
static void ag_autoreconnect_timer_cb(TIMER_PARAM_TYPE arg);
static wiced_bool_t ag_get_last_bonded_device(wiced_bt_device_address_t bd_addr);

#if defined(CYW20819A1)
#include "wiced_memory_pre_init.h"
/* override weak version of this struct to adjust memory for audio application */
WICED_MEM_PRE_INIT_CONTROL g_mem_pre_init =
{
    .max_ble_connections = WICED_MEM_PRE_INIT_IGNORE,
    .max_peripheral_piconet = WICED_MEM_PRE_INIT_IGNORE, /* use to reduce Bluetooth connections */
    .max_resolving_list = WICED_MEM_PRE_INIT_IGNORE,
    .onfound_list_len = 0,
    .max_multi_adv_instances = WICED_MEM_PRE_INIT_IGNORE,
};
#endif

static app_identity_random_mapping_t addr_mapping[ADDR_MAPPING_MAX_COUNT] = {0};
static wiced_timer_t delayed_bond_dump_timer;
static wiced_timer_t ag_autoreconnect_timer;
static wiced_bt_device_address_t ag_autoreconnect_bda = {0};
static wiced_bool_t ag_manual_disconnect_pending = WICED_FALSE;
static uint8_t ag_autoreconnect_stage = 0;
static uint8_t ag_autoreconnect_retry_count = 0;

#define AG_AUTORECONNECT_STAGE_HFP   1
#define AG_AUTORECONNECT_STAGE_AVRCP 2
#define AG_AUTORECONNECT_STAGE_A2DP  3
#define AG_AUTORECONNECT_BACKOFF_CAP_SECONDS 30U

extern wiced_result_t av_app_initiate_sdp(BD_ADDR bda);

static uint32_t ag_autoreconnect_next_backoff(uint32_t base_delay_seconds)
{
    uint32_t shift = ag_autoreconnect_retry_count;
    uint32_t delay = base_delay_seconds;

    if (delay == 0U)
    {
        delay = 2U;
    }

    if (shift > 4U)
    {
        shift = 4U;
    }

    delay <<= shift;
    if (delay > AG_AUTORECONNECT_BACKOFF_CAP_SECONDS)
    {
        delay = AG_AUTORECONNECT_BACKOFF_CAP_SECONDS;
    }

    if (ag_autoreconnect_retry_count < 0xFFU)
    {
        ag_autoreconnect_retry_count++;
    }

    return delay;
}

void hf_note_manual_ag_disconnect(void)
{
    ag_manual_disconnect_pending = WICED_TRUE;
    ag_autoreconnect_retry_count = 0;
}

void hf_note_manual_ag_connect(void)
{
    ag_manual_disconnect_pending = WICED_FALSE;
    ag_autoreconnect_retry_count = 0;
}

void hf_autoreconnect_restart_full(const wiced_bt_device_address_t bd_addr, uint32_t delay_seconds)
{
    static const wiced_bt_device_address_t empty_bda = {0};

    if (memcmp(bd_addr, empty_bda, BD_ADDR_LEN) == 0)
    {
        return;
    }

    memcpy(ag_autoreconnect_bda, bd_addr, BD_ADDR_LEN);
    ag_autoreconnect_stage = AG_AUTORECONNECT_STAGE_HFP;
    wiced_stop_timer(&ag_autoreconnect_timer);
    wiced_start_timer(&ag_autoreconnect_timer, (delay_seconds == 0U) ? 1U : delay_seconds);

    WICED_BT_TRACE("[AUTO_AG] queued staged reconnect to <%B> in %lu sec (retry_count=%u)\n",
                   ag_autoreconnect_bda,
                   (unsigned long)((delay_seconds == 0U) ? 1U : delay_seconds),
                   ag_autoreconnect_retry_count);
}

static void ag_autoreconnect_timer_cb(TIMER_PARAM_TYPE arg)
{
    UNUSED_VARIABLE(arg);

    if (ag_autoreconnect_stage == AG_AUTORECONNECT_STAGE_HFP)
    {
        WICED_BT_TRACE("[AUTO_AG] reconnect stage HFP to <%B>\n", ag_autoreconnect_bda);
        hfp_ag_connect(ag_autoreconnect_bda);
        ag_autoreconnect_stage = AG_AUTORECONNECT_STAGE_AVRCP;
        ag_autoreconnect_retry_count = 0;
        wiced_start_timer(&ag_autoreconnect_timer, 1);
    }
    else if (ag_autoreconnect_stage == AG_AUTORECONNECT_STAGE_AVRCP)
    {
        WICED_BT_TRACE("[AUTO_AG] reconnect stage AVRCP TG to <%B>\n", ag_autoreconnect_bda);
        wiced_bt_avrc_tg_initiate_open(ag_autoreconnect_bda);
        ag_autoreconnect_stage = AG_AUTORECONNECT_STAGE_A2DP;
        ag_autoreconnect_retry_count = 0;
        wiced_start_timer(&ag_autoreconnect_timer, 1);
    }
    else if (ag_autoreconnect_stage == AG_AUTORECONNECT_STAGE_A2DP)
    {
        WICED_BT_TRACE("[AUTO_AG] reconnect stage A2DP source to <%B>\n", ag_autoreconnect_bda);
        av_app_initiate_sdp(ag_autoreconnect_bda);
        ag_autoreconnect_stage = 0;
        ag_autoreconnect_retry_count = 0;
    }
}

static wiced_bool_t ag_get_last_bonded_device(wiced_bt_device_address_t bd_addr)
{
    hci_control_nvram_chunk_t *chunk = p_nvram_first;

    if (chunk != NULL)
    {
        memcpy(bd_addr, chunk->data, BD_ADDR_LEN);
        return WICED_TRUE;
    }

    return WICED_FALSE;
}

/*
 * Application Start, ie, entry point to the application.
 */
#ifndef APPLICATION_START
void APPLICATION_START()
#else
APPLICATION_START()
#endif
{
    wiced_result_t result;

    hci_control_init();

#ifdef WICED_BT_TRACE_ENABLE
#ifdef NO_PUART_SUPPORT
#if defined(CYW43012C0)
    wiced_debug_uart = WICED_ROUTE_DEBUG_TO_DBG_UART;
    debug_uart_enable(3000000);
#else // CYW43012C0
    wiced_set_debug_uart(WICED_ROUTE_DEBUG_TO_WICED_UART);
#endif // CYW43012C0
#else
    /* Reserve PUART for the inter-board bridge; keep formatted debug on the host path. */
    wiced_set_debug_uart( WICED_ROUTE_DEBUG_TO_WICED_UART );
#endif // NO_PUART_SUPPORT
#endif // WICED_BT_TRACE_ENABLE

    result = app_stack_init();

    if (WICED_SUCCESS != result)
    {
        WICED_BT_TRACE("ERROR bt_stack_init %u\n", result);
        return;
    }

    result = wiced_audio_buffer_initialize(wiced_bt_audio_buf_config);
    if (WICED_SUCCESS != result)
    {
        WICED_BT_TRACE("ERROR audio_buffer_init %u\n", result);
        return;
    }

#ifdef WICED_APP_LE_INCLUDED
    hci_control_le_init();
#endif

#ifdef WICED_APP_LE_PERIPHERAL_CLIENT_INCLUDED
    le_peripheral_app_init();
#endif
#ifndef DEBUG
    //Enable the Bluetooth coex functionality
//    wiced_bt_coex_enable();
#endif

    WICED_BT_TRACE("Watch App Start\n");
}

app_identity_random_mapping_t * get_addr_mapping_by_random_addr(wiced_bt_device_address_t random_addr)
{
    for (int i=0; i<ADDR_MAPPING_MAX_COUNT;i++)
    {
        if (memcmp(random_addr, addr_mapping[i].random_addr, sizeof(wiced_bt_device_address_t))==0)
            return &addr_mapping[i];
    }
    return NULL;
}

app_identity_random_mapping_t * get_addr_mapping_by_identity_addr(wiced_bt_device_address_t identity_addr)
{
    for (int i=0; i<ADDR_MAPPING_MAX_COUNT;i++)
    {
        if (memcmp(identity_addr, addr_mapping[i].identity_addr, sizeof(wiced_bt_device_address_t))==0)
            return &addr_mapping[i];
    }
    return NULL;
}

app_identity_random_mapping_t * get_empty_addr_mapping()
{
    wiced_bt_device_address_t empty_addr={0};

    return get_addr_mapping_by_identity_addr(empty_addr);
}

void write_eir(void)
{
    uint8_t *pBuf;
    uint8_t *p, *p_tmp;
    uint8_t nb_uuid = 0;
    uint8_t length;

    //Allocating a buffer from the public pool
    pBuf = (uint8_t *)wiced_bt_get_buffer( WICED_HS_EIR_BUF_MAX_SIZE );

    WICED_BT_TRACE("%s %x\n", __func__, pBuf);

    if ( !pBuf )
    {
        return;
    }

    p = pBuf;

    length = strlen( (char *)wiced_bt_cfg_settings.device_name );
    UINT8_TO_STREAM(p, length + 1);
    UINT8_TO_STREAM(p, BT_EIR_COMPLETE_LOCAL_NAME_TYPE);
    memcpy( p, wiced_bt_cfg_settings.device_name, length );
    p += length;

    // Add other BR/EDR UUIDs
    p_tmp = p;      // We don't now the number of UUIDs for the moment
    p++;
    UINT8_TO_STREAM(p, BT_EIR_COMPLETE_16BITS_UUID_TYPE);
#ifdef WICED_APP_AUDIO_SRC_INCLUDED
    UINT16_TO_STREAM(p, UUID_SERVCLASS_AUDIO_SOURCE);       nb_uuid++;
#endif
#ifdef WICED_APP_AUDIO_RC_TG_INCLUDED
    UINT16_TO_STREAM(p, UUID_SERVCLASS_AV_REM_CTRL_TARGET); nb_uuid++;
#endif
#ifdef WICED_APP_AUDIO_RC_CT_INCLUDED
    UINT16_TO_STREAM(p, UUID_SERVCLASS_AV_REMOTE_CONTROL);  nb_uuid++;
    UINT16_TO_STREAM(p, UUID_SERVCLASS_AUDIO_SINK);         nb_uuid++;
#endif
#if (defined(WICED_APP_HFP_AG_INCLUDED) || defined(WICED_APP_HFP_HF_INCLUDED))
    UINT16_TO_STREAM(p, UUID_SERVCLASS_HEADSET);            nb_uuid++;
    UINT16_TO_STREAM(p, UUID_SERVCLASS_HF_HANDSFREE);       nb_uuid++;
    UINT16_TO_STREAM(p, UUID_SERVCLASS_GENERIC_AUDIO);      nb_uuid++;
#endif

#ifdef WICED_APP_PANU_INCLUDED
    UINT16_TO_STREAM(p, UUID_SERVCLASS_PANU);               nb_uuid++;
#endif
#ifdef WICED_APP_PANNAP_INCLUDED
    UINT16_TO_STREAM(p, UUID_SERVCLASS_NAP);                nb_uuid++;
#endif
    /* Now, we can update the UUID Tag's length */
    UINT8_TO_STREAM(p_tmp, (nb_uuid * LEN_UUID_16) + 1);

    // Last Tag
    UINT8_TO_STREAM(p, 0x00);

    // print EIR data
    WICED_BT_TRACE_ARRAY( ( uint8_t* )( pBuf ), MIN( p - ( uint8_t* )pBuf, 100 ), "EIR :" );
    wiced_bt_dev_write_eir( pBuf, (uint16_t)(p - pBuf) );

    /* Allocated buffer not anymore needed. Free it */
    wiced_bt_free_buffer( pBuf );

    return;
}

static void log_bond_state(void)
{
    hci_control_nvram_chunk_t *chunk = p_nvram_first;
    uint8_t chunk_count = 0;
    uint8_t mapping_count = 0;
    uint8_t i;

    WICED_BT_TRACE("BOND_DUMP begin\n");

    while (chunk != NULL)
    {
        chunk_count++;
        WICED_BT_TRACE("BOND_DUMP nvram_id:%d len:%d addr:%B\n",
                       chunk->nvram_id,
                       chunk->chunk_len,
                       chunk->data);
        chunk = (hci_control_nvram_chunk_t *)chunk->p_next;
    }

    for (i = 0; i < ADDR_MAPPING_MAX_COUNT; i++)
    {
        static const wiced_bt_device_address_t empty_addr = {0};

        if (memcmp(addr_mapping[i].identity_addr, empty_addr, BD_ADDR_LEN) != 0 ||
            memcmp(addr_mapping[i].random_addr, empty_addr, BD_ADDR_LEN) != 0)
        {
            mapping_count++;
            WICED_BT_TRACE("BOND_DUMP map[%d] identity:%B random:%B\n",
                           i,
                           addr_mapping[i].identity_addr,
                           addr_mapping[i].random_addr);
        }
    }

    WICED_BT_TRACE("BOND_DUMP summary nvram:%d maps:%d\n", chunk_count, mapping_count);
}

static void delayed_bond_dump(TIMER_PARAM_TYPE arg)
{
    WICED_BT_TRACE("BOND_DUMP delayed snapshot\n");
    log_bond_state();
}

wiced_result_t btm_event_handler(wiced_bt_management_evt_t event, wiced_bt_management_evt_data_t *p_event_data)
{
    wiced_result_t                     result = WICED_BT_SUCCESS;
    wiced_bt_dev_encryption_status_t  *p_encryption_status;
    int                                bytes_written, bytes_read;
    int                                nvram_id;
    wiced_bt_power_mgmt_notification_t *p_power_mgmt_notification;
    wiced_bt_dev_pairing_cplt_t        *p_pairing_cmpl;
    uint8_t                             pairing_result;

    WICED_BT_TRACE( "btm_event_handler 0x%02x\n", event );

    switch( event )
    {
        /* Bluetooth stack enabled */
        case BTM_ENABLED_EVT:
            result = btm_enabled_event_handler(&p_event_data->enabled);
            break;

        case BTM_DISABLED_EVT:
            hci_control_send_device_error_evt(p_event_data->disabled.reason, 0);
            break;

        case BTM_PIN_REQUEST_EVT:
            WICED_BT_TRACE("[PAIR] PIN request from %B\n", p_event_data->pin_request.bd_addr);
            hci_control_send_pin_request_evt(*p_event_data->pin_request.bd_addr);
            break;

        case BTM_USER_CONFIRMATION_REQUEST_EVT:
            WICED_BT_TRACE("[PAIR] User confirmation request from %B just_works:%d numeric:%lu\n",
                           p_event_data->user_confirmation_request.bd_addr,
                           p_event_data->user_confirmation_request.just_works,
                           (unsigned long)p_event_data->user_confirmation_request.numeric_value);
            // If this is just works pairing, accept. Otherwise send event to the MCU to confirm the same value.
            if (p_event_data->user_confirmation_request.just_works)
            {
                wiced_bt_dev_confirm_req_reply( WICED_BT_SUCCESS, p_event_data->user_confirmation_request.bd_addr );
            }
            else
            {
                hci_control_send_user_confirmation_request_evt(p_event_data->user_confirmation_request.bd_addr, p_event_data->user_confirmation_request.numeric_value );
            }
            break;

        case BTM_PASSKEY_NOTIFICATION_EVT:
            WICED_BT_TRACE("PassKey Notification. BDA %B, Key %d \n", p_event_data->user_passkey_notification.bd_addr, p_event_data->user_passkey_notification.passkey );
            hci_control_send_user_confirmation_request_evt(p_event_data->user_passkey_notification.bd_addr, p_event_data->user_passkey_notification.passkey );
            break;

        case BTM_PAIRING_IO_CAPABILITIES_BR_EDR_REQUEST_EVT:
            /* Use the default security for BR/EDR*/
            WICED_BT_TRACE("BTM_PAIRING_IO_CAPABILITIES_BR_EDR_REQUEST_EVT bda %B\n", p_event_data->pairing_io_capabilities_br_edr_request.bd_addr);
            p_event_data->pairing_io_capabilities_br_edr_request.local_io_cap = BTM_IO_CAPABILITIES_DISPLAY_AND_YES_NO_INPUT;
            p_event_data->pairing_io_capabilities_br_edr_request.oob_data     = WICED_FALSE;
            p_event_data->pairing_io_capabilities_br_edr_request.auth_req     = BTM_AUTH_ALL_PROFILES_YES;
            break;

        case BTM_PAIRING_IO_CAPABILITIES_BLE_REQUEST_EVT:
            /* Use the default security for LE */
            WICED_BT_TRACE("BTM_PAIRING_IO_CAPABILITIES_BLE_REQUEST_EVT bda %B\n",
                    p_event_data->pairing_io_capabilities_ble_request.bd_addr);
            p_event_data->pairing_io_capabilities_ble_request.local_io_cap  = BTM_IO_CAPABILITIES_DISPLAY_AND_YES_NO_INPUT;
            p_event_data->pairing_io_capabilities_ble_request.oob_data      = BTM_OOB_NONE;
            p_event_data->pairing_io_capabilities_ble_request.auth_req      = BTM_LE_AUTH_REQ_SC_MITM_BOND;
            p_event_data->pairing_io_capabilities_ble_request.max_key_size  = 16;
            p_event_data->pairing_io_capabilities_ble_request.init_keys     = BTM_LE_KEY_PENC|BTM_LE_KEY_PID|BTM_LE_KEY_PCSRK|BTM_LE_KEY_LENC;
            p_event_data->pairing_io_capabilities_ble_request.resp_keys     = BTM_LE_KEY_PENC|BTM_LE_KEY_PID|BTM_LE_KEY_PCSRK|BTM_LE_KEY_LENC;
            break;

        case BTM_PAIRING_COMPLETE_EVT:
            p_pairing_cmpl = &p_event_data->pairing_complete;
            if(p_pairing_cmpl->transport == BT_TRANSPORT_BR_EDR)
            {
                pairing_result = p_pairing_cmpl->pairing_complete_info.br_edr.status;
                WICED_BT_TRACE("[PAIR] BR/EDR pairing complete peer:%B status:%d\n",
                               p_event_data->pairing_complete.bd_addr,
                               pairing_result);
                hci_control_send_pairing_completed_evt( pairing_result, p_event_data->pairing_complete.bd_addr );
                if (pairing_result == WICED_BT_SUCCESS)
                {
                    ag_manual_disconnect_pending = WICED_FALSE;
                    ag_autoreconnect_retry_count = 0;
                    hf_autoreconnect_restart_full(p_event_data->pairing_complete.bd_addr, 1);
                }
            }
            else
            {
                pairing_result = p_pairing_cmpl->pairing_complete_info.ble.reason;
                WICED_BT_TRACE("[PAIR] LE pairing complete peer:%B reason:%d\n",
                               p_event_data->pairing_complete.bd_addr,
                               pairing_result);
                app_identity_random_mapping_t * addr_map = get_addr_mapping_by_random_addr(p_event_data->pairing_complete.bd_addr);
                if ( addr_map != NULL )
                {
                    hci_control_send_pairing_completed_evt( pairing_result, addr_map->identity_addr );
                }
            }
            WICED_BT_TRACE( "Pairing Result: %d\n", pairing_result );
            break;

        case BTM_ENCRYPTION_STATUS_EVT:
            p_encryption_status = &p_event_data->encryption_status;

            WICED_BT_TRACE("[PAIR] Encryption status peer:%B transport:%d result:%d\n",
                           p_encryption_status->bd_addr,
                           p_encryption_status->transport,
                           p_encryption_status->result);

#ifdef WICED_APP_LE_PERIPHERAL_CLIENT_INCLUDED
            if (p_encryption_status->transport == BT_TRANSPORT_LE)
                le_peripheral_encryption_status_changed(p_encryption_status);
#endif
            hci_control_send_encryption_changed_evt( p_encryption_status->result, p_encryption_status->bd_addr );
            if ((hfp_profile_role == HFP_AUDIO_GATEWAY_ROLE) &&
                (p_encryption_status->transport == BT_TRANSPORT_BR_EDR) &&
                (p_encryption_status->result != WICED_BT_SUCCESS))
            {
                if (ag_manual_disconnect_pending)
                {
                    ag_manual_disconnect_pending = WICED_FALSE;
                    WICED_BT_TRACE("[AUTO_AG] skip reconnect after manual disconnect\n");
                }
                else
                {
                    uint32_t retry_delay = ag_autoreconnect_next_backoff(2);
                    WICED_BT_TRACE("[AUTO_AG] encryption failure reconnect backoff=%lu sec (retry_count=%u)\n",
                                   (unsigned long)retry_delay,
                                   ag_autoreconnect_retry_count);
                    hf_autoreconnect_restart_full(p_encryption_status->bd_addr, retry_delay);
                }
            }
            else if ((hfp_profile_role == HFP_AUDIO_GATEWAY_ROLE) &&
                     (p_encryption_status->transport == BT_TRANSPORT_BR_EDR) &&
                     (p_encryption_status->result == WICED_BT_SUCCESS))
            {
                ag_autoreconnect_retry_count = 0;
            }
            break;

        case BTM_SECURITY_REQUEST_EVT:
            WICED_BT_TRACE("[PAIR] Security request from %B pairing_allowed:%d\n",
                           p_event_data->security_request.bd_addr,
                           hci_control_cb.pairing_allowed);
            if ( hci_control_cb.pairing_allowed )
            {
                wiced_bt_ble_security_grant( p_event_data->security_request.bd_addr, WICED_BT_SUCCESS );
            }
            else
            {
                // Pairing not allowed, return error
                result = WICED_BT_ERROR;
            }
            break;

        case BTM_PAIRED_DEVICE_LINK_KEYS_UPDATE_EVT:
            WICED_BT_TRACE("[PAIR] Link keys update for %B\n",
                           p_event_data->paired_device_link_keys_update.bd_addr);
            app_paired_device_link_keys_update( p_event_data );
            break;

        case  BTM_PAIRED_DEVICE_LINK_KEYS_REQUEST_EVT:
            /* read existing key from the NVRAM  */
            WICED_BT_TRACE("[PAIR] Link keys request for %B\n",
                           p_event_data->paired_device_link_keys_request.bd_addr);

            if ( ( nvram_id = hci_control_find_nvram_id( p_event_data->paired_device_link_keys_request.bd_addr, BD_ADDR_LEN ) ) != 0)
            {
                 bytes_read = hci_control_read_nvram( nvram_id, &p_event_data->paired_device_link_keys_request, sizeof( wiced_bt_device_link_keys_t ) );

                 result = WICED_BT_SUCCESS;
                 WICED_BT_TRACE("Read:nvram_id:%d bytes:%d\n", nvram_id, bytes_read);
            }
            else
            {
                result = WICED_BT_ERROR;
                WICED_BT_TRACE("Key retrieval failure\n");
            }
            break;

        case BTM_LOCAL_IDENTITY_KEYS_UPDATE_EVT:
            /* Request to store newly generated local identity keys to NVRAM */
            /* (sample app does not store keys to NVRAM) */

            break;


        case BTM_LOCAL_IDENTITY_KEYS_REQUEST_EVT:
            /*
             * Request to restore local identity keys from NVRAM
             * (requested during Bluetooth start up)
             * */
            /* (sample app does not store keys to NVRAM)
             * New local identity keys will be generated
             * */
            result = WICED_BT_NO_RESOURCES;
            break;
#ifdef WICED_APP_LE_INCLUDED

        case BTM_BLE_SCAN_STATE_CHANGED_EVT:
            hci_control_le_scan_state_changed( p_event_data->ble_scan_state_changed );
            break;

        case BTM_BLE_ADVERT_STATE_CHANGED_EVT:
            WICED_BT_TRACE("BLE_ADVERT_STATE_CHANGED_EVT:%d\n", p_event_data->ble_advert_state_changed);
            hci_control_le_advert_state_changed( p_event_data->ble_advert_state_changed );
            break;

        case BTM_BLE_CONNECTION_PARAM_UPDATE:
            WICED_BT_TRACE ("BTM LE Connection Update event status %d BDA [%B] interval %d latency %d supervision timeout %d \n",
                                p_event_data->ble_connection_param_update.status, p_event_data->ble_connection_param_update.bd_addr,
                                p_event_data->ble_connection_param_update.conn_interval, p_event_data->ble_connection_param_update.conn_latency,
                                p_event_data->ble_connection_param_update.supervision_timeout);

            if(p_event_data->ble_connection_param_update.supervision_timeout != 600)
            {
                uint8_t index = find_index_by_address(p_event_data->ble_connection_param_update.bd_addr);

                if (index == 0xFF)
                    index = 0;
                else
                    index++;
                wiced_bt_l2cap_update_ble_conn_params( p_event_data->ble_connection_param_update.bd_addr, 108, 108 + 12*index, 0, 600 );
            }
            break;
#endif

        case BTM_POWER_MANAGEMENT_STATUS_EVT:
            p_power_mgmt_notification = &p_event_data->power_mgmt_notification;
            WICED_BT_TRACE("Power mgmt status event: bd ( %B ) status:%d hci_status:%d\n", p_power_mgmt_notification->bd_addr,
                    p_power_mgmt_notification->status, p_power_mgmt_notification->hci_status);
            break;

        case BTM_SCO_CONNECTED_EVT:
        case BTM_SCO_DISCONNECTED_EVT:
        case BTM_SCO_CONNECTION_REQUEST_EVT:
        case BTM_SCO_CONNECTION_CHANGE_EVT:
#ifdef WICED_APP_HFP_AG_INCLUDED
            if (hfp_profile_role == HFP_AUDIO_GATEWAY_ROLE)
            {
                hfp_ag_sco_management_callback( event, p_event_data );
            }
#endif
#ifdef WICED_APP_HFP_HF_INCLUDED
            if (hfp_profile_role == HFP_HANDSFREE_UNIT_ROLE)
            {
                hci_control_hf_sco_management_callback( event, p_event_data );
            }
#endif
            break;

        default:
            result = WICED_BT_USE_DEFAULT_SECURITY;
            break;
    }
    return result;
}

wiced_result_t btm_enabled_event_handler(wiced_bt_dev_enabled_t *event_data)
{
    wiced_result_t result;
    wiced_bt_device_address_t bonded_addr = {0};

#ifdef CYW20706A2
    wiced_bt_app_init();
#endif

    write_eir( );

    /* create SDP records */
    if (!wiced_bt_sdp_db_init((uint8_t *)wiced_app_cfg_sdp_record, wiced_app_cfg_sdp_record_get_size()))
    {
        WICED_BT_TRACE("ERROR sdp_db_init\n");
        return WICED_BT_ERROR;
    }

    hci_control_post_init();

#ifdef CYW9BT_AUDIO
    /* Initialize AudioManager */
    wiced_am_init();
#endif

    WICED_BT_TRACE("Free Bytes After Init:%d\n", wiced_memory_get_free_bytes());

    wiced_init_timer(&delayed_bond_dump_timer, delayed_bond_dump, 0, WICED_SECONDS_TIMER);
    wiced_start_timer(&delayed_bond_dump_timer, 3);
    wiced_init_timer(&ag_autoreconnect_timer, ag_autoreconnect_timer_cb, 0, WICED_SECONDS_TIMER);

    wiced_bt_dev_set_discoverability(BTM_GENERAL_DISCOVERABLE,
                                     BTM_DEFAULT_DISC_WINDOW,
                                     BTM_DEFAULT_DISC_INTERVAL);
    wiced_bt_dev_set_connectability(WICED_TRUE,
                                    BTM_DEFAULT_CONN_WINDOW,
                                    BTM_DEFAULT_CONN_INTERVAL);
    hci_control_cb.pairing_allowed = WICED_TRUE;
    wiced_bt_set_pairable_mode(WICED_TRUE, 0);
    WICED_BT_TRACE("Boot default visibility/connectability/pairability enabled\n");

    if (ag_get_last_bonded_device(bonded_addr))
    {
        ag_autoreconnect_retry_count = 0;
        WICED_BT_TRACE("[AUTO_AG] boot reconnect target <%B>\n", bonded_addr);
        hf_autoreconnect_restart_full(bonded_addr, 2);
    }
    else
    {
        WICED_BT_TRACE("[AUTO_AG] no bonded peer found at boot; waiting for manual pair/connect\n");
    }

    return WICED_BT_SUCCESS;
}
