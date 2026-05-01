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
 * This file implements Hands-free profile Audio Gateway
 *
 */

#ifdef WICED_APP_HFP_AG_INCLUDED

#include <string.h>

#include "hci_control_api.h"
#include "wiced_bt_trace.h"
#include "wiced_hal_puart.h"
#include "hci_control_hfp_ag.h"
#include "hci_control_rc_target.h"
#include "hci_control.h"

#include "wiced_bt_hfp_ag.h"

#if (BTM_WBS_INCLUDED == TRUE )
#define BT_AUDIO_HFP_SUPPORTED_FEATURES     (HFP_AG_FEAT_VREC | HFP_AG_FEAT_CODEC | HFP_AG_FEAT_ESCO | HFP_AG_FEAT_ECS)
#else
#define BT_AUDIO_HFP_SUPPORTED_FEATURES     (HFP_AG_FEAT_VREC | HFP_AG_FEAT_ESCO | HFP_AG_FEAT_ECS)
#endif

#define AG_BRIDGE_AG_STR_MAX        64U
#define AG_BRIDGE_CIND_STRING_LEN   13U
#define AG_BRIDGE_CAR_CMD_QUEUE_DEPTH 8U
#define AG_BRIDGE_CAR_CMD_ANSWER    1U
#define AG_BRIDGE_CAR_CMD_REJECT    2U
#define AG_BRIDGE_CAR_CMD_HANGUP    3U

/******************************************************
 *               Variables Definitions
 ******************************************************/
hfp_ag_session_cb_t  ag_scb[HCI_CONTROL_AG_NUM_SCB];
static char ag_bridge_caller_id[32];
static char ag_bridge_call_state = '0';
static char ag_bridge_callsetup_state = '0';
static char ag_bridge_callheld_state = '0';
static wiced_bool_t ag_bridge_clcc_pending = WICED_FALSE;
static uint16_t ag_bridge_clcc_handle = 0;
static uint8_t ag_bridge_pending_car_cmd[AG_BRIDGE_CAR_CMD_QUEUE_DEPTH];
static uint8_t ag_bridge_pending_car_cmd_head = 0;
static uint8_t ag_bridge_pending_car_cmd_tail = 0;
static uint8_t ag_bridge_pending_car_cmd_count = 0;

static void hci_control_ag_bridge_log_prefixed_text( const char *prefix, const char *text )
{
    char line[96];
    uint16_t prefix_len;
    uint16_t text_len;
    uint16_t copy_len;

    if ( ( prefix == NULL ) || ( text == NULL ) )
    {
        return;
    }

    prefix_len = (uint16_t)strlen(prefix);
    text_len = (uint16_t)strlen(text);
    if ( prefix_len >= sizeof(line) )
    {
        return;
    }

    copy_len = text_len;
    if ( ( prefix_len + copy_len ) >= sizeof(line) )
    {
        copy_len = (uint16_t)(sizeof(line) - prefix_len - 1U);
    }

    memcpy(line, prefix, prefix_len);
    memcpy(&line[prefix_len], text, copy_len);
    line[prefix_len + copy_len] = '\0';

    hci_control_send_bridge_status_line(line);
}

static char hci_control_ag_bridge_upper_char( char c )
{
    if ( ( c >= 'a' ) && ( c <= 'z' ) )
    {
        return (char)( c - ( 'a' - 'A' ) );
    }

    return c;
}

static wiced_bool_t hci_control_ag_bridge_at_matches( const uint8_t *cmd,
                                                      uint16_t cmd_len,
                                                      const char *text )
{
    uint16_t start = 0;
    uint16_t end = cmd_len;
    uint16_t index;
    uint16_t text_len;

    if ( ( cmd == NULL ) || ( text == NULL ) )
    {
        return WICED_FALSE;
    }

    while ( ( start < end ) &&
            ( ( cmd[start] == ' ' ) || ( cmd[start] == '\t' ) || ( cmd[start] == '\0' ) ) )
    {
        start++;
    }

    while ( ( end > start ) &&
            ( ( cmd[end - 1U] == ' ' ) ||
              ( cmd[end - 1U] == '\t' ) ||
              ( cmd[end - 1U] == '\r' ) ||
              ( cmd[end - 1U] == '\n' ) ||
              ( cmd[end - 1U] == '\0' ) ) )
    {
        end--;
    }

    text_len = (uint16_t)strlen(text);
    if ( ( end - start ) != text_len )
    {
        return WICED_FALSE;
    }

    for ( index = 0; index < text_len; index++ )
    {
        if ( hci_control_ag_bridge_upper_char((char)cmd[start + index]) != text[index] )
        {
            return WICED_FALSE;
        }
    }

    return WICED_TRUE;
}

static void hci_control_ag_bridge_queue_car_cmd( uint8_t cmd )
{
    if ( ag_bridge_pending_car_cmd_count >= AG_BRIDGE_CAR_CMD_QUEUE_DEPTH )
    {
        ag_bridge_pending_car_cmd_tail =
            (uint8_t)( ( ag_bridge_pending_car_cmd_tail + 1U ) % AG_BRIDGE_CAR_CMD_QUEUE_DEPTH );
        ag_bridge_pending_car_cmd_count--;
    }

    ag_bridge_pending_car_cmd[ag_bridge_pending_car_cmd_head] = cmd;
    ag_bridge_pending_car_cmd_head =
        (uint8_t)( ( ag_bridge_pending_car_cmd_head + 1U ) % AG_BRIDGE_CAR_CMD_QUEUE_DEPTH );
    ag_bridge_pending_car_cmd_count++;
}

void hci_control_ag_bridge_send_puart_line( const char *line )
{
    uint16_t index;
    uint16_t line_len;

    if ( line == NULL )
    {
        return;
    }

    line_len = (uint16_t)strlen(line);
    for ( index = 0; index < line_len; index++ )
    {
        wiced_hal_puart_write((uint8_t)line[index]);
    }
    wiced_hal_puart_write('\r');
    wiced_hal_puart_write('\n');

    hci_control_ag_bridge_log_prefixed_text("AG_CMD:TX ", line);
}

static void hci_control_ag_bridge_send_ag_str( hfp_ag_session_cb_t *p_scb, const char *text )
{
    uint8_t payload[2U + AG_BRIDGE_AG_STR_MAX + 1U];
    uint16_t text_len;

    if ( ( p_scb == NULL ) || ( text == NULL ) )
    {
        return;
    }

    text_len = (uint16_t)strlen(text);
    if ( text_len > AG_BRIDGE_AG_STR_MAX )
    {
        text_len = AG_BRIDGE_AG_STR_MAX;
    }

    hci_control_ag_bridge_log_prefixed_text("AG_CALL:STR ", text);

    payload[0] = (uint8_t)p_scb->app_handle;
    payload[1] = (uint8_t)(p_scb->app_handle >> 8);
    memcpy(&payload[2], text, text_len);
    payload[2U + text_len] = '\0';

    hci_control_ag_handle_command(HCI_CONTROL_AG_COMMAND_STR, payload, 2U + text_len);
}

static void hci_control_ag_bridge_set_cind( char call_state,
                                            char callsetup_state,
                                            char callheld_state )
{
    uint8_t cind[] = "0,0,0,1,5,5,0";

    cind[0] = (uint8_t)call_state;
    cind[2] = (uint8_t)callsetup_state;
    cind[4] = (uint8_t)callheld_state;

    hci_control_ag_bridge_log_prefixed_text("AG_CALL:CIND ", (char *)cind);
    hci_control_ag_handle_command(HCI_CONTROL_AG_COMMAND_SET_CIND, cind, AG_BRIDGE_CIND_STRING_LEN);
}

static void hci_control_ag_bridge_send_ciev( hfp_ag_session_cb_t *p_scb,
                                             char indicator_index,
                                             char indicator_value )
{
    char ciev[] = "+CIEV: 1,0";

    ciev[7] = indicator_index;
    ciev[9] = indicator_value;

    hci_control_ag_bridge_send_ag_str(p_scb, ciev);
}

static wiced_bool_t hci_control_ag_bridge_line_matches( const uint8_t *line, uint16_t line_len, const char *text )
{
    uint16_t text_len = (uint16_t)strlen(text);

    return ( ( line_len == text_len ) && ( memcmp(line, text, text_len) == 0 ) ) ? WICED_TRUE : WICED_FALSE;
}

static wiced_bool_t hci_control_ag_bridge_line_starts_with( const uint8_t *line, uint16_t line_len, const char *text )
{
    uint16_t text_len = (uint16_t)strlen(text);

    return ( ( line_len >= text_len ) && ( memcmp(line, text, text_len) == 0 ) ) ? WICED_TRUE : WICED_FALSE;
}

static wiced_bool_t hci_control_ag_bridge_parse_u32( const uint8_t *line,
                                                     uint16_t line_len,
                                                     uint16_t *p_index,
                                                     uint32_t *p_value )
{
    uint32_t value = 0;
    uint16_t index;
    wiced_bool_t seen_digit = WICED_FALSE;

    if ( ( line == NULL ) || ( p_index == NULL ) || ( p_value == NULL ) )
    {
        return WICED_FALSE;
    }

    index = *p_index;
    while ( index < line_len )
    {
        uint8_t c = line[index];

        if ( c == ',' )
        {
            break;
        }

        if ( ( c < '0' ) || ( c > '9' ) )
        {
            return WICED_FALSE;
        }

        seen_digit = WICED_TRUE;
        value = ( value * 10U ) + (uint32_t)( c - '0' );
        index++;
    }

    if ( seen_digit == WICED_FALSE )
    {
        return WICED_FALSE;
    }

    *p_value = value;
    *p_index = index;
    return WICED_TRUE;
}

static wiced_bool_t hci_control_ag_bridge_update_media_attr( const uint8_t *line,
                                                             uint16_t line_len,
                                                             const char *prefix,
                                                             uint8_t attr_id )
{
    uint16_t prefix_len = (uint16_t)strlen(prefix);

    if ( hci_control_ag_bridge_line_starts_with(line, line_len, prefix) == WICED_FALSE )
    {
        return WICED_FALSE;
    }

    hci_control_rc_target_bridge_update_track_attr(attr_id,
                                                   &line[prefix_len],
                                                   (uint16_t)(line_len - prefix_len));
    hci_control_send_bridge_status_line("AG_MEDIA:metadata update");
    return WICED_TRUE;
}

static wiced_bool_t hci_control_ag_bridge_handle_media_line( const uint8_t *line, uint16_t line_len )
{
    uint16_t index;
    uint32_t play_state;
    uint32_t song_len;
    uint32_t song_pos;
    static const char playstatus_prefix[] = "BR1,PLAYSTATUS,";

    if ( hci_control_ag_bridge_update_media_attr(line,
                                                 line_len,
                                                 "BR1,META,TITLE,",
                                                 AVRC_MEDIA_ATTR_ID_TITLE) )
    {
        return WICED_TRUE;
    }

    if ( hci_control_ag_bridge_update_media_attr(line,
                                                 line_len,
                                                 "BR1,META,ARTIST,",
                                                 AVRC_MEDIA_ATTR_ID_ARTIST) )
    {
        return WICED_TRUE;
    }

    if ( hci_control_ag_bridge_update_media_attr(line,
                                                 line_len,
                                                 "BR1,META,ALBUM,",
                                                 AVRC_MEDIA_ATTR_ID_ALBUM) )
    {
        return WICED_TRUE;
    }

    if ( hci_control_ag_bridge_update_media_attr(line,
                                                 line_len,
                                                 "BR1,META,TRACK,",
                                                 AVRC_MEDIA_ATTR_ID_TRACK_NUM) )
    {
        return WICED_TRUE;
    }

    if ( hci_control_ag_bridge_update_media_attr(line,
                                                 line_len,
                                                 "BR1,META,TOTAL,",
                                                 AVRC_MEDIA_ATTR_ID_NUM_TRACKS) )
    {
        return WICED_TRUE;
    }

    if ( hci_control_ag_bridge_update_media_attr(line,
                                                 line_len,
                                                 "BR1,META,GENRE,",
                                                 AVRC_MEDIA_ATTR_ID_GENRE) )
    {
        return WICED_TRUE;
    }

    if ( hci_control_ag_bridge_update_media_attr(line,
                                                 line_len,
                                                 "BR1,META,TIME,",
                                                 AVRC_MEDIA_ATTR_ID_PLAYING_TIME) )
    {
        return WICED_TRUE;
    }

    if ( hci_control_ag_bridge_line_starts_with(line, line_len, playstatus_prefix) == WICED_FALSE )
    {
        return WICED_FALSE;
    }

    index = (uint16_t)(sizeof(playstatus_prefix) - 1U);
    if ( hci_control_ag_bridge_parse_u32(line, line_len, &index, &play_state) == WICED_FALSE )
    {
        return WICED_TRUE;
    }
    if ( ( index >= line_len ) || ( line[index] != ',' ) )
    {
        return WICED_TRUE;
    }
    index++;

    if ( hci_control_ag_bridge_parse_u32(line, line_len, &index, &song_len) == WICED_FALSE )
    {
        return WICED_TRUE;
    }
    if ( ( index >= line_len ) || ( line[index] != ',' ) )
    {
        return WICED_TRUE;
    }
    index++;

    if ( hci_control_ag_bridge_parse_u32(line, line_len, &index, &song_pos) == WICED_FALSE )
    {
        return WICED_TRUE;
    }

    hci_control_rc_target_bridge_update_player_status((uint8_t)play_state, song_len, song_pos);
    hci_control_send_bridge_status_line("AG_MEDIA:playstatus update");
    return WICED_TRUE;
}

static void hci_control_ag_bridge_save_cid( const uint8_t *caller_id, uint16_t caller_id_len )
{
    uint16_t index;
    uint16_t copy_len = 0;

    for ( index = 0; index < caller_id_len; index++ )
    {
        char c = (char)caller_id[index];

        if ( c == ',' )
        {
            break;
        }

        if ( ( ( c >= '0' ) && ( c <= '9' ) ) || ( c == '+' ) || ( c == '*' ) || ( c == '#' ) )
        {
            if ( copy_len < ( sizeof(ag_bridge_caller_id) - 1U ) )
            {
                ag_bridge_caller_id[copy_len++] = c;
            }
        }
    }

    ag_bridge_caller_id[copy_len] = '\0';
}

static hfp_ag_session_cb_t *hci_control_ag_bridge_get_car_scb( void )
{
    hfp_ag_session_cb_t *p_scb = &ag_scb[0];

    if ( p_scb->rfc_conn_handle == 0 )
    {
        hci_control_send_bridge_status_line("AG_CALL:no car HFP link");
        return NULL;
    }

    return p_scb;
}

static hfp_ag_session_cb_t *hci_control_ag_bridge_get_scb_by_handle( uint16_t handle )
{
    uint8_t index;

    for ( index = 0; index < HCI_CONTROL_AG_NUM_SCB; index++ )
    {
        if ( ag_scb[index].app_handle == handle )
        {
            return &ag_scb[index];
        }
    }

    return NULL;
}

static char *hci_control_ag_bridge_append_text( char *p, char *end, const char *text )
{
    while ( ( p < end ) && ( *text != '\0' ) )
    {
        *p++ = *text++;
    }

    return p;
}

static char *hci_control_ag_bridge_append_number( char *p, char *end, const char *number )
{
    while ( ( p < end ) && ( *number != '\0' ) )
    {
        char c = *number++;

        if ( ( ( c >= '0' ) && ( c <= '9' ) ) || ( c == '+' ) || ( c == '*' ) || ( c == '#' ) )
        {
            *p++ = c;
        }
    }

    return p;
}

static void hci_control_ag_bridge_send_clip( hfp_ag_session_cb_t *p_scb )
{
    char clip[56];
    char *p = clip;
    char *end = &clip[sizeof(clip) - 1U];

    if ( ( ag_bridge_caller_id[0] == '\0' ) || ( p_scb->clip_enabled == WICED_FALSE ) )
    {
        hci_control_send_bridge_status_line(( ag_bridge_caller_id[0] == '\0' ) ?
                                            "AG_CALL:CLIP skip no cid" :
                                            "AG_CALL:CLIP skip disabled");
        return;
    }

    p = hci_control_ag_bridge_append_text(p, end, "+CLIP: \"");
    p = hci_control_ag_bridge_append_number(p, end, ag_bridge_caller_id);
    p = hci_control_ag_bridge_append_text(p, end, "\",");
    p = hci_control_ag_bridge_append_text(p, end, ( ag_bridge_caller_id[0] == '+' ) ? "145" : "129");
    *p = '\0';

    hci_control_ag_bridge_send_ag_str(p_scb, clip);
    hci_control_send_bridge_status_line("AG_CALL:CLIP sent");
}

static void hci_control_ag_bridge_set_call_state( hfp_ag_session_cb_t *p_scb,
                                                  char call_state,
                                                  char callsetup_state,
                                                  char callheld_state,
                                                  const char *reason )
{
    if ( ( ag_bridge_call_state == call_state ) &&
         ( ag_bridge_callsetup_state == callsetup_state ) &&
         ( ag_bridge_callheld_state == callheld_state ) )
    {
        return;
    }

    ag_bridge_call_state = call_state;
    ag_bridge_callsetup_state = callsetup_state;
    ag_bridge_callheld_state = callheld_state;

    hci_control_ag_bridge_set_cind(call_state, callsetup_state, callheld_state);
    hci_control_ag_bridge_send_ciev(p_scb, '3', callheld_state);
    hci_control_ag_bridge_send_ciev(p_scb, '2', callsetup_state);
    hci_control_ag_bridge_send_ciev(p_scb, '1', call_state);
    hci_control_send_bridge_status_line(reason);
}

static void hci_control_ag_bridge_assert_incoming( hfp_ag_session_cb_t *p_scb, const char *reason )
{
    hci_control_ag_bridge_set_cind('0', '1', '0');
    hci_control_ag_bridge_send_ciev(p_scb, '2', '1');
    hci_control_send_bridge_status_line(reason);

    ag_bridge_call_state = '0';
    ag_bridge_callsetup_state = '1';
    ag_bridge_callheld_state = '0';
}

static wiced_bool_t hci_control_ag_bridge_get_clcc_status( char *status )
{
    if ( status == NULL )
    {
        return WICED_FALSE;
    }

    if ( ag_bridge_callsetup_state == '1' )
    {
        *status = '4'; /* incoming */
        return WICED_TRUE;
    }

    if ( ag_bridge_callsetup_state == '2' )
    {
        *status = '2'; /* dialing */
        return WICED_TRUE;
    }

    if ( ag_bridge_callsetup_state == '3' )
    {
        *status = '3'; /* alerting */
        return WICED_TRUE;
    }

    if ( ag_bridge_call_state == '1' )
    {
        *status = '0'; /* active */
        return WICED_TRUE;
    }

    if ( ag_bridge_callheld_state != '0' )
    {
        *status = '1'; /* held */
        return WICED_TRUE;
    }

    return WICED_FALSE;
}

static void hci_control_ag_bridge_send_clcc_response( hfp_ag_session_cb_t *p_scb )
{
    char status;

    if ( hci_control_ag_bridge_get_clcc_status(&status) )
    {
        char clcc[80];
        char *p = clcc;
        char *end = &clcc[sizeof(clcc) - 1U];

        p = hci_control_ag_bridge_append_text(p, end, "+CLCC: 1,1,");
        if ( p < end )
        {
            *p++ = status;
        }
        p = hci_control_ag_bridge_append_text(p, end, ",0,0");

        if ( ag_bridge_caller_id[0] != '\0' )
        {
            p = hci_control_ag_bridge_append_text(p, end, ",\"");
            p = hci_control_ag_bridge_append_number(p, end, ag_bridge_caller_id);
            p = hci_control_ag_bridge_append_text(p, end, "\",");
            p = hci_control_ag_bridge_append_text(p, end, ( ag_bridge_caller_id[0] == '+' ) ? "145" : "129");
        }

        *p = '\0';
        hci_control_ag_bridge_send_ag_str(p_scb, clcc);
    }
    else
    {
        hci_control_send_bridge_status_line("AG_CALL:CLCC no calls");
    }

    hci_control_ag_bridge_send_ag_str(p_scb, "OK");
    hci_control_send_bridge_status_line("AG_CALL:CLCC response");
}

/******************************************************
 *               Function Definitions
 ******************************************************/
/*
 * Audio Gateway init
 */
void hci_control_ag_init( void )
{
    hfp_ag_session_cb_t *p_scb = &ag_scb[0];
    wiced_bt_dev_status_t result;
    int i;

    memset( &ag_scb, 0, sizeof( hfp_ag_session_cb_t ) );

    for ( i = 0; i < HCI_CONTROL_AG_NUM_SCB; i++, p_scb++ )
    {
        p_scb->app_handle = ( uint16_t ) ( i + 1 );

        if(i == 0)
            p_scb->hf_profile_uuid = UUID_SERVCLASS_HF_HANDSFREE;
        else
            p_scb->hf_profile_uuid = UUID_SERVCLASS_HEADSET;
    }

    hfp_ag_startup( &ag_scb[0], HCI_CONTROL_AG_NUM_SCB, BT_AUDIO_HFP_SUPPORTED_FEATURES );
}

void hci_control_ag_bridge_on_clcc_req( uint16_t handle )
{
    ag_bridge_clcc_handle = handle;
    ag_bridge_clcc_pending = WICED_TRUE;
}

void hci_control_ag_bridge_flush_pending_clcc( void )
{
    hfp_ag_session_cb_t *p_scb;

    if ( ag_bridge_clcc_pending == WICED_FALSE )
    {
        return;
    }

    ag_bridge_clcc_pending = WICED_FALSE;
    p_scb = hci_control_ag_bridge_get_scb_by_handle(ag_bridge_clcc_handle);
    if ( p_scb == NULL )
    {
        hci_control_send_bridge_status_line("AG_CALL:CLCC no handle");
        return;
    }

    hci_control_send_bridge_status_line("AG_CALL:CLCC req");
    hci_control_ag_bridge_send_clcc_response(p_scb);
}

void hci_control_ag_bridge_note_car_at_command( const uint8_t *cmd, uint16_t cmd_len )
{
    if ( ( cmd == NULL ) || ( cmd_len == 0U ) )
    {
        return;
    }

    if ( hci_control_ag_bridge_at_matches(cmd, cmd_len, "ATA") ||
         hci_control_ag_bridge_at_matches(cmd, cmd_len, "AT+CHLD=1") ||
         hci_control_ag_bridge_at_matches(cmd, cmd_len, "AT+CHLD=2") )
    {
        hci_control_ag_bridge_queue_car_cmd(AG_BRIDGE_CAR_CMD_ANSWER);
        return;
    }

    if ( hci_control_ag_bridge_at_matches(cmd, cmd_len, "AT+CHLD=0") )
    {
        hci_control_ag_bridge_queue_car_cmd(AG_BRIDGE_CAR_CMD_REJECT);
        return;
    }

    if ( hci_control_ag_bridge_at_matches(cmd, cmd_len, "AT+CHUP") )
    {
        hci_control_ag_bridge_queue_car_cmd(
            ( ag_bridge_callsetup_state == '1' ) ?
                AG_BRIDGE_CAR_CMD_REJECT : AG_BRIDGE_CAR_CMD_HANGUP);
    }
}

void hci_control_ag_bridge_flush_pending_car_commands( void )
{
    hfp_ag_session_cb_t *p_scb;

    if ( ag_bridge_pending_car_cmd_count == 0U )
    {
        return;
    }

    p_scb = hci_control_ag_bridge_get_car_scb();

    while ( ag_bridge_pending_car_cmd_count != 0U )
    {
        uint8_t cmd = ag_bridge_pending_car_cmd[ag_bridge_pending_car_cmd_tail];

        ag_bridge_pending_car_cmd_tail =
            (uint8_t)( ( ag_bridge_pending_car_cmd_tail + 1U ) % AG_BRIDGE_CAR_CMD_QUEUE_DEPTH );
        ag_bridge_pending_car_cmd_count--;

        switch ( cmd )
        {
        case AG_BRIDGE_CAR_CMD_ANSWER:
            if ( p_scb != NULL )
            {
                hci_control_ag_bridge_set_call_state(p_scb, '1', '0', '0', "AG_CALL:local answer");
            }
            hci_control_ag_bridge_send_puart_line("BR1,ANSWER");
            break;

        case AG_BRIDGE_CAR_CMD_REJECT:
            if ( p_scb != NULL )
            {
                hci_control_ag_bridge_set_call_state(p_scb, '0', '0', '0', "AG_CALL:local reject");
                ag_bridge_caller_id[0] = '\0';
            }
            hci_control_ag_bridge_send_puart_line("BR1,REJECT");
            break;

        case AG_BRIDGE_CAR_CMD_HANGUP:
            if ( p_scb != NULL )
            {
                hci_control_ag_bridge_set_call_state(p_scb, '0', '0', '0', "AG_CALL:local hangup");
                ag_bridge_caller_id[0] = '\0';
            }
            hci_control_ag_bridge_send_puart_line("BR1,HANGUP");
            break;

        default:
            break;
        }
    }
}

void hci_control_ag_bridge_handle_line( const uint8_t *line, uint16_t line_len )
{
    hfp_ag_session_cb_t *p_scb;

    if ( ( line == NULL ) || ( line_len < 4U ) )
    {
        return;
    }

    if ( hci_control_ag_bridge_handle_media_line(line, line_len) )
    {
        return;
    }

    p_scb = hci_control_ag_bridge_get_car_scb();
    if ( p_scb == NULL )
    {
        return;
    }

    if ( hci_control_ag_bridge_line_matches(line, line_len, "BR1,INCOMING") )
    {
        hci_control_ag_bridge_set_call_state(p_scb, '0', '1', '0', "AG_CALL:incoming");
        return;
    }

    if ( hci_control_ag_bridge_line_starts_with(line, line_len, "BR1,INCOMING,") )
    {
        hci_control_ag_bridge_save_cid(&line[13], (uint16_t)(line_len - 13U));
        hci_control_ag_bridge_set_call_state(p_scb, '0', '1', '0', "AG_CALL:incoming cid");
        hci_control_ag_bridge_send_clip(p_scb);
        return;
    }

    if ( hci_control_ag_bridge_line_matches(line, line_len, "BR1,RING") )
    {
        hci_control_ag_bridge_assert_incoming(p_scb, "AG_CALL:incoming via ring");
        hci_control_ag_bridge_send_ag_str(p_scb, "RING");
        hci_control_ag_bridge_send_clip(p_scb);
        hci_control_send_bridge_status_line("AG_CALL:ring");
        return;
    }

    if ( hci_control_ag_bridge_line_starts_with(line, line_len, "BR1,CID,") )
    {
        hci_control_ag_bridge_save_cid(&line[8], (uint16_t)(line_len - 8U));
        hci_control_ag_bridge_assert_incoming(p_scb, "AG_CALL:incoming via cid");
        hci_control_ag_bridge_send_clip(p_scb);
        hci_control_send_bridge_status_line("AG_CALL:cid");
        return;
    }

    if ( hci_control_ag_bridge_line_matches(line, line_len, "BR1,ACTIVE") )
    {
        hci_control_ag_bridge_set_call_state(p_scb, '1', '0', '0', "AG_CALL:active");
        return;
    }

    if ( hci_control_ag_bridge_line_matches(line, line_len, "BR1,ENDED") )
    {
        hci_control_ag_bridge_set_call_state(p_scb, '0', '0', '0', "AG_CALL:ended");
        ag_bridge_caller_id[0] = '\0';
        return;
    }
}

/*
 * Handle Handsfree commands received over UART.
 */
void hci_control_ag_handle_command( uint16_t opcode, uint8_t* p_data, uint32_t length )
{
    uint16_t handle;
    uint8_t  hs_cmd;
    uint8_t  *p = ( uint8_t * ) p_data;

    switch ( opcode )
    {
    case HCI_CONTROL_AG_COMMAND_CONNECT:
        hci_control_switch_hfp_role( HFP_AUDIO_GATEWAY_ROLE );
        hfp_ag_connect( p );
        break;

    case HCI_CONTROL_AG_COMMAND_DISCONNECT:
        handle = p[0] | ( p[1] << 8 );
        hfp_ag_disconnect( handle );
        break;

    case HCI_CONTROL_AG_COMMAND_OPEN_AUDIO:
        handle = p[0] | ( p[1] << 8 );
        hfp_ag_audio_open( handle );
        break;

    case HCI_CONTROL_AG_COMMAND_CLOSE_AUDIO:
        handle = p[0] | ( p[1] << 8 );
        hfp_ag_audio_close( handle );
        break;
    case HCI_CONTROL_AG_COMMAND_SET_CIND:
        hfp_ag_set_cind((char *)&p[0], length);
        break;
    case HCI_CONTROL_AG_COMMAND_STR:
        handle = p[0] | ( p[1] << 8 );
        hfp_ag_send_cmd_str(handle, &p[2], length-2);
        break;
    default:
        WICED_BT_TRACE ( "hci_control_ag_handle_command - unkn own opcode: %u %u\n", opcode);
        break;
    }
}

#endif  // WICED_APP_HFP_AG_INCLUDED
