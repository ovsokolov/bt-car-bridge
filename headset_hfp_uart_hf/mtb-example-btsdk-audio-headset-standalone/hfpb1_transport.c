/*
 * HFPB1 transport core (Phase 2 scaffolding)
 */

#include "hfpb1_transport.h"

#include <stdio.h>
#include <string.h>

static hfpb1_transport_state_t g_hfpb1_state;

static uint8_t hfpb1_is_hex_char(char c)
{
    return (uint8_t)(((c >= '0') && (c <= '9')) ||
                     ((c >= 'A') && (c <= 'F')) ||
                     ((c >= 'a') && (c <= 'f')));
}

static uint8_t hfpb1_hex_nibble(char c)
{
    if (c >= '0' && c <= '9')
    {
        return (uint8_t)(c - '0');
    }
    if (c >= 'A' && c <= 'F')
    {
        return (uint8_t)(10 + (c - 'A'));
    }
    if (c >= 'a' && c <= 'f')
    {
        return (uint8_t)(10 + (c - 'a'));
    }
    return 0;
}

static uint16_t hfpb1_parse_u16_hex(const char *text, uint8_t len)
{
    uint16_t value = 0;
    uint8_t i;
    for (i = 0; i < len; i++)
    {
        value = (uint16_t)((value << 4) | hfpb1_hex_nibble(text[i]));
    }
    return value;
}

static void hfpb1_u32_to_hex8(uint32_t value, char out_text[9])
{
    static const char *k_hex = "0123456789ABCDEF";
    int i;
    for (i = 7; i >= 0; i--)
    {
        out_text[i] = k_hex[value & 0xFU];
        value >>= 4;
    }
    out_text[8] = '\0';
}

static void hfpb1_u16_to_hex4(uint16_t value, char out_text[5])
{
    static const char *k_hex = "0123456789ABCDEF";
    int i;
    for (i = 3; i >= 0; i--)
    {
        out_text[i] = k_hex[value & 0xFU];
        value >>= 4;
    }
    out_text[4] = '\0';
}

static uint8_t hfpb1_copy_field(char *dst, uint16_t dst_size, const char *src, uint16_t src_len)
{
    if (dst == NULL || src == NULL || dst_size == 0 || src_len >= dst_size)
    {
        return 0;
    }
    memcpy(dst, src, src_len);
    dst[src_len] = '\0';
    return 1;
}

void hfpb1_transport_init(hfpb1_role_t role, uint32_t session_seed)
{
    memset(&g_hfpb1_state, 0, sizeof(g_hfpb1_state));
    g_hfpb1_state.role = role;
    g_hfpb1_state.next_seq = 1U;
    g_hfpb1_state.critical_queue_max = HFPB1_CRIT_QUEUE_MAX;
    g_hfpb1_state.noncritical_queue_max = HFPB1_NONCRIT_QUEUE_MAX;
    g_hfpb1_state.retry_max = HFPB1_RETRY_MAX;

    /* SID is a deterministic 8-hex token in v1. */
    if (session_seed == 0U)
    {
        session_seed = (role == HFPB1_ROLE_AG) ? 0xA6000001U : 0xF1000001U;
    }
    hfpb1_u32_to_hex8(session_seed, g_hfpb1_state.sid);
}

const hfpb1_transport_state_t *hfpb1_transport_get_state(void)
{
    return &g_hfpb1_state;
}

uint16_t hfpb1_crc16_ccitt_false(const uint8_t *data, uint16_t length)
{
    uint16_t crc = 0xFFFFU;
    uint16_t i;
    uint8_t bit;
    if (data == NULL)
    {
        return crc;
    }
    for (i = 0; i < length; i++)
    {
        crc ^= (uint16_t)((uint16_t)data[i] << 8);
        for (bit = 0; bit < 8; bit++)
        {
            if ((crc & 0x8000U) != 0U)
            {
                crc = (uint16_t)((crc << 1) ^ 0x1021U);
            }
            else
            {
                crc <<= 1;
            }
        }
    }
    return crc;
}

uint32_t hfpb1_next_sequence(void)
{
    uint32_t current = g_hfpb1_state.next_seq;
    if (g_hfpb1_state.next_seq == 0xFFFFFFFFU)
    {
        g_hfpb1_state.next_seq = 1U;
    }
    else
    {
        g_hfpb1_state.next_seq++;
    }
    return current;
}

void hfpb1_fill_sequence(char out_seq[HFPB1_MAX_SEQ_TEXT_LEN + 1], uint32_t seq)
{
    if (out_seq == NULL)
    {
        return;
    }
    hfpb1_u32_to_hex8(seq, out_seq);
}

uint8_t hfpb1_is_critical_priority(char pri_char)
{
    return (uint8_t)(pri_char == 'C');
}

uint8_t hfpb1_is_ack_required(const hfpb1_frame_t *frame)
{
    if (frame == NULL)
    {
        return 0;
    }
    if ((strcmp(frame->type, "SYN") == 0) ||
        (strcmp(frame->type, "RST") == 0) ||
        (strcmp(frame->type, "SNP") == 0))
    {
        return 1;
    }
    if ((strcmp(frame->type, "HFP") == 0) && hfpb1_is_critical_priority(frame->pri))
    {
        return 1;
    }
    return 0;
}

uint8_t hfpb1_parse_frame(const char *line, uint16_t line_len, hfpb1_frame_t *out_frame)
{
    char scratch[HFPB1_MAX_FRAME_LEN + 1];
    char *parts[12];
    uint8_t part_count = 0;
    uint16_t i;
    uint16_t payload_len;
    uint16_t parsed_crc;
    uint16_t computed_crc;
    char *cursor;

    if (line == NULL || out_frame == NULL || line_len == 0 || line_len > HFPB1_MAX_FRAME_LEN)
    {
        return 0;
    }

    while (line_len > 0 && (line[line_len - 1] == '\n' || line[line_len - 1] == '\r'))
    {
        line_len--;
    }
    if (line_len == 0 || line_len > HFPB1_MAX_FRAME_LEN)
    {
        return 0;
    }

    memcpy(scratch, line, line_len);
    scratch[line_len] = '\0';

    for (i = 0; i < line_len; i++)
    {
        if (scratch[i] == '|')
        {
            scratch[i] = '\0';
        }
    }

    cursor = scratch;
    while (part_count < 12U)
    {
        parts[part_count++] = cursor;
        cursor += strlen(cursor) + 1U;
        if ((cursor - scratch) >= (int)(line_len + 1U))
        {
            break;
        }
    }

    if (part_count != 12U)
    {
        return 0;
    }

    if (strcmp(parts[0], HFPB1_PROTOCOL_TAG) != 0)
    {
        return 0;
    }

    if (!hfpb1_copy_field(out_frame->type, sizeof(out_frame->type), parts[1], (uint16_t)strlen(parts[1])) ||
        !hfpb1_copy_field(out_frame->src, sizeof(out_frame->src), parts[2], (uint16_t)strlen(parts[2])) ||
        !hfpb1_copy_field(out_frame->dst, sizeof(out_frame->dst), parts[3], (uint16_t)strlen(parts[3])) ||
        !hfpb1_copy_field(out_frame->sid, sizeof(out_frame->sid), parts[4], (uint16_t)strlen(parts[4])) ||
        !hfpb1_copy_field(out_frame->seq, sizeof(out_frame->seq), parts[5], (uint16_t)strlen(parts[5])) ||
        !hfpb1_copy_field(out_frame->ref, sizeof(out_frame->ref), parts[6], (uint16_t)strlen(parts[6])) ||
        !hfpb1_copy_field(out_frame->flags_hex, sizeof(out_frame->flags_hex), parts[8], (uint16_t)strlen(parts[8])) ||
        !hfpb1_copy_field(out_frame->ts, sizeof(out_frame->ts), parts[9], (uint16_t)strlen(parts[9])))
    {
        return 0;
    }

    out_frame->pri = parts[7][0];
    payload_len = (uint16_t)strlen(parts[10]);
    if (!hfpb1_copy_field(out_frame->payload, sizeof(out_frame->payload), parts[10], payload_len))
    {
        return 0;
    }
    if (!hfpb1_copy_field(out_frame->crc_hex, sizeof(out_frame->crc_hex), parts[11], (uint16_t)strlen(parts[11])))
    {
        return 0;
    }

    if (strlen(out_frame->crc_hex) != 4U)
    {
        return 0;
    }
    for (i = 0; i < 4U; i++)
    {
        if (!hfpb1_is_hex_char(out_frame->crc_hex[i]))
        {
            return 0;
        }
    }

    /* Rebuild prefix with trailing '|' for CRC check. */
    {
        char crc_prefix[HFPB1_MAX_FRAME_LEN + 1];
        int written = snprintf(crc_prefix,
                               sizeof(crc_prefix),
                               "%s|%s|%s|%s|%s|%s|%s|%c|%s|%s|%s|",
                               HFPB1_PROTOCOL_TAG,
                               out_frame->type,
                               out_frame->src,
                               out_frame->dst,
                               out_frame->sid,
                               out_frame->seq,
                               out_frame->ref,
                               out_frame->pri,
                               out_frame->flags_hex,
                               out_frame->ts,
                               out_frame->payload);
        if (written <= 0 || written >= (int)sizeof(crc_prefix))
        {
            return 0;
        }
        computed_crc = hfpb1_crc16_ccitt_false((const uint8_t *)crc_prefix, (uint16_t)written);
    }

    parsed_crc = hfpb1_parse_u16_hex(out_frame->crc_hex, 4);
    return (uint8_t)(computed_crc == parsed_crc);
}

uint8_t hfpb1_encode_frame(const hfpb1_frame_t *frame, char *out_line, uint16_t out_size, uint16_t *out_len)
{
    char prefix[HFPB1_MAX_FRAME_LEN + 1];
    char crc_text[5];
    uint16_t crc;
    int prefix_len;
    int full_len;

    if (frame == NULL || out_line == NULL || out_size == 0)
    {
        return 0;
    }

    prefix_len = snprintf(prefix,
                          sizeof(prefix),
                          "%s|%s|%s|%s|%s|%s|%s|%c|%s|%s|%s|",
                          HFPB1_PROTOCOL_TAG,
                          frame->type,
                          frame->src,
                          frame->dst,
                          frame->sid,
                          frame->seq,
                          frame->ref,
                          frame->pri,
                          frame->flags_hex,
                          frame->ts,
                          frame->payload);
    if (prefix_len <= 0 || prefix_len >= (int)sizeof(prefix))
    {
        return 0;
    }

    crc = hfpb1_crc16_ccitt_false((const uint8_t *)prefix, (uint16_t)prefix_len);
    hfpb1_u16_to_hex4(crc, crc_text);

    full_len = snprintf(out_line, out_size, "%s%s\n", prefix, crc_text);
    if (full_len <= 0 || full_len >= (int)out_size)
    {
        return 0;
    }
    if (out_len != NULL)
    {
        *out_len = (uint16_t)full_len;
    }
    return 1;
}
