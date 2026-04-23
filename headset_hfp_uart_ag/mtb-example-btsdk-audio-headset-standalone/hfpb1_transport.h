/*
 * HFPB1 transport core (Phase 2 scaffolding)
 *
 * This module owns protocol framing, CRC validation, sequence/session tracking,
 * and transport-level policy helpers. HFP semantic policy mapping is handled
 * separately in AG/HF profile modules.
 */

#pragma once

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define HFPB1_PROTOCOL_TAG "HFPB1"

#define HFPB1_MAX_FRAME_LEN       1024U
#define HFPB1_MAX_TYPE_LEN        4U
#define HFPB1_MAX_ENDPOINT_LEN    2U
#define HFPB1_MAX_SESSION_LEN     8U
#define HFPB1_MAX_SEQ_TEXT_LEN    8U
#define HFPB1_MAX_REF_TEXT_LEN    8U
#define HFPB1_MAX_FLAGS_LEN       2U
#define HFPB1_MAX_TS_LEN          12U
#define HFPB1_MAX_PAYLOAD_LEN     720U

#define HFPB1_CRIT_QUEUE_MAX      64U
#define HFPB1_NONCRIT_QUEUE_MAX   256U
#define HFPB1_RETRY_MAX           5U

typedef enum
{
    HFPB1_ROLE_UNKNOWN = 0,
    HFPB1_ROLE_HF      = 1,
    HFPB1_ROLE_AG      = 2
} hfpb1_role_t;

typedef struct
{
    char type[HFPB1_MAX_TYPE_LEN + 1];
    char src[HFPB1_MAX_ENDPOINT_LEN + 1];
    char dst[HFPB1_MAX_ENDPOINT_LEN + 1];
    char sid[HFPB1_MAX_SESSION_LEN + 1];
    char seq[HFPB1_MAX_SEQ_TEXT_LEN + 1];
    char ref[HFPB1_MAX_REF_TEXT_LEN + 1];
    char pri;
    char flags_hex[HFPB1_MAX_FLAGS_LEN + 1];
    char ts[HFPB1_MAX_TS_LEN + 1];
    char payload[HFPB1_MAX_PAYLOAD_LEN + 1];
    char crc_hex[5];
} hfpb1_frame_t;

typedef struct
{
    hfpb1_role_t role;
    char sid[HFPB1_MAX_SESSION_LEN + 1];
    uint32_t next_seq;
    uint16_t critical_queue_max;
    uint16_t noncritical_queue_max;
    uint8_t retry_max;
} hfpb1_transport_state_t;

void hfpb1_transport_init(hfpb1_role_t role, uint32_t session_seed);
const hfpb1_transport_state_t *hfpb1_transport_get_state(void);

uint16_t hfpb1_crc16_ccitt_false(const uint8_t *data, uint16_t length);
uint8_t hfpb1_parse_frame(const char *line, uint16_t line_len, hfpb1_frame_t *out_frame);
uint8_t hfpb1_encode_frame(const hfpb1_frame_t *frame, char *out_line, uint16_t out_size, uint16_t *out_len);

uint32_t hfpb1_next_sequence(void);
void hfpb1_fill_sequence(char out_seq[HFPB1_MAX_SEQ_TEXT_LEN + 1], uint32_t seq);
uint8_t hfpb1_is_ack_required(const hfpb1_frame_t *frame);
uint8_t hfpb1_is_critical_priority(char pri_char);

#ifdef __cplusplus
}
#endif

