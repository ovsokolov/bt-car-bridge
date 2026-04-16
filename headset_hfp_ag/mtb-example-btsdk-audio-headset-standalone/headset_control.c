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
 * Headset Sample Application for the Audio Shield platform.
 *
 * The sample app demonstrates Bluetooth A2DP sink, HFP and AVRCP Controller (and Target for absolute volume control).
 *
 * Features demonstrated
 *  - A2DP Sink and AVRCP Controller (Target for absolute volume)
 *  - Handsfree Device
 *  - GATT
 *  - SDP and GATT descriptor/attribute configuration
 *  - This app is targeted for the Audio Shield platform
 *  - This App doesn't support HCI UART for logging, PUART is supported.
 *  - HCI Client Control is not supported.
 *
 * Setting up Connection
 * 1. press and hold the SW15 on EVAL board for at least 2 seconds.
 * 2. This will set device in discovery mode(A2DP, HFP, and LE) and LED will start blinking.
 * 3. Scan for 'headsetpro' device on the peer source device, and pair with the headsetpro.
 * 4. Once connected LED will stop blinking and turns on.
 * 5. If no connection is established within 30sec,LED will turn off and device is not be discoverable,repeat instructions from step 1 to start again.
 *
 * A2DP Play back
 * 1. Start music play back from peer device, you should be able to hear music from headphones(use J27 headphone jack on Audio board)
 * 2. You can control play back and volume from peer device (Play, Pause, Stop) controls.
 *
 * AVRCP
 * 1. We can use buttons connected to the EVAL board for AVRCP control
 * 2. SW15 - Discoverable/Play/Pause    - Long press this button to enter discoverable mode. Click the button to Play/Pause the music play back.
 * 3. SW16 -                            - No function
 * 4. SW17 - Volume Up/Forward          - Click this button to increase volume or long press the button to forward
 * 5. SW18 - Volume Down/Backward       - Click this button to decrease volume or long press the button to backward
 *                                      (There are 16 volume steps).
 * 6. SW19 - Voice Recognition          - Long press to voice control
 *
 * Hands-free
 * 1. Make a phone call to the peer device.
 * 2. In case of in-band ring mode is supported from peer device, you will hear the set ring tone
 * 3. In case of out-of-band ring tone, no tone will be heard on headset.
 * 4. SW15  is used as multi-function button to accept,hang-up or reject call.
 * 5. Long press SW15 to reject the incoming call.
 * 6. Click SW15 to accept the call or hang-up the active call.
 * 7. If the call is on hold click SW15 to hang-up the call.
 * 8. Every click of SW17(Volume Up) button will increase the volume
 * 9. Every click of SW18(Volume down) button will decrease the volume
 *
 * LE
 *  - To connect a Bluetooth LE device: set Bluetooth headset in discovery mode by long press of SW15 button
 *    search for 'headsetpro' device in peer side phone app (Ex:BLEScanner for Android and LightBlue for iOS) and connect.
 *  - From the peer side app you should be able to do GATT read/write of the elements listed.
 */
#include <bt_hs_spk_handsfree.h>
#include <wiced_hal_puart.h>
#include "headset_control.h"
#include "headset_control_le.h"
#include "wiced_bt_gatt.h"
#include "wiced_bt_ble.h"
#include <wiced_bt_stack.h>
#include "wiced_app_cfg.h"
#include "wiced_memory.h"
#include "wiced_bt_sdp.h"
#include "wiced_bt_dev.h"
#include "bt_hs_spk_control.h"
#include "wiced_platform.h"
#include "wiced_app.h"
#include "wiced_bt_a2dp_sink.h"
#if BTSTACK_VER >= 0x03000001
#include "wiced_audio_sink_route_config.h"
#endif
#ifndef PLATFORM_LED_DISABLED
#include "wiced_led_manager.h"
#endif // !PLATFORM_LED_DISABLED
#include "bt_hs_spk_button.h"
#include "wiced_audio_manager.h"
#if defined(CYW20706A2)
#include "bt_hs_spk_audio.h"
#include "wiced_hal_cpu_clk.h"
#endif // defined(CYW20706A2)
#include "wiced_hal_gpio.h"
#include "hci_control_api.h"
#include "headset_nvram.h"
#include "wiced_rtos.h"
#include "wiced_transport.h"
#ifdef FASTPAIR_ENABLE
#include "wiced_bt_gfps.h"
#endif
#ifdef AUTO_ELNA_SWITCH
#include "cycfg_pins.h"
#include "wiced_hal_rfm.h"
#ifndef TX_PU
#define TX_PU   CTX
#endif
#ifndef RX_PU
#define RX_PU   CRX
#endif
#endif

/*****************************************************************************
**  Constants
*****************************************************************************/
#define HEADSET_CONTROL_MIC_DATA_BUFFER_LEN 1024    // bytes

/*****************************************************************************
**  Structures
*****************************************************************************/

/******************************************************
 *               Function Declarations
 ******************************************************/
static wiced_result_t btheadset_control_management_callback(wiced_bt_management_evt_t event,
                                                            wiced_bt_management_evt_data_t *p_event_data);

static void headset_control_proc_rx_cmd(uint16_t op_code, uint8_t *p_data, uint32_t data_len);
#if defined(CYW20706A2)
// 20706A2 does not support wiced_platform_transport_init; init in application itself
static void hci_control_transport_status(wiced_transport_type_t type);
static uint32_t hci_control_proc_rx_cmd(uint8_t *p_data, uint32_t length);
static void headset_control_a2dp_sink_event_post_handler(wiced_bt_a2dp_sink_event_t event, wiced_bt_a2dp_sink_event_data_t* p_data);
#endif

static void headset_control_mic_data_add(uint8_t *p_data, uint16_t len);
static wiced_bool_t headset_control_mic_data_add_callback(uint8_t *p_data, uint32_t len);
static void headset_control_mic_data_reset(void);

/******************************************************
 *               Variables Definitions
 ******************************************************/
extern wiced_bt_a2dp_config_data_t bt_audio_config;
extern uint8_t                     bt_avrc_ct_supported_events[];
extern void wiced_audio_sink_set_hci_event_audio_data_extra_header(uint8_t enabled);

#if defined (CYW20706A2)
const wiced_transport_cfg_t transport_cfg =
{
    .type = WICED_TRANSPORT_UART,
    .cfg  =
    {
        .uart_cfg              =
        {
            .mode      = WICED_TRANSPORT_UART_HCI_MODE,
            .baud_rate = HCI_UART_DEFAULT_BAUD
        },
    },
#if BTSTACK_VER >= 0x03000001
    .heap_config               =
    {
        .data_heap_size        = 1024 * 4 + 1500 * 2,
        .hci_trace_heap_size   = 1024 * 2,
        .debug_trace_heap_size = 1024,
    },
#else
    .rx_buff_pool_cfg          =
    {
        .buffer_size  = 0,
        .buffer_count = 0
    },
#endif /* if BTSTACK_VER >= 0x03000001 */

#ifdef HCI_TRACE_OVER_TRANSPORT
    .p_status_handler    = hci_control_transport_status,
    .p_data_handler      = hci_control_proc_rx_cmd,
    .p_tx_complete_cback = NULL
#else
    .p_status_handler    = NULL,
    .p_data_handler      = NULL,
    .p_tx_complete_cback = NULL
#endif // HCI_TRACE_OVER_TRANSPORT
};
#endif // CYW20706A2

#if BTSTACK_VER >= 0x03000001
#define BT_STACK_HEAP_SIZE          1024 * 7
wiced_bt_heap_t *p_default_heap = NULL;
#endif

extern const uint8_t btheadset_sdp_db[];

#ifndef PLATFORM_LED_DISABLED
/*LED config for app status indication */
static wiced_led_config_t led_config =
{
    .led    = PLATFORM_LED_1,
    .bright = 50,
};
#endif

/* Local Identify Resolving Key. */
typedef struct
{
    wiced_bt_local_identity_keys_t local_irk;
    wiced_result_t                 result;
} headset_control_local_irk_info_t;

static headset_control_local_irk_info_t local_irk_info = { 0 };

struct headset_control_mic_data_info_t
{
    wiced_mutex_t *p_mutex;
    uint8_t        buffer[HEADSET_CONTROL_MIC_DATA_BUFFER_LEN];
    uint32_t       data_len;
    uint32_t       index_start;
    uint32_t       index_end;
} headset_control_mic_data = { 0 };

/******************************************************
 *               Function Definitions
 ******************************************************/

/*
 * Restore local Identity Resolving Key
 */
static void headset_control_local_irk_restore(void)
{
    uint16_t nb_bytes;

    nb_bytes = wiced_hal_read_nvram(HEADSET_NVRAM_ID_LOCAL_IRK,
                                    BTM_SECURITY_LOCAL_KEY_DATA_LEN,
                                    (uint8_t *)&local_irk_info.local_irk,
                                    &local_irk_info.result);

    WICED_BT_TRACE("headset_control_local_irk_restore (result: %d, nb_bytes: %d)\n",
                   local_irk_info.result,
                   nb_bytes);
}

/*
 * Update local Identity Resolving Key
 */
static void headset_control_local_irk_update(uint8_t *p_key)
{
    uint16_t       nb_bytes;
    wiced_result_t result;

    /* Check if the IRK shall be updated. */
    if (memcmp((void *)p_key,
               (void *)&local_irk_info.local_irk,
               BTM_SECURITY_LOCAL_KEY_DATA_LEN) != 0)
    {
        nb_bytes = wiced_hal_write_nvram(HEADSET_NVRAM_ID_LOCAL_IRK,
                                         BTM_SECURITY_LOCAL_KEY_DATA_LEN,
                                         p_key,
                                         &result);

        WICED_BT_TRACE("Update local IRK (result: %d, nb_bytes: %d)\n",
                       result,
                       nb_bytes);

        if ((nb_bytes == BTM_SECURITY_LOCAL_KEY_DATA_LEN) &&
            (result == WICED_BT_SUCCESS))
        {
            memcpy((void *)&local_irk_info.local_irk,
                   (void *)p_key,
                   BTM_SECURITY_LOCAL_KEY_DATA_LEN);

            local_irk_info.result = result;
        }
    }
}

/*
 *  btheadset_control_init
 *  Does Bluetooth stack and audio buffer init
 */
void btheadset_control_init(void)
{
#ifndef CYW20706A2
    wiced_platform_transport_init(&headset_control_proc_rx_cmd);
#else //CYW20706A2
    wiced_transport_init(&transport_cfg);
#endif

#ifdef WICED_BT_TRACE_ENABLE
    // Set the debug uart as WICED_ROUTE_DEBUG_NONE to get rid of prints
    // wiced_set_debug_uart(WICED_ROUTE_DEBUG_NONE);

#ifdef NO_PUART_SUPPORT
    wiced_set_debug_uart(WICED_ROUTE_DEBUG_TO_WICED_UART);
#else // NO_PUART_SUPPORT
#if defined(CYW20706A2)
    wiced_set_debug_uart_baudrate(3000000);
    wiced_set_debug_uart(WICED_ROUTE_DEBUG_TO_PUART);
    wiced_hal_puart_select_uart_pads(WICED_PUART_RXD, WICED_PUART_TXD, 0, 0);
#else
    // Set to PUART to see traces on peripheral uart(puart)
    wiced_hal_puart_init();
    wiced_hal_puart_configuration(3000000, PARITY_NONE, STOP_BIT_2);
#endif
    wiced_set_debug_uart(WICED_ROUTE_DEBUG_TO_PUART);
#endif // NO_PUART_SUPPORT

    // Set to HCI to see traces on HCI uart - default if no call to wiced_set_debug_uart()
    // wiced_set_debug_uart( WICED_ROUTE_DEBUG_TO_HCI_UART );

    // Use WICED_ROUTE_DEBUG_TO_WICED_UART to send formatted debug strings over the WICED
    // HCI debug interface to be parsed by ClientControl/BtSpy.
    // Note: WICED HCI must be configured to use this - see wiced_trasnport_init(), must
    // be called with wiced_transport_cfg_t.wiced_tranport_data_handler_t callback present
    // wiced_set_debug_uart(WICED_ROUTE_DEBUG_TO_WICED_UART);
#endif /* ifdef WICED_BT_TRACE_ENABLE */

    WICED_BT_TRACE("#########################\n");
    WICED_BT_TRACE("# headset_standalone APP START #\n");
    WICED_BT_TRACE("#########################\n");

#if defined(CYW20721B2) || defined(CYW20706A2)
    /* Disable secure connection because connection will drop when connecting with Win10 first time */
    wiced_bt_dev_lrac_disable_secure_connection();
#endif
}

#ifdef HCI_TRACE_OVER_TRANSPORT
/*
 *  Process all HCI packet received from stack
 */
void hci_control_hci_packet_cback(wiced_bt_hci_trace_type_t type, uint16_t length, uint8_t *p_data)
{
#if (WICED_HCI_TRANSPORT == WICED_HCI_TRANSPORT_UART)
    // send the trace
#if BTSTACK_VER >= 0x03000001
    wiced_transport_send_hci_trace(type, p_data, length);
#else
    wiced_transport_send_hci_trace(NULL, type, length, p_data);
#endif
#endif
}

#endif // HCI_TRACE_OVER_TRANSPORT

/*
 * btheadset_post_bt_init
 */
wiced_result_t btheadset_post_bt_init(void)
{
    wiced_bool_t               ret    = WICED_FALSE;
    bt_hs_spk_control_config_t config = { 0 };
    bt_hs_spk_eir_config_t     eir    = { 0 };

    eir.p_dev_name = (char *)wiced_bt_cfg_settings.device_name;
    eir.default_uuid_included = WICED_TRUE;

    if (WICED_SUCCESS != bt_hs_spk_write_eir(&eir))
    {
        WICED_BT_TRACE("Write EIR Failed\n");
    }

    ret = wiced_bt_sdp_db_init((uint8_t *)btheadset_sdp_db, wiced_app_cfg_sdp_record_get_size());
    if (ret != TRUE)
    {
        WICED_BT_TRACE("%s Failed to Initialize SDP databse\n", __FUNCTION__);
        return WICED_BT_ERROR;
    }

    config.conn_status_change_cb = NULL;
#ifdef LOW_POWER_MEASURE_MODE
    config.discoverable_timeout = 60;               /* 60 Sec */
#else
    config.discoverable_timeout = 240;              /* 240 Sec */
#endif
    config.acl3mbpsPacketSupport            = WICED_TRUE;
    config.audio.a2dp.p_audio_config        = &bt_audio_config;
    config.audio.a2dp.p_pre_handler         = NULL;
#if defined(CYW20706A2)
    config.audio.a2dp.post_handler          = &headset_control_a2dp_sink_event_post_handler;
#else
    config.audio.a2dp.post_handler          = NULL;
#endif
    config.audio.avrc_ct.p_supported_events = bt_avrc_ct_supported_events;
    config.hfp.rfcomm.buffer_size           = 700;
    config.hfp.rfcomm.buffer_count          = 4;
#if (WICED_BT_HFP_HF_WBS_INCLUDED == TRUE)
    config.hfp.feature_mask = WICED_BT_HFP_HF_FEATURE_3WAY_CALLING | \
                              WICED_BT_HFP_HF_FEATURE_CLIP_CAPABILITY | \
                              WICED_BT_HFP_HF_FEATURE_REMOTE_VOLUME_CONTROL| \
                              WICED_BT_HFP_HF_FEATURE_HF_INDICATORS | \
                              WICED_BT_HFP_HF_FEATURE_CODEC_NEGOTIATION | \
                              WICED_BT_HFP_HF_FEATURE_VOICE_RECOGNITION_ACTIVATION | \
                              WICED_BT_HFP_HF_FEATURE_ESCO_S4_SETTINGS_SUPPORT;
#else
    config.hfp.feature_mask = WICED_BT_HFP_HF_FEATURE_3WAY_CALLING | \
                              WICED_BT_HFP_HF_FEATURE_CLIP_CAPABILITY | \
                              WICED_BT_HFP_HF_FEATURE_REMOTE_VOLUME_CONTROL| \
                              WICED_BT_HFP_HF_FEATURE_HF_INDICATORS | \
                              WICED_BT_HFP_HF_FEATURE_VOICE_RECOGNITION_ACTIVATION | \
                              WICED_BT_HFP_HF_FEATURE_ESCO_S4_SETTINGS_SUPPORT;
#endif /* if (WICED_BT_HFP_HF_WBS_INCLUDED == TRUE) */

#if !(defined(CYW20706A2))
    config.sleep_config.enable               = WICED_TRUE;
    config.sleep_config.sleep_mode           = WICED_SLEEP_MODE_NO_TRANSPORT;
    config.sleep_config.host_wake_mode       = WICED_SLEEP_WAKE_ACTIVE_HIGH;
    config.sleep_config.device_wake_mode     = WICED_SLEEP_WAKE_ACTIVE_LOW;
    config.sleep_config.device_wake_source   = WICED_SLEEP_WAKE_SOURCE_GPIO;
    config.sleep_config.device_wake_gpio_num = WICED_P02;
#endif

    config.nvram.link_key.id         = HEADSET_NVRAM_ID_LINK_KEYS;
    config.nvram.link_key.p_callback = NULL;

    if (WICED_SUCCESS != bt_hs_spk_post_stack_init(&config))
    {
        WICED_BT_TRACE("bt_audio_post_stack_init failed\n");
        return WICED_BT_ERROR;
    }

    /*Set audio sink*/
    bt_hs_spk_set_audio_sink(AM_UART);

#if (WICED_APP_LE_INCLUDED == TRUE)
    hci_control_le_enable();
#endif

    /* Register the MIC data add callback. */
    bt_hs_spk_handsfree_sco_mic_data_add_callback_register(&headset_control_mic_data_add_callback);

    /* Create mutex for MIC data control. */
    headset_control_mic_data.p_mutex = wiced_rtos_create_mutex();

    if (!headset_control_mic_data.p_mutex)
    {
        WICED_BT_TRACE("Err: fail to create mutex for MIC data control\n");
        return WICED_BT_ERROR;
    }

    /* Initialize the mutex used for MIC data control. */
    if (wiced_rtos_init_mutex(headset_control_mic_data.p_mutex) != WICED_BT_SUCCESS)
    {
        WICED_BT_TRACE("Err: fail to init. mutex for MIC data control\n");
        return WICED_BT_ERROR;
    }

#if (!CYW20706A2)
    // 20706A2 does not support channel assessment
    /*we will use the channel map provided by the phone*/
    ret = wiced_bt_dev_set_afh_channel_assessment(WICED_FALSE);
    WICED_BT_TRACE("wiced_bt_dev_set_afh_channel_assessment status:%d\n", ret);
    if (ret != WICED_BT_SUCCESS)
    {
        return WICED_BT_ERROR;
    }
#endif
#if (!CYW20706A2)
    // audio uart transport has been included in wiced_audio_sink.a for 20706A2
    wiced_audio_sink_set_hci_event_audio_data_extra_header(1);
#endif

#ifdef AUTO_ELNA_SWITCH
    wiced_hal_rfm_auto_elna_enable(1, RX_PU);
#endif
#ifdef AUTO_EPA_SWITCH
    wiced_hal_rfm_auto_epa_enable(1, TX_PU);
#endif

    return WICED_SUCCESS;
}

/*
 *  Management callback receives various notifications from the stack
 */
wiced_result_t btheadset_control_management_callback(wiced_bt_management_evt_t event, wiced_bt_management_evt_data_t *p_event_data)
{
    wiced_result_t                    result = WICED_BT_SUCCESS;
    wiced_bt_dev_status_t             dev_status;
    wiced_bt_dev_ble_pairing_info_t  *p_pairing_info;
    wiced_bt_dev_encryption_status_t *p_encryption_status;
    int bytes_written, bytes_read;
    int nvram_id;
    wiced_bt_dev_pairing_cplt_t *p_pairing_cmpl;
    uint8_t pairing_result;

#if (WICED_HCI_TRANSPORT == WICED_HCI_TRANSPORT_UART)
    WICED_BT_TRACE("btheadset bluetooth management callback event: %d\n", event);
#endif

    switch (event)
    {
    /* Bluetooth  stack enabled */
    case BTM_ENABLED_EVT:
        if (p_event_data->enabled.status != WICED_BT_SUCCESS)
        {
            WICED_BT_TRACE("arrived with failure\n");
        }
        else
        {
            btheadset_post_bt_init();

#ifdef HCI_TRACE_OVER_TRANSPORT
            // Disable while streaming audio over the uart.
            wiced_bt_dev_register_hci_trace(hci_control_hci_packet_cback);
#endif

            if (WICED_SUCCESS != btheadset_init_button_interface())
            {
                WICED_BT_TRACE("btheadset button init failed\n");
            }

#ifndef PLATFORM_LED_DISABLED
            if (WICED_SUCCESS != wiced_led_manager_init(&led_config))
            {
                WICED_BT_TRACE("btheadset LED init failed\n");
            }
#endif

            WICED_BT_TRACE("Free RAM sizes: %d\n", wiced_memory_get_free_bytes());
        }
        break;

    case BTM_DISABLED_EVT:
        //hci_control_send_device_error_evt( p_event_data->disabled.reason, 0 );
        break;

    case BTM_PIN_REQUEST_EVT:
        WICED_BT_TRACE("remote address= %B\n", p_event_data->pin_request.bd_addr);
        //wiced_bt_dev_pin_code_reply(*p_event_data->pin_request.bd_addr, WICED_BT_SUCCESS, WICED_PIN_CODE_LEN, (uint8_t *)&pincode[0]);
        break;

    case BTM_USER_CONFIRMATION_REQUEST_EVT:
        // If this is just works pairing, accept. Otherwise send event to the MCU to confirm the same value.
        WICED_BT_TRACE("BTM_USER_CONFIRMATION_REQUEST_EVT BDA %B\n", p_event_data->user_confirmation_request.bd_addr);
        if (p_event_data->user_confirmation_request.just_works)
        {
            WICED_BT_TRACE("just_works \n");
            wiced_bt_dev_confirm_req_reply(WICED_BT_SUCCESS, p_event_data->user_confirmation_request.bd_addr);
        }
        else
        {
            WICED_BT_TRACE("Need to send user_confirmation_request, Key %d \n", p_event_data->user_confirmation_request.numeric_value);
#ifdef FASTPAIR_ENABLE
            wiced_bt_gfps_provider_seeker_passkey_set(p_event_data->user_confirmation_request.numeric_value);
#endif
            wiced_bt_dev_confirm_req_reply(WICED_BT_SUCCESS, p_event_data->user_confirmation_request.bd_addr);
        }
        break;

    case BTM_PASSKEY_NOTIFICATION_EVT:
        WICED_BT_TRACE("PassKey Notification. BDA %B, Key %d \n", p_event_data->user_passkey_notification.bd_addr, p_event_data->user_passkey_notification.passkey);
        //hci_control_send_user_confirmation_request_evt(p_event_data->user_passkey_notification.bd_addr, p_event_data->user_passkey_notification.passkey );
        break;

    case BTM_PAIRING_IO_CAPABILITIES_BR_EDR_REQUEST_EVT:
        /* Use the default security for BR/EDR*/
        WICED_BT_TRACE("BTM_PAIRING_IO_CAPABILITIES_BR_EDR_REQUEST_EVT (%B)\n",
                       p_event_data->pairing_io_capabilities_br_edr_request.bd_addr);

#ifdef FASTPAIR_ENABLE
        if (wiced_bt_gfps_provider_pairing_state_get())
        {       // Google Fast Pair service Seeker triggers this pairing process.
                /* Set local capability to Display/YesNo to identify local device is not a
                 * man-in-middle device.
                 * Otherwise, the Google Fast Pair Service Seeker will terminate this pairing
                 * process. */
            p_event_data->pairing_io_capabilities_br_edr_request.local_io_cap = BTM_IO_CAPABILITIES_DISPLAY_AND_YES_NO_INPUT;
        }
        else
#endif
        {
            p_event_data->pairing_io_capabilities_br_edr_request.local_io_cap = BTM_IO_CAPABILITIES_NONE;
        }

        p_event_data->pairing_io_capabilities_br_edr_request.auth_req = BTM_AUTH_SINGLE_PROFILE_GENERAL_BONDING_NO;
        p_event_data->pairing_io_capabilities_br_edr_request.oob_data = WICED_FALSE;
//            p_event_data->pairing_io_capabilities_br_edr_request.auth_req     = BTM_AUTH_ALL_PROFILES_NO;
        break;

    case BTM_PAIRING_IO_CAPABILITIES_BR_EDR_RESPONSE_EVT:
        WICED_BT_TRACE("BTM_PAIRING_IO_CAPABILITIES_BR_EDR_RESPONSE_EVT (%B, io_cap: 0x%02X) \n",
                       p_event_data->pairing_io_capabilities_br_edr_response.bd_addr,
                       p_event_data->pairing_io_capabilities_br_edr_response.io_cap);

#ifdef FASTPAIR_ENABLE
        if (wiced_bt_gfps_provider_pairing_state_get())
        {       // Google Fast Pair service Seeker triggers this pairing process.
                /* If the device capability is set to NoInput/NoOutput, end pairing, to avoid using
                 * Just Works pairing method. todo*/
            if (p_event_data->pairing_io_capabilities_br_edr_response.io_cap == BTM_IO_CAPABILITIES_NONE)
            {
                WICED_BT_TRACE("Terminate the pairing process\n");
            }
        }
#endif
        break;

    case BTM_PAIRING_IO_CAPABILITIES_BLE_REQUEST_EVT:
        /* Use the default security for LE */
        WICED_BT_TRACE("BTM_PAIRING_IO_CAPABILITIES_BLE_REQUEST_EVT bda %B\n",
                       p_event_data->pairing_io_capabilities_ble_request.bd_addr);

        p_event_data->pairing_io_capabilities_ble_request.local_io_cap = BTM_IO_CAPABILITIES_NONE;
        p_event_data->pairing_io_capabilities_ble_request.oob_data     = BTM_OOB_NONE;
        p_event_data->pairing_io_capabilities_ble_request.auth_req     = BTM_LE_AUTH_REQ_SC_MITM_BOND;
        p_event_data->pairing_io_capabilities_ble_request.max_key_size = 16;
        p_event_data->pairing_io_capabilities_ble_request.init_keys    = BTM_LE_KEY_PENC|BTM_LE_KEY_PID|BTM_LE_KEY_PCSRK|BTM_LE_KEY_LENC;
        p_event_data->pairing_io_capabilities_ble_request.resp_keys    = BTM_LE_KEY_PENC|BTM_LE_KEY_PID|BTM_LE_KEY_PCSRK|BTM_LE_KEY_LENC;
        break;

    case BTM_PAIRING_COMPLETE_EVT:
        p_pairing_cmpl = &p_event_data->pairing_complete;
        if (p_pairing_cmpl->transport == BT_TRANSPORT_BR_EDR)
        {
            pairing_result = p_pairing_cmpl->pairing_complete_info.br_edr.status;
            WICED_BT_TRACE("BREDR Pairing Result: %02x\n", pairing_result);
        }
        else
        {
            pairing_result = p_pairing_cmpl->pairing_complete_info.ble.reason;
            WICED_BT_TRACE("LE Pairing Result: %02x\n", pairing_result);
        }
        //btheadset_control_pairing_completed_evt( pairing_result, p_event_data->pairing_complete.bd_addr );
        break;

    case BTM_ENCRYPTION_STATUS_EVT:
        p_encryption_status = &p_event_data->encryption_status;

        WICED_BT_TRACE("Encryption Status:(%B) res:%d\n", p_encryption_status->bd_addr, p_encryption_status->result);

        bt_hs_spk_control_btm_event_handler_encryption_status(p_encryption_status);

        break;

    case BTM_SECURITY_REQUEST_EVT:
        WICED_BT_TRACE("Security Request Event, Pairing allowed %d\n", hci_control_cb.pairing_allowed);
        if (hci_control_cb.pairing_allowed)
        {
            wiced_bt_ble_security_grant(p_event_data->security_request.bd_addr, WICED_BT_SUCCESS);
        }
        else
        {
            // Pairing not allowed, return error
            result = WICED_BT_ERROR;
        }
        break;

    case BTM_PAIRED_DEVICE_LINK_KEYS_UPDATE_EVT:
        result = bt_hs_spk_control_btm_event_handler_link_key(event, &p_event_data->paired_device_link_keys_update) ? WICED_BT_SUCCESS : WICED_BT_ERROR;
        break;

    case BTM_PAIRED_DEVICE_LINK_KEYS_REQUEST_EVT:
        result = bt_hs_spk_control_btm_event_handler_link_key(event, &p_event_data->paired_device_link_keys_request) ? WICED_BT_SUCCESS : WICED_BT_ERROR;
        break;

    case BTM_LOCAL_IDENTITY_KEYS_UPDATE_EVT:
        WICED_BT_TRACE("BTM_LOCAL_IDENTITY_KEYS_UPDATE_EVT\n");

        headset_control_local_irk_update((uint8_t *)&p_event_data->local_identity_keys_update);
        break;

    case BTM_LOCAL_IDENTITY_KEYS_REQUEST_EVT:
        /*
         * Request to restore local identity keys from NVRAM
         * (requested during Bluetooth start up)
         * */
        WICED_BT_TRACE("BTM_LOCAL_IDENTITY_KEYS_REQUEST_EVT (%d)\n", local_irk_info.result);

        if (local_irk_info.result == WICED_BT_SUCCESS)
        {
            memcpy((void *)&p_event_data->local_identity_keys_request,
                   (void *)&local_irk_info.local_irk,
                   BTM_SECURITY_LOCAL_KEY_DATA_LEN);
        }
        else
        {
            result = WICED_BT_NO_RESOURCES;
        }
        break;

    case BTM_BLE_ADVERT_STATE_CHANGED_EVT:
        WICED_BT_TRACE("BLE_ADVERT_STATE_CHANGED_EVT:%d\n", p_event_data->ble_advert_state_changed);
        break;

    case BTM_POWER_MANAGEMENT_STATUS_EVT:
        bt_hs_spk_control_btm_event_handler_power_management_status(&p_event_data->power_mgmt_notification);
        break;

    case BTM_SCO_CONNECTED_EVT:
    case BTM_SCO_DISCONNECTED_EVT:
    case BTM_SCO_CONNECTION_REQUEST_EVT:
    case BTM_SCO_CONNECTION_CHANGE_EVT:
        hf_sco_management_callback(event, p_event_data);

        if (event == BTM_SCO_DISCONNECTED_EVT)
        {
            headset_control_mic_data_reset();
        }
        break;

    case BTM_BLE_CONNECTION_PARAM_UPDATE:
        WICED_BT_TRACE("BTM_BLE_CONNECTION_PARAM_UPDATE (%B, status: %d, conn_interval: %d, conn_latency: %d, supervision_timeout: %d)\n",
                       p_event_data->ble_connection_param_update.bd_addr,
                       p_event_data->ble_connection_param_update.status,
                       p_event_data->ble_connection_param_update.conn_interval,
                       p_event_data->ble_connection_param_update.conn_latency,
                       p_event_data->ble_connection_param_update.supervision_timeout);
        break;

#if (!CYW20706A2)
    // 20706A2 does not support phy update
    case BTM_BLE_PHY_UPDATE_EVT:
        /* LE PHY Update to 1M or 2M */
        WICED_BT_TRACE("PHY config is updated as TX_PHY : %dM, RX_PHY : %dM\n",
                       p_event_data->ble_phy_update_event.tx_phy,
                       p_event_data->ble_phy_update_event.rx_phy);
        break;

#endif
#ifdef CYW20721B2
    case BTM_BLE_REMOTE_CONNECTION_PARAM_REQ_EVT:
        result = bt_hs_spk_control_btm_event_handler_ble_remote_conn_param_req(
            p_event_data->ble_rc_connection_param_req.bd_addr,
            p_event_data->ble_rc_connection_param_req.min_int,
            p_event_data->ble_rc_connection_param_req.max_int,
            p_event_data->ble_rc_connection_param_req.latency,
            p_event_data->ble_rc_connection_param_req.timeout);
        break;

#endif /* CYW20721B2 */
    default:
        result = WICED_BT_USE_DEFAULT_SECURITY;
        break;
    }
    return result;
}

/*
 * headset_control_start
 *
 * Start the application.
 */
static void headset_control_start(uint8_t *p_data, uint32_t data_len)
{
    wiced_result_t ret = WICED_BT_ERROR;

    /* Check parameter.*/
    if (data_len != 0)
    {
        return;
    }

#if BTSTACK_VER >= 0x03000001
    /* Create default heap */
    p_default_heap = wiced_bt_create_heap("default_heap", NULL, BT_STACK_HEAP_SIZE, NULL,
                                          WICED_TRUE);
    if (p_default_heap == NULL)
    {
        WICED_BT_TRACE("create default heap error: size %d\n", BT_STACK_HEAP_SIZE);
        return;
    }
#endif

    /* Enable Bluetooth stack */
#if BTSTACK_VER >= 0x03000001
    ret = wiced_bt_stack_init(btheadset_control_management_callback, &wiced_bt_cfg_settings);
#else
    ret = wiced_bt_stack_init(btheadset_control_management_callback, &wiced_bt_cfg_settings, wiced_app_cfg_buf_pools);
#endif
    if (ret != WICED_BT_SUCCESS)
    {
        WICED_BT_TRACE("wiced_bt_stack_init returns error: %d\n", ret);
        return;
    }

    /* Configure Audio buffer */
    ret = wiced_audio_buffer_initialize(wiced_bt_audio_buf_config);
    if (ret != WICED_BT_SUCCESS)
    {
        WICED_BT_TRACE("wiced_audio_buffer_initialize returns error: %d\n", ret);
        return;
    }

    /* Restore local Identify Resolving Key (IRK) for LE Private Resolvable Address. */
    headset_control_local_irk_restore();
}

/*
 * headset_control_proc_rx_cmd_button
 *
 * Handle the received button event.
 *
 * The format of incoming button event:
 * Byte: |     0     |       1      |      2       |
 * Data: | BUTTON_ID | BUTTON_EVENT | BUTTON_STATE |
 *
 */
static void headset_control_proc_rx_cmd_button(uint8_t *p_data, uint32_t length)
{
    uint8_t button_id;
    uint8_t button_event;
    uint8_t button_state;

    /* Check data length. */
    if (length != sizeof(button_id) + sizeof(button_event) + sizeof(button_state))
    {
        return;
    }

    STREAM_TO_UINT8(button_id, p_data);
    STREAM_TO_UINT8(button_event, p_data);
    STREAM_TO_UINT8(button_state, p_data);

    /* Process this button event. */
    bt_hs_spk_button_event_emulator((platform_button_t)button_id,
                                    (button_manager_event_t)button_event,
                                    (button_manager_button_state_t)button_state,
                                    0);
}

/*
 * Handle received command over UART. Please refer to the WICED Smart Ready
 * Software User Manual (WICED-Smart-Ready-SWUM100-R) for details on the
 * HCI UART control protocol.
 */
static void headset_control_proc_rx_cmd(uint16_t op_code, uint8_t *p_data, uint32_t data_len)
{
    /* Check parameter. */
    if (p_data == NULL)
    {
        return;
    }

    /* Process the incoming command. */
    switch (op_code)
    {
    case HCI_CONTROL_HCI_AUDIO_COMMAND_MIC_DATA:
        headset_control_mic_data_add(p_data, data_len);
        break;

    case HCI_CONTROL_HCI_AUDIO_COMMAND_BT_START:
        headset_control_start(p_data, data_len);
        break;

    case HCI_CONTROL_HCI_AUDIO_COMMAND_BUTTON:
        headset_control_proc_rx_cmd_button(p_data, data_len);
        break;

    default:
        break;
    }
}

#ifdef CYW20706A2
/*
 * hci_control_proc_rx_cmd
 */
static uint32_t hci_control_proc_rx_cmd(uint8_t *p_buffer, uint32_t length)
{
    uint16_t opcode;
    uint16_t payload_len;
    uint8_t *p_data = p_buffer;

    /* Check parameter. */
    if (p_buffer == NULL)
    {
        return HCI_CONTROL_STATUS_INVALID_ARGS;
    }

    // Expected minimum 4 byte as the wiced header
    if (length < (sizeof(opcode) + sizeof(payload_len)))
    {
        wiced_transport_free_buffer(p_buffer);
        return HCI_CONTROL_STATUS_INVALID_ARGS;
    }

    STREAM_TO_UINT16(opcode, p_data);       // Get OpCode
    STREAM_TO_UINT16(payload_len, p_data);  // Gen Payload Length

    headset_control_proc_rx_cmd(opcode, p_data, payload_len);

    // Freeing the buffer in which data is received
    wiced_transport_free_buffer(p_buffer);

    return HCI_CONTROL_STATUS_SUCCESS;
}

/*
 * hci_control_transport_status
 */
static void hci_control_transport_status(wiced_transport_type_t type)
{
    wiced_transport_send_data(HCI_CONTROL_EVENT_DEVICE_STARTED, NULL, 0);
}

#endif // CYW20706A2


/*
 * headset_control_mic_data_reset
 */
static void headset_control_mic_data_reset(void)
{
    memset((void *)headset_control_mic_data.buffer,
           0,
           HEADSET_CONTROL_MIC_DATA_BUFFER_LEN);

    headset_control_mic_data.data_len    = 0;
    headset_control_mic_data.index_start = 0;
    headset_control_mic_data.index_end   = 0;
}

/*
 * headset_control_mic_data_add
 */
static void headset_control_mic_data_add(uint8_t *p_data, uint16_t len)
{
    uint32_t data_to_be_fill = 0;

    /* Lock. */
    wiced_rtos_lock_mutex(headset_control_mic_data.p_mutex);

    /* Check available buffer length. */
    if (headset_control_mic_data.data_len == HEADSET_CONTROL_MIC_DATA_BUFFER_LEN)
    {
        /* Unlock */
        wiced_rtos_unlock_mutex(headset_control_mic_data.p_mutex);
        return;
    }

    /* Count total data to be filled. */
    if (len <= (HEADSET_CONTROL_MIC_DATA_BUFFER_LEN - headset_control_mic_data.data_len))
    {
        data_to_be_fill = len;
    }
    else
    {
        data_to_be_fill = HEADSET_CONTROL_MIC_DATA_BUFFER_LEN - headset_control_mic_data.data_len;
    }

    /* Fill data to buffer. */
    if (HEADSET_CONTROL_MIC_DATA_BUFFER_LEN - headset_control_mic_data.index_end >= data_to_be_fill)
    {
        memcpy((void *)&headset_control_mic_data.buffer[headset_control_mic_data.index_end],
               (void *)p_data,
               data_to_be_fill);
    }
    else
    {
        memcpy((void *)&headset_control_mic_data.buffer[headset_control_mic_data.index_end],
               (void *)p_data,
               HEADSET_CONTROL_MIC_DATA_BUFFER_LEN - headset_control_mic_data.index_end);

        memcpy((void *)&headset_control_mic_data.buffer[0],
               (void *)&p_data[HEADSET_CONTROL_MIC_DATA_BUFFER_LEN - headset_control_mic_data.index_end],
               data_to_be_fill - (HEADSET_CONTROL_MIC_DATA_BUFFER_LEN - headset_control_mic_data.index_end));
    }

    /* Update information. */
    headset_control_mic_data.data_len += data_to_be_fill;

    headset_control_mic_data.index_end += data_to_be_fill;
    if (headset_control_mic_data.index_end >= HEADSET_CONTROL_MIC_DATA_BUFFER_LEN)
    {
        headset_control_mic_data.index_end -= HEADSET_CONTROL_MIC_DATA_BUFFER_LEN;
    }

    wiced_rtos_unlock_mutex(headset_control_mic_data.p_mutex);
}

/*
 * headset_control_mic_data_add_callback
 *
 * User callback to add MIC data (PCM data) to the HFP audio stream (forwareded to the AG).
 */
static wiced_bool_t headset_control_mic_data_add_callback(uint8_t *p_data, uint32_t len)
{
    uint32_t data_to_be_fill = 0;

    /* Lock. */
    wiced_rtos_lock_mutex(headset_control_mic_data.p_mutex);

    /* Check available data length. */
    if (headset_control_mic_data.data_len == 0)
    {
        /* Unlock */
        wiced_rtos_unlock_mutex(headset_control_mic_data.p_mutex);
        return WICED_FALSE;
    }

    /* Count total data to be filled. */
    if (headset_control_mic_data.data_len >= len)
    {
        data_to_be_fill = len;
    }
    else
    {
        data_to_be_fill = headset_control_mic_data.data_len;
    }

    /* Fill data. */
    if (HEADSET_CONTROL_MIC_DATA_BUFFER_LEN - headset_control_mic_data.index_start >= data_to_be_fill)
    {
        memcpy((void *)p_data,
               (void *)&headset_control_mic_data.buffer[headset_control_mic_data.index_start],
               data_to_be_fill);
    }
    else
    {
        memcpy((void *)p_data,
               (void *)&headset_control_mic_data.buffer[headset_control_mic_data.index_start],
               HEADSET_CONTROL_MIC_DATA_BUFFER_LEN - headset_control_mic_data.index_start);

        memcpy((void *)&p_data[HEADSET_CONTROL_MIC_DATA_BUFFER_LEN - headset_control_mic_data.index_start],
               (void *)&headset_control_mic_data.buffer[0],
               data_to_be_fill - (HEADSET_CONTROL_MIC_DATA_BUFFER_LEN - headset_control_mic_data.index_start));
    }

    /* Append 0s if need. */
    if (data_to_be_fill < len)
    {
        memset((void *)&p_data[data_to_be_fill], 0, (len - data_to_be_fill));
    }

    /* Update information. */
    headset_control_mic_data.data_len -= data_to_be_fill;

    headset_control_mic_data.index_start += data_to_be_fill;
    if (headset_control_mic_data.index_start >= HEADSET_CONTROL_MIC_DATA_BUFFER_LEN)
    {
        headset_control_mic_data.index_start -= HEADSET_CONTROL_MIC_DATA_BUFFER_LEN;
    }

    wiced_rtos_unlock_mutex(headset_control_mic_data.p_mutex);

    return WICED_TRUE;
}

#if defined(CYW20706A2)
/*
 * A2DP event post-handler
 */
static void headset_control_a2dp_sink_event_post_handler(wiced_bt_a2dp_sink_event_t event, wiced_bt_a2dp_sink_event_data_t* p_data)
{
    switch (event)
    {
    case WICED_BT_A2DP_SINK_START_IND_EVT:
    case WICED_BT_A2DP_SINK_START_CFM_EVT:
        if (bt_hs_spk_audio_is_a2dp_streaming_started())
        {
            if (!wiced_update_cpu_clock(WICED_TRUE, WICED_CPU_CLK_96MHZ))
            {
                WICED_BT_TRACE("Err: faile to update cpu clk\n");
            }
        }
        break;

    case WICED_BT_A2DP_SINK_SUSPEND_EVT:
        if (!bt_hs_spk_audio_is_a2dp_streaming_started())
        {
            if (!wiced_update_cpu_clock(WICED_FALSE, WICED_CPU_CLK_96MHZ))
            {
                WICED_BT_TRACE("Err: faile to update cpu clk\n");
            }
        }
        break;

    default:
        break;
    }
}
#endif // defined(CYW20706A2)
