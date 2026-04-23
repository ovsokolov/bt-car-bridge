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

#include "hci_control_api.h"
#include "wiced_bt_trace.h"
#include "hci_control_hfp_ag.h"
#include "hci_control.h"
#include "wiced_app.h"
#include "wiced_timer.h"

#include "wiced_bt_hfp_ag.h"
#include <string.h>
#include <stdarg.h>

#if (BTM_WBS_INCLUDED == TRUE )
#define BT_AUDIO_HFP_SUPPORTED_FEATURES     (HFP_AG_FEAT_VREC | HFP_AG_FEAT_INBAND | HFP_AG_FEAT_CODEC | HFP_AG_FEAT_ESCO | HFP_AG_FEAT_ECS | HFP_AG_FEAT_ECC)
#else
#define BT_AUDIO_HFP_SUPPORTED_FEATURES     (HFP_AG_FEAT_VREC | HFP_AG_FEAT_INBAND | HFP_AG_FEAT_ESCO | HFP_AG_FEAT_ECS | HFP_AG_FEAT_ECC)
#endif

#define AG_PENDING_STR_MAX 24
#define AG_PENDING_STR_LEN 260

#define strncmp hci_control_ag_strncmp
#define snprintf hci_control_ag_snprintf
#define sscanf hci_control_ag_sscanf
#define atoi hci_control_ag_atoi

/******************************************************
 *               Variables Definitions
 ******************************************************/
hfp_ag_session_cb_t  ag_scb[HCI_CONTROL_AG_NUM_SCB];
typedef struct
{
    uint16_t requested_handle;
    uint8_t critical;
    char str[AG_PENDING_STR_LEN];
} ag_pending_str_entry_t;
static ag_pending_str_entry_t ag_pending_str_queue[AG_PENDING_STR_MAX];
static uint8_t ag_pending_str_count = 0;
static uint8_t ag_phone_hf_cind[8] = {0, 0, 0, 0, 0, 5, 0, 5};
static char ag_last_clip_number[64] = {0};
static char ag_last_clip_type[8] = "129";
static wiced_bool_t ag_call_has_real_clip = WICED_FALSE;
static wiced_bool_t ag_ring_placeholder_clip_sent = WICED_FALSE;

extern hfp_ag_session_cb_t *hfp_ag_find_scb_by_app_handle( uint16_t app_handle );

/******************************************************
 *               Static Function Declarations
 ******************************************************/
/******************************************************
 *               Function Definitions
 ******************************************************/
static int hci_control_ag_strncmp(const char *a, const char *b, size_t n)
{
    size_t i;
    for (i = 0; i < n; i++)
    {
        unsigned char ca = (unsigned char)a[i];
        unsigned char cb = (unsigned char)b[i];
        if (ca != cb)
        {
            return (int)ca - (int)cb;
        }
        if (ca == 0)
        {
            return 0;
        }
    }
    return 0;
}

static int hci_control_ag_atoi(const char *s)
{
    int sign = 1;
    int value = 0;
    while (*s == ' ' || *s == '\t')
    {
        s++;
    }
    if (*s == '-')
    {
        sign = -1;
        s++;
    }
    else if (*s == '+')
    {
        s++;
    }
    while (*s >= '0' && *s <= '9')
    {
        value = (value * 10) + (*s - '0');
        s++;
    }
    return sign * value;
}

static int hci_control_ag_snprintf(char *dst, size_t size, const char *fmt, ...)
{
    va_list args;
    size_t out_len = 0;
    const char *p = fmt;

    if (size == 0U)
    {
        return 0;
    }

    dst[0] = 0;
    va_start(args, fmt);
    while (*p != 0)
    {
        if (*p != '%')
        {
            if (out_len + 1U < size)
            {
                dst[out_len] = *p;
            }
            out_len++;
            p++;
            continue;
        }

        p++;
        if (*p == 's')
        {
            const char *s = va_arg(args, const char *);
            while (*s != 0)
            {
                if (out_len + 1U < size)
                {
                    dst[out_len] = *s;
                }
                out_len++;
                s++;
            }
            p++;
        }
        else if (*p == 'u' || *p == 'd')
        {
            int value = (*p == 'u') ? (int)va_arg(args, unsigned int) : va_arg(args, int);
            char num[16];
            uint16_t nlen = 0;
            if (value < 0)
            {
                if (out_len + 1U < size)
                {
                    dst[out_len] = '-';
                }
                out_len++;
                value = -value;
            }
            utl_itoa((uint16_t)value, num);
            nlen = (uint16_t)strlen(num);
            if (nlen > 0)
            {
                uint16_t i;
                for (i = 0; i < nlen; i++)
                {
                    if (out_len + 1U < size)
                    {
                        dst[out_len] = num[i];
                    }
                    out_len++;
                }
            }
            p++;
        }
        else
        {
            if (out_len + 1U < size)
            {
                dst[out_len] = '%';
            }
            out_len++;
        }
    }
    if (out_len >= size)
    {
        dst[size - 1U] = 0;
    }
    else
    {
        dst[out_len] = 0;
    }
    va_end(args);
    return (int)out_len;
}

static int hci_control_ag_sscanf(const char *src, const char *fmt, ...)
{
    va_list args;
    int expected = 0;
    int matched = 0;
    const char *f = fmt;
    const char *s = src;

    while (*f != 0)
    {
        if (f[0] == '%' && f[1] == 'd')
        {
            expected++;
            f += 2;
            continue;
        }
        f++;
    }

    va_start(args, fmt);
    while (matched < expected)
    {
        int sign = 1;
        int value = 0;
        int has_digit = 0;
        int *out = va_arg(args, int *);

        while (*s == ' ' || *s == '\t' || *s == ',')
        {
            s++;
        }
        if (*s == '-')
        {
            sign = -1;
            s++;
        }
        else if (*s == '+')
        {
            s++;
        }
        while (*s >= '0' && *s <= '9')
        {
            has_digit = 1;
            value = (value * 10) + (*s - '0');
            s++;
        }
        if (!has_digit)
        {
            break;
        }
        *out = sign * value;
        matched++;
    }
    va_end(args);
    return matched;
}

static wiced_bool_t hci_control_ag_is_critical_str(const char *line)
{
    return ((strncmp(line, "RING", 4) == 0) ||
            (strncmp(line, "+CLIP:", 6) == 0) ||
            (strncmp(line, "+CCWA:", 6) == 0) ||
            (strncmp(line, "+CLCC:", 6) == 0) ||
            (strncmp(line, "+CIEV: 2,", 9) == 0) ||
            (strncmp(line, "+CIEV: 3,", 9) == 0) ||
            (strncmp(line, "OK", 2) == 0) ||
            (strncmp(line, "ERROR", 5) == 0));
}

static void hci_control_ag_remove_pending_str(uint8_t index)
{
    if (index >= ag_pending_str_count)
    {
        return;
    }

    if ((index + 1U) < ag_pending_str_count)
    {
        memmove(&ag_pending_str_queue[index],
                &ag_pending_str_queue[index + 1U],
                (size_t)(ag_pending_str_count - (index + 1U)) * sizeof(ag_pending_str_entry_t));
    }

    ag_pending_str_count--;
}

static void hci_control_ag_clear_pending_str(const char *reason)
{
    if (ag_pending_str_count == 0)
    {
        return;
    }

    WICED_BT_TRACE("[AG_POLICY] clearing %u queued AG string(s): %s\n",
                   ag_pending_str_count,
                   reason);
    ag_pending_str_count = 0;
}

static void hci_control_ag_enqueue_pending_str(uint16_t requested_handle, const char *line)
{
    uint8_t insert_index = ag_pending_str_count;
    wiced_bool_t critical = hci_control_ag_is_critical_str(line);

    if (ag_pending_str_count >= AG_PENDING_STR_MAX)
    {
        uint8_t i;
        uint8_t drop_index = 0;

        if (critical)
        {
            for (i = 0; i < ag_pending_str_count; i++)
            {
                if (!ag_pending_str_queue[i].critical)
                {
                    drop_index = i;
                    break;
                }
            }
        }

        WICED_BT_TRACE("[AG_POLICY] pending AG string queue full (%u). Dropping %s entry '%s'\n",
                       ag_pending_str_count,
                       ag_pending_str_queue[drop_index].critical ? "critical" : "non-critical",
                       ag_pending_str_queue[drop_index].str);
        hci_control_ag_remove_pending_str(drop_index);
        insert_index = ag_pending_str_count;
    }

    ag_pending_str_queue[insert_index].requested_handle = requested_handle;
    ag_pending_str_queue[insert_index].critical = (uint8_t)(critical ? 1U : 0U);
    strncpy(ag_pending_str_queue[insert_index].str, line, AG_PENDING_STR_LEN - 1U);
    ag_pending_str_queue[insert_index].str[AG_PENDING_STR_LEN - 1U] = 0;
    ag_pending_str_count++;

    WICED_BT_TRACE("[AG_POLICY] deferred AG string (%s, depth=%u): %s\n",
                   critical ? "critical" : "normal",
                   ag_pending_str_count,
                   ag_pending_str_queue[insert_index].str);
}

static void hci_control_ag_send_str_now(uint16_t handle, const char *line, const char *source)
{
    WICED_BT_TRACE("[AG_POLICY] sending AG string from %s on handle %u: %s\n",
                   source,
                   handle,
                   line);
    hfp_ag_send_cmd_str(handle, (uint8_t *)line, strlen(line) + 1U);
}

static void hci_control_ag_flush_pending_str(uint16_t handle, const char *reason)
{
    uint8_t i;
    uint8_t priority;

    if (handle == 0 || ag_pending_str_count == 0)
    {
        return;
    }

    WICED_BT_TRACE("[AG_POLICY] flushing %u queued AG string(s) on handle %u after %s\n",
                   ag_pending_str_count,
                   handle,
                   reason);

    for (priority = 1; priority <= 2; priority++)
    {
        i = 0;
        while (i < ag_pending_str_count)
        {
            if ((priority == 1U && ag_pending_str_queue[i].critical) ||
                (priority == 2U && !ag_pending_str_queue[i].critical))
            {
                hci_control_ag_send_str_now(handle,
                                            ag_pending_str_queue[i].str,
                                            ag_pending_str_queue[i].critical ? "queue-replay critical" : "queue-replay");
                hci_control_ag_remove_pending_str(i);
                continue;
            }
            i++;
        }
    }
}

static wiced_bool_t hci_control_ag_starts_with(const char *text, const char *prefix)
{
    size_t prefix_len = strlen(prefix);
    return (strncmp(text, prefix, prefix_len) == 0) ? WICED_TRUE : WICED_FALSE;
}

static void hci_control_ag_format_current_cind(char *out, size_t out_size)
{
    snprintf(out,
             out_size,
             "%u,%u,%u,%u,%u,%u,%u",
             ag_phone_hf_cind[2],
             ag_phone_hf_cind[3],
             ag_phone_hf_cind[4],
             ag_phone_hf_cind[1],
             ag_phone_hf_cind[7],
             ag_phone_hf_cind[5],
             ag_phone_hf_cind[6]);
}

static void hci_control_ag_apply_stack_cind(const char *reason)
{
    char cind[48];
    hci_control_ag_format_current_cind(cind, sizeof(cind));
    hfp_ag_set_cind(cind, strlen(cind));
    WICED_BT_TRACE("[AG_POLICY] %s -> AG stack CIND %s\n", reason, cind);
}

static wiced_bool_t hci_control_ag_set_call_indicators(uint8_t call_val, uint8_t setup_val, uint8_t held_val)
{
    wiced_bool_t changed = WICED_FALSE;

    if (ag_phone_hf_cind[2] != call_val)
    {
        ag_phone_hf_cind[2] = call_val;
        changed = WICED_TRUE;
    }
    if (ag_phone_hf_cind[3] != setup_val)
    {
        ag_phone_hf_cind[3] = setup_val;
        changed = WICED_TRUE;
    }
    if (ag_phone_hf_cind[4] != held_val)
    {
        ag_phone_hf_cind[4] = held_val;
        changed = WICED_TRUE;
    }
    return changed;
}

static void hci_control_ag_send_policy_line(uint16_t handle, const char *line, const char *source)
{
    if (line == NULL || *line == 0)
    {
        return;
    }

    if (handle == 0)
    {
        hci_control_ag_enqueue_pending_str(handle, line);
    }
    else
    {
        hci_control_ag_send_str_now(handle, line, source);
    }
}

static void hci_control_ag_extract_clip(const char *line)
{
    const char *first_quote = strchr(line, '"');
    const char *second_quote = NULL;
    const char *comma_after = NULL;
    size_t number_len;
    int number_type;

    if (first_quote == NULL)
    {
        return;
    }

    second_quote = strchr(first_quote + 1, '"');
    if (second_quote == NULL || second_quote <= first_quote + 1)
    {
        return;
    }

    number_len = (size_t)(second_quote - (first_quote + 1));
    if (number_len >= sizeof(ag_last_clip_number))
    {
        number_len = sizeof(ag_last_clip_number) - 1;
    }
    memcpy(ag_last_clip_number, first_quote + 1, number_len);
    ag_last_clip_number[number_len] = 0;

    comma_after = strchr(second_quote + 1, ',');
    if (comma_after != NULL)
    {
        number_type = atoi(comma_after + 1);
        if (number_type > 0)
        {
            snprintf(ag_last_clip_type, sizeof(ag_last_clip_type), "%d", number_type);
        }
    }

    if ((strcmp(ag_last_clip_type, "145") == 0) &&
        (ag_last_clip_number[0] != 0) &&
        (ag_last_clip_number[0] != '+'))
    {
        char normalized[sizeof(ag_last_clip_number)];
        snprintf(normalized, sizeof(normalized), "+%s", ag_last_clip_number);
        strncpy(ag_last_clip_number, normalized, sizeof(ag_last_clip_number) - 1);
        ag_last_clip_number[sizeof(ag_last_clip_number) - 1] = 0;
    }

    ag_call_has_real_clip = WICED_TRUE;
    ag_ring_placeholder_clip_sent = WICED_FALSE;
}

static void hci_control_ag_send_placeholder_clip_if_needed(uint16_t handle, const char *reason)
{
    if (ag_call_has_real_clip || ag_ring_placeholder_clip_sent)
    {
        return;
    }
    hci_control_ag_send_policy_line(handle, "+CLIP: \"Unknown\",129", reason);
    ag_ring_placeholder_clip_sent = WICED_TRUE;
}

static void hci_control_ag_send_synthetic_clcc(uint16_t handle, uint8_t status, const char *reason)
{
    char clcc[160];
    const char *num_type = (ag_last_clip_type[0] != 0) ? ag_last_clip_type : "129";

    if (ag_last_clip_number[0] != 0)
    {
        snprintf(clcc,
                 sizeof(clcc),
                 "+CLCC: 1,1,%u,0,0,\"%s\",%s",
                 status,
                 ag_last_clip_number,
                 num_type);
    }
    else
    {
        snprintf(clcc,
                 sizeof(clcc),
                 "+CLCC: 1,1,%u,0,0,\"\",%s",
                 status,
                 num_type);
    }
    hci_control_ag_send_policy_line(handle, clcc, reason);
}

static void hci_control_ag_apply_clcc_status(uint16_t handle, int clcc_status, const char *reason)
{
    uint8_t call_val = 0;
    uint8_t setup_val = 0;
    uint8_t held_val = 0;
    char line[24];

    switch (clcc_status)
    {
    case 0:
        call_val = 1; setup_val = 0; held_val = 0;
        break;
    case 1:
        call_val = 1; setup_val = 0; held_val = 1;
        break;
    case 2:
    case 3:
        call_val = 0; setup_val = 2; held_val = 0;
        break;
    case 4:
        call_val = 0; setup_val = 1; held_val = 0;
        break;
    case 5:
        call_val = 1; setup_val = 1; held_val = 0;
        break;
    case 6:
        call_val = 1; setup_val = 0; held_val = 2;
        break;
    default:
        return;
    }

    if (!hci_control_ag_set_call_indicators(call_val, setup_val, held_val))
    {
        return;
    }

    hci_control_ag_apply_stack_cind(reason);
    snprintf(line, sizeof(line), "+CIEV: 1,%u", call_val);
    hci_control_ag_send_policy_line(handle, line, reason);
    snprintf(line, sizeof(line), "+CIEV: 2,%u", setup_val);
    hci_control_ag_send_policy_line(handle, line, reason);
    snprintf(line, sizeof(line), "+CIEV: 3,%u", held_val);
    hci_control_ag_send_policy_line(handle, line, reason);
}

static void hci_control_ag_process_host_hfp_text(uint16_t handle, const char *line)
{
    const uint8_t ciev_map[8] = {0, 4, 1, 2, 3, 6, 7, 5};
    char text[AG_PENDING_STR_LEN];
    size_t text_len;

    int idx;
    int val;
    int n1, n2, n3, n4, n5, n6, n7;
    int clcc_idx, clcc_dir, clcc_status;
    char converted[AG_PENDING_STR_LEN];
    char cind[48];

    if (line == NULL)
    {
        return;
    }

    text_len = strlen(line);
    while (text_len > 0 && (line[text_len - 1] == '\r' || line[text_len - 1] == '\n'))
    {
        text_len--;
    }
    if (text_len == 0)
    {
        return;
    }

    if (text_len >= sizeof(text))
    {
        text_len = sizeof(text) - 1;
    }
    memcpy(text, line, text_len);
    text[text_len] = 0;

    if (hci_control_ag_starts_with(text, "+CIEV:") &&
        (sscanf(text + 6, " %d , %d", &idx, &val) == 2) &&
        (idx >= 1) && (idx <= 7) &&
        (val >= 0) && (val <= 7))
    {
        ag_phone_hf_cind[idx] = (uint8_t)val;

        if ((ag_phone_hf_cind[2] == 0) && (ag_phone_hf_cind[3] == 0))
        {
            ag_call_has_real_clip = WICED_FALSE;
            ag_last_clip_number[0] = 0;
            strncpy(ag_last_clip_type, "129", sizeof(ag_last_clip_type) - 1);
            ag_last_clip_type[sizeof(ag_last_clip_type) - 1] = 0;
            ag_ring_placeholder_clip_sent = WICED_FALSE;
        }
        else if (idx == 3 && val == 0)
        {
            ag_ring_placeholder_clip_sent = WICED_FALSE;
        }

        hci_control_ag_apply_stack_cind("HF +CIEV");

        if (idx == 3 && val == 1)
        {
            hci_control_ag_send_policy_line(handle, "RING", "HF +CIEV 3,1 fallback");
            hci_control_ag_send_placeholder_clip_if_needed(handle, "HF +CIEV 3,1 fallback");
            if (ag_last_clip_number[0] != 0)
            {
                snprintf(converted,
                         sizeof(converted),
                         "+CLIP: \"%s\",%s",
                         ag_last_clip_number,
                         ag_last_clip_type[0] ? ag_last_clip_type : "129");
                hci_control_ag_send_policy_line(handle, converted, "HF +CIEV 3,1 fallback");
            }
            hci_control_ag_send_synthetic_clcc(handle, 4, "HF +CIEV 3,1 fallback");
        }

        if (ciev_map[idx] > 0)
        {
            snprintf(converted, sizeof(converted), "+CIEV: %u,%d", ciev_map[idx], val);
            hci_control_ag_send_policy_line(handle, converted, "HF +CIEV mapped");
        }
        return;
    }

    if (hci_control_ag_starts_with(text, "+CIND:") &&
        (sscanf(text + 6,
                " %d , %d , %d , %d , %d , %d , %d",
                &n1, &n2, &n3, &n4, &n5, &n6, &n7) == 7))
    {
        ag_phone_hf_cind[1] = (uint8_t)n1;
        ag_phone_hf_cind[2] = (uint8_t)n2;
        ag_phone_hf_cind[3] = (uint8_t)n3;
        ag_phone_hf_cind[4] = (uint8_t)n4;
        ag_phone_hf_cind[5] = (uint8_t)n5;
        ag_phone_hf_cind[6] = (uint8_t)n6;
        ag_phone_hf_cind[7] = (uint8_t)n7;

        hci_control_ag_format_current_cind(cind, sizeof(cind));
        hci_control_ag_apply_stack_cind("HF +CIND");
        snprintf(converted, sizeof(converted), "+CIND: %s", cind);
        hci_control_ag_send_policy_line(handle, converted, "HF +CIND mapped");
        return;
    }

    if (strcmp(text, "RING") == 0)
    {
        if (hci_control_ag_set_call_indicators(0, 1, 0))
        {
            hci_control_ag_apply_stack_cind("HF RING inferred incoming");
            hci_control_ag_send_policy_line(handle, "+CIEV: 1,0", "HF RING inferred incoming");
            hci_control_ag_send_policy_line(handle, "+CIEV: 2,1", "HF RING inferred incoming");
        }
        hci_control_ag_send_policy_line(handle, "RING", "HF RING passthrough");
        hci_control_ag_send_placeholder_clip_if_needed(handle, "HF RING fallback");
        hci_control_ag_send_synthetic_clcc(handle, 4, "HF RING fallback");
        return;
    }

    if (hci_control_ag_starts_with(text, "+CLIP:"))
    {
        hci_control_ag_extract_clip(text);
        if (ag_last_clip_number[0] != 0)
        {
            snprintf(converted,
                     sizeof(converted),
                     "+CLIP: \"%s\",%s",
                     ag_last_clip_number,
                     ag_last_clip_type[0] ? ag_last_clip_type : "129");
            hci_control_ag_send_policy_line(handle, converted, "HF +CLIP normalized");
        }
        else
        {
            hci_control_ag_send_policy_line(handle, text, "HF +CLIP passthrough");
        }
        return;
    }

    if (hci_control_ag_starts_with(text, "+CLCC:"))
    {
        if (sscanf(text + 6, " %d , %d , %d", &clcc_idx, &clcc_dir, &clcc_status) == 3)
        {
            hci_control_ag_apply_clcc_status(handle, clcc_status, "HF +CLCC status");
        }
        hci_control_ag_extract_clip(text);
        hci_control_ag_send_policy_line(handle, text, "HF +CLCC passthrough");
        return;
    }

    hci_control_ag_send_policy_line(handle, text, "HF text passthrough");
}
/*
 * Audio Gateway init
 */
void hci_control_ag_init( void )
{
    hfp_ag_session_cb_t *p_scb = &ag_scb[0];
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

void hci_control_ag_local_call_state_update( uint16_t handle, char call_state, char callsetup_state )
{
    ( void )handle;
    ( void )call_state;
    ( void )callsetup_state;
}

/*
 * Handle Handsfree commands received over UART.
 */
void hci_control_ag_handle_command( uint16_t opcode, uint8_t* p_data, uint32_t length )
{
    uint16_t handle;
    uint8_t  *p = ( uint8_t * ) p_data;

    switch ( opcode )
    {
    case HCI_CONTROL_AG_COMMAND_CONNECT:
        hci_control_switch_hfp_role( HFP_AUDIO_GATEWAY_ROLE );
        hf_note_manual_ag_connect();
        hfp_ag_connect( p );
        break;

    case HCI_CONTROL_AG_COMMAND_DISCONNECT:
        handle = p[0] | ( p[1] << 8 );
        hf_note_manual_ag_disconnect();
        hfp_ag_disconnect( handle );
        hci_control_ag_clear_pending_str("manual disconnect");
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
        if (length > 2U)
        {
            uint16_t raw_len = (uint16_t)(length - 2U);
            uint16_t i;
            uint16_t max_copy = (uint16_t)(AG_PENDING_STR_LEN - 1U);
            char line_buf[AG_PENDING_STR_LEN];

            memset(line_buf, 0, sizeof(line_buf));

            for (i = 0; i < raw_len && i < max_copy; i++)
            {
                if (p[2U + i] == 0)
                {
                    break;
                }
                line_buf[i] = (char)p[2U + i];
            }

            if (line_buf[0] == 0)
            {
                WICED_BT_TRACE("[AG_POLICY] ignored empty AG string from host\n");
            }
            else
            {
                hci_control_ag_process_host_hfp_text(handle, line_buf);
                if (handle != 0)
                {
                    hci_control_ag_flush_pending_str(handle, "AG handle available");
                }
            }
        }
        break;
    default:
        WICED_BT_TRACE ( "hci_control_ag_handle_command - unkn own opcode: %u %u\n", opcode);
        break;
    }
}

#endif  // WICED_APP_HFP_AG_INCLUDED
