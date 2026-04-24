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
#include "hci_control_hfp_hf.h"
#include "hci_control_rc_controller.h"
#include "hci_control_rc_target.h"
#include "headset_nvram.h"
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

typedef enum
{
    HF_AUTORECONNECT_IDLE = 0,
    HF_AUTORECONNECT_HFP,
    HF_AUTORECONNECT_AVRCP,
    HF_AUTORECONNECT_A2DP,
} hf_autoreconnect_stage_t;

static void write_eir(void);
static wiced_result_t btm_enabled_event_handler(wiced_bt_dev_enabled_t *event_data);
static void delayed_bond_dump(TIMER_PARAM_TYPE arg);
static void log_bond_state(void);
static void hf_autoreconnect_timer_cb(TIMER_PARAM_TYPE arg);
static wiced_bool_t hf_get_last_bonded_device(wiced_bt_device_address_t bd_addr);
static void hf_schedule_autoreconnect(const wiced_bt_device_address_t bd_addr, uint32_t delay_seconds);
static void hf_schedule_autoreconnect_stage(const wiced_bt_device_address_t bd_addr,
                                            hf_autoreconnect_stage_t stage,
                                            uint32_t delay_seconds);
static void hf_start_autoreconnect(const char *reason, uint32_t delay_seconds);
static void apply_role_specific_local_address(void);
static void enable_pairing_visibility_when_unbonded(void);
static void recover_from_stale_bond(const wiced_bt_device_address_t bd_addr, const char *reason);
static wiced_bool_t hf_autoreconnect_status_ok_for_progress(wiced_result_t status);

extern wiced_result_t av_app_initiate_sdp(BD_ADDR bda);

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
static wiced_timer_t hf_autoreconnect_timer;
static wiced_bt_device_address_t hf_autoreconnect_bda = {0};

static hf_autoreconnect_stage_t hf_autoreconnect_stage = HF_AUTORECONNECT_IDLE;

static const char *hf_autoreconnect_role_name(void)
{
    return (hfp_profile_role == HFP_AUDIO_GATEWAY_ROLE) ? "AG" : "HF";
}

static void apply_role_specific_local_address(void)
{
    wiced_bt_device_address_t current_addr = {0};
    wiced_bt_device_address_t desired_addr = {0};
    wiced_bt_device_address_t effective_addr = {0};

    wiced_bt_dev_read_local_addr(current_addr);
    memcpy(desired_addr, current_addr, BD_ADDR_LEN);

    /*
     * Ensure HF and AG firmware images cannot keep the exact same local address
     * when both are built/flashed from one workspace.
     */
    if (hfp_profile_role == HFP_AUDIO_GATEWAY_ROLE)
    {
        /* Flip the low byte in the device-specific portion. */
        desired_addr[BD_ADDR_LEN - 1] ^= 0x01;
    }

    if (memcmp(current_addr, desired_addr, BD_ADDR_LEN) != 0)
    {
        wiced_bt_set_local_bdaddr(desired_addr, BLE_ADDR_PUBLIC);
        wiced_bt_dev_read_local_addr(effective_addr);
        WICED_BT_TRACE("[AUTO_%s] set_local_bdaddr issued current=<%B> desired=<%B> effective=<%B>\n",
                       hf_autoreconnect_role_name(),
                       current_addr,
                       desired_addr,
                       effective_addr);
    }
    else
    {
        WICED_BT_TRACE("[AUTO_%s] local address kept as <%B>\n",
                       hf_autoreconnect_role_name(),
                       current_addr);
    }
}

static void enable_pairing_visibility_when_unbonded(void)
{
    wiced_bt_device_address_t bonded_addr = {0};

    if (hf_get_last_bonded_device(bonded_addr))
    {
        WICED_BT_TRACE("[AUTO_%s] bonded peer exists <%B>; keeping default hidden/pairable-off policy\n",
                       hf_autoreconnect_role_name(),
                       bonded_addr);
        return;
    }

    wiced_bt_set_pairable_mode(WICED_TRUE, 0);
    wiced_bt_dev_set_discoverability(BTM_GENERAL_DISCOVERABLE,
                                     BTM_DEFAULT_DISC_WINDOW,
                                     BTM_DEFAULT_DISC_INTERVAL);
    wiced_bt_dev_set_connectability(WICED_TRUE,
                                    BTM_DEFAULT_CONN_WINDOW,
                                    BTM_DEFAULT_CONN_INTERVAL);

    WICED_BT_TRACE("[AUTO_%s] no bonded peer: auto-enabled pairable/discoverable/connectable for first-time pairing\n",
                   hf_autoreconnect_role_name());
}

static void recover_from_stale_bond(const wiced_bt_device_address_t bd_addr, const char *reason)
{
    int nvram_id = hci_control_find_nvram_id((uint8_t *)bd_addr, BD_ADDR_LEN);

    if (nvram_id != 0)
    {
        WICED_BT_TRACE("[AUTO_%s] stale bond recovery (%s): deleting key id %d for <%B>\n",
                       hf_autoreconnect_role_name(),
                       reason,
                       nvram_id,
                       bd_addr);
        hci_control_delete_nvram(nvram_id, WICED_FALSE);
    }

    wiced_bt_set_pairable_mode(WICED_TRUE, 0);
    wiced_bt_dev_set_discoverability(BTM_GENERAL_DISCOVERABLE,
                                     BTM_DEFAULT_DISC_WINDOW,
                                     BTM_DEFAULT_DISC_INTERVAL);
    wiced_bt_dev_set_connectability(WICED_TRUE,
                                    BTM_DEFAULT_CONN_WINDOW,
                                    BTM_DEFAULT_CONN_INTERVAL);

    WICED_BT_TRACE("[AUTO_%s] stale bond recovery (%s): enabled pairable/discoverable/connectable\n",
                   hf_autoreconnect_role_name(),
                   reason);
}

static wiced_bool_t hf_autoreconnect_status_ok_for_progress(wiced_result_t status)
{
    return (status == WICED_BT_SUCCESS ||
            status == WICED_BT_PENDING ||
            status == WICED_BT_BUSY ||
            status == WICED_ALREADY_CONNECTED);
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
    debug_uart_enable(921600);
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

    WICED_BT_TRACE("Headset HF App Start\n");
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
    UINT16_TO_STREAM(p, UUID_SERVCLASS_AUDIO_SINK);         nb_uuid++;
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

static wiced_bool_t hf_get_last_bonded_device(wiced_bt_device_address_t bd_addr)
{
    hci_control_nvram_chunk_t *chunk = p_nvram_first;
    wiced_result_t nvram_status;
    wiced_bt_device_link_keys_t link_keys;
    int nvram_id;

    if (chunk != NULL)
    {
        memcpy(bd_addr, chunk->data, BD_ADDR_LEN);
        return WICED_TRUE;
    }

    for (nvram_id = WICED_NVRAM_VSID_END; nvram_id >= WICED_NVRAM_VSID_START; nvram_id--)
    {
        if (wiced_hal_read_nvram((uint8_t)nvram_id,
                                 sizeof(link_keys),
                                 (uint8_t *)&link_keys,
                                 &nvram_status) == sizeof(link_keys))
        {
            memcpy(bd_addr, link_keys.bd_addr, BD_ADDR_LEN);
            return WICED_TRUE;
        }

        if (nvram_id == WICED_NVRAM_VSID_START)
        {
            break;
        }
    }

    return WICED_FALSE;
}

static void hf_schedule_autoreconnect(const wiced_bt_device_address_t bd_addr, uint32_t delay_seconds)
{
    hf_schedule_autoreconnect_stage(bd_addr, HF_AUTORECONNECT_HFP, delay_seconds);
}

static void hf_schedule_autoreconnect_stage(const wiced_bt_device_address_t bd_addr,
                                            hf_autoreconnect_stage_t stage,
                                            uint32_t delay_seconds)
{
    memcpy(hf_autoreconnect_bda, bd_addr, BD_ADDR_LEN);
    hf_autoreconnect_stage = stage;
    wiced_stop_timer(&hf_autoreconnect_timer);
    wiced_start_timer(&hf_autoreconnect_timer, delay_seconds);
    WICED_BT_TRACE("[AUTO_%s] scheduled stage %d to <%B> in %lu sec\n",
                   hf_autoreconnect_role_name(),
                   stage,
                   hf_autoreconnect_bda,
                   (unsigned long)delay_seconds);
}

void hf_autoreconnect_restart_full(const wiced_bt_device_address_t bd_addr, uint32_t delay_seconds)
{
    hf_schedule_autoreconnect_stage(bd_addr, HF_AUTORECONNECT_HFP, delay_seconds);
}

void hf_autoreconnect_continue_from_hfp(const wiced_bt_device_address_t bd_addr, uint32_t delay_seconds)
{
    hf_schedule_autoreconnect_stage(bd_addr, HF_AUTORECONNECT_AVRCP, delay_seconds);
}

void hf_autoreconnect_continue_from_avrcp(const wiced_bt_device_address_t bd_addr, uint32_t delay_seconds)
{
    hf_schedule_autoreconnect_stage(bd_addr, HF_AUTORECONNECT_A2DP, delay_seconds);
}

static void hf_start_autoreconnect(const char *reason, uint32_t delay_seconds)
{
    wiced_bt_device_address_t bd_addr = {0};

    if (!hf_get_last_bonded_device(bd_addr))
    {
        WICED_BT_TRACE("[AUTO_%s] no bonded peer available for %s\n",
                       hf_autoreconnect_role_name(),
                       reason);
        return;
    }

    WICED_BT_TRACE("[AUTO_%s] using bonded peer <%B> after %s\n",
                   hf_autoreconnect_role_name(),
                   bd_addr,
                   reason);
    hf_schedule_autoreconnect(bd_addr, delay_seconds);
}

static void hf_autoreconnect_timer_cb(TIMER_PARAM_TYPE arg)
{
    uint8_t audio_format_cmd[2] = { AUDIO_SRC_AUDIO_DATA_FORMAT_PCM, AUDIO_ROUTE_I2S };
    wiced_result_t status = WICED_BT_SUCCESS;

    UNUSED_VARIABLE(arg);

    switch (hf_autoreconnect_stage)
    {
    case HF_AUTORECONNECT_HFP:
        if (hfp_profile_role == HFP_AUDIO_GATEWAY_ROLE)
        {
#ifdef WICED_APP_HFP_AG_INCLUDED
            WICED_BT_TRACE("[AUTO_AG] connecting HFP AG to <%B>\n", hf_autoreconnect_bda);
            hfp_ag_connect(hf_autoreconnect_bda);
            status = WICED_BT_PENDING;
#else
            WICED_BT_TRACE("[AUTO_AG] HFP AG profile is not enabled in this build\n");
            status = WICED_BT_UNSUPPORTED;
#endif
        }
        else
        {
#ifdef WICED_APP_HFP_HF_INCLUDED
            WICED_BT_TRACE("[AUTO_HF] connecting HFP HF to <%B>\n", hf_autoreconnect_bda);
            status = wiced_bt_hfp_hf_connect(hf_autoreconnect_bda);
#else
            WICED_BT_TRACE("[AUTO_HF] HFP HF profile is not enabled in this build\n");
            status = WICED_BT_UNSUPPORTED;
#endif
        }
        if (status == WICED_BT_SUCCESS || status == WICED_ALREADY_CONNECTED || status == WICED_BT_UNSUPPORTED)
        {
            hf_schedule_autoreconnect_stage(hf_autoreconnect_bda, HF_AUTORECONNECT_AVRCP, 1);
            return;
        }
        break;

    case HF_AUTORECONNECT_AVRCP:
        if (hfp_profile_role == HFP_AUDIO_GATEWAY_ROLE)
        {
#ifdef WICED_APP_AUDIO_RC_TG_INCLUDED
            WICED_BT_TRACE("[AUTO_AG] connecting AVRCP TG to <%B>\n", hf_autoreconnect_bda);
            wiced_bt_avrc_tg_initiate_open(hf_autoreconnect_bda);
            status = WICED_BT_PENDING;
#else
            WICED_BT_TRACE("[AUTO_AG] AVRCP TG profile is not enabled in this build\n");
            status = WICED_BT_UNSUPPORTED;
#endif
        }
        else
        {
#ifdef WICED_APP_AUDIO_RC_CT_INCLUDED
            WICED_BT_TRACE("[AUTO_HF] connecting AVRCP CT to <%B>\n", hf_autoreconnect_bda);
            status = wiced_bt_avrc_ct_connect(hf_autoreconnect_bda);
#else
            WICED_BT_TRACE("[AUTO_HF] AVRCP CT profile is not enabled in this build\n");
            status = WICED_BT_UNSUPPORTED;
#endif
        }
        if (status == WICED_BT_SUCCESS || status == WICED_ALREADY_CONNECTED || status == WICED_BT_UNSUPPORTED)
        {
            hf_schedule_autoreconnect_stage(hf_autoreconnect_bda, HF_AUTORECONNECT_A2DP, 1);
            return;
        }
        break;

    case HF_AUTORECONNECT_A2DP:
        if (hfp_profile_role == HFP_AUDIO_GATEWAY_ROLE)
        {
#ifdef WICED_APP_AUDIO_SRC_INCLUDED
            WICED_BT_TRACE("[AUTO_AG] connecting A2DP source to <%B>\n", hf_autoreconnect_bda);
            status = av_app_initiate_sdp(hf_autoreconnect_bda);
#else
            WICED_BT_TRACE("[AUTO_AG] A2DP source profile is not enabled in this build\n");
            status = WICED_BT_UNSUPPORTED;
#endif
        }
        else
        {
#ifdef WICED_APP_AUDIO_SRC_INCLUDED
            WICED_BT_TRACE("[AUTO_HF] connecting A2DP sink to <%B> via I2S\n", hf_autoreconnect_bda);
            hci_control_audio_handle_command(HCI_CONTROL_AUDIO_DATA_FORMAT,
                                             audio_format_cmd,
                                             sizeof(audio_format_cmd));
            status = av_app_initiate_sdp(hf_autoreconnect_bda);
#else
            WICED_BT_TRACE("[AUTO_HF] A2DP profile is not enabled in this build\n");
            status = WICED_BT_UNSUPPORTED;
#endif
        }
        break;

    default:
        return;
    }

    WICED_BT_TRACE("[AUTO_%s] stage result %d\n", hf_autoreconnect_role_name(), status);

    hf_autoreconnect_stage = HF_AUTORECONNECT_IDLE;
    if (!hf_autoreconnect_status_ok_for_progress(status))
    {
        WICED_BT_TRACE("[AUTO_%s] stage failure detected; scheduling reconnect retry\n",
                       hf_autoreconnect_role_name());
        hf_start_autoreconnect("stage failure", 5);
    }
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
            WICED_BT_TRACE("remote address= %B\n", p_event_data->pin_request.bd_addr);
            hci_control_send_pin_request_evt(*p_event_data->pin_request.bd_addr);
            break;

        case BTM_USER_CONFIRMATION_REQUEST_EVT:
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
            p_event_data->pairing_io_capabilities_br_edr_request.local_io_cap = BTM_IO_CAPABILITIES_NONE;
            p_event_data->pairing_io_capabilities_br_edr_request.oob_data     = WICED_FALSE;
            p_event_data->pairing_io_capabilities_br_edr_request.auth_req     = BTM_AUTH_SINGLE_PROFILE_GENERAL_BONDING_NO;
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
                hci_control_send_pairing_completed_evt( pairing_result, p_event_data->pairing_complete.bd_addr );
                if (pairing_result == WICED_BT_SUCCESS)
                {
                    hf_autoreconnect_restart_full(p_event_data->pairing_complete.bd_addr, 1);
                }
                else
                {
                    recover_from_stale_bond(p_event_data->pairing_complete.bd_addr, "pairing failure");
                }
            }
            else
            {
                pairing_result = p_pairing_cmpl->pairing_complete_info.ble.reason;
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

            WICED_BT_TRACE( "Encryption Status:(%B) res:%d\n", p_encryption_status->bd_addr, p_encryption_status->result );

#ifdef WICED_APP_LE_PERIPHERAL_CLIENT_INCLUDED
            if (p_encryption_status->transport == BT_TRANSPORT_LE)
                le_peripheral_encryption_status_changed(p_encryption_status);
#endif
            hci_control_send_encryption_changed_evt( p_encryption_status->result, p_encryption_status->bd_addr );
            if ((p_encryption_status->transport == BT_TRANSPORT_BR_EDR) &&
                (p_encryption_status->result != WICED_BT_SUCCESS))
            {
                recover_from_stale_bond(p_encryption_status->bd_addr, "encryption failure");
            }
            break;

        case BTM_SECURITY_REQUEST_EVT:
            WICED_BT_TRACE( "Security Request Event, Pairing allowed %d\n", hci_control_cb.pairing_allowed );
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
            app_paired_device_link_keys_update( p_event_data );
            break;

        case  BTM_PAIRED_DEVICE_LINK_KEYS_REQUEST_EVT:
            /* read existing key from the NVRAM  */
            WICED_BT_TRACE("\t\tfind device %B\n", p_event_data->paired_device_link_keys_request.bd_addr);

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

    apply_role_specific_local_address();
    enable_pairing_visibility_when_unbonded();

#ifdef CYW9BT_AUDIO
    /* Initialize AudioManager */
    wiced_am_init();
#endif

    WICED_BT_TRACE("Free Bytes After Init:%d\n", wiced_memory_get_free_bytes());

    wiced_init_timer(&delayed_bond_dump_timer, delayed_bond_dump, 0, WICED_SECONDS_TIMER);
    wiced_start_timer(&delayed_bond_dump_timer, 3);
    wiced_init_timer(&hf_autoreconnect_timer, hf_autoreconnect_timer_cb, 0, WICED_SECONDS_TIMER);
    hf_start_autoreconnect("boot", 5);

    WICED_BT_TRACE("Boot auto-reconnect (%s role) will target the last bonded peer when available\n",
                   hf_autoreconnect_role_name());

    return WICED_BT_SUCCESS;
}
