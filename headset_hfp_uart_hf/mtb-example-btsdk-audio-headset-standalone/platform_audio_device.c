/*
 * Minimal platform audio device shim for the HF CS4344 I2S DAC test.
 *
 * The Bluetooth audio data path is handled by the controller/audio-sink route
 * configuration. CS4344 has no control bus, so Audio Manager only needs these
 * hooks to succeed without selecting the host-audio UART platform device.
 */

#include "wiced.h"
#include "wiced_bt_trace.h"
#include "platform_audio_device.h"

static platform_audio_config_t platform_audio_device_config[PLATFORM_DEVICE_MAX];
static int32_t platform_audio_device_volume[PLATFORM_DEVICE_MAX];
static int32_t platform_audio_device_mic_gain[PLATFORM_DEVICE_MAX];

static wiced_bool_t platform_audio_device_valid(platform_audio_device_id_t device_id)
{
    return (device_id < PLATFORM_DEVICE_MAX) ? WICED_TRUE : WICED_FALSE;
}

wiced_result_t platform_audio_device_init(const platform_audio_device_id_t device_id)
{
    if (!platform_audio_device_valid(device_id))
    {
        return WICED_BADARG;
    }

    WICED_BT_TRACE("CS4344 audio_device_init id=%u\n", device_id);
    return WICED_SUCCESS;
}

wiced_result_t platform_audio_device_configure(const platform_audio_device_id_t device_id,
                                               platform_audio_config_t *config)
{
    if (!platform_audio_device_valid(device_id) || (config == NULL))
    {
        return WICED_BADARG;
    }

    platform_audio_device_config[device_id] = *config;
    WICED_BT_TRACE("CS4344 audio_device_config id=%u sr=%lu bits=%u ch=%u io=%u\n",
                   device_id,
                   (unsigned long)config->sample_rate,
                   config->bits_per_sample,
                   config->channels,
                   config->io_device);

    return WICED_SUCCESS;
}

wiced_result_t platform_audio_device_set_output_device(const platform_audio_device_id_t device_id,
                                                       platform_audio_io_device_t sink)
{
    if (!platform_audio_device_valid(device_id))
    {
        return WICED_BADARG;
    }

    platform_audio_device_config[device_id].io_device = sink;
    return WICED_SUCCESS;
}

wiced_result_t platform_audio_device_set_sr(const platform_audio_device_id_t device_id, int32_t sr)
{
    if (!platform_audio_device_valid(device_id))
    {
        return WICED_BADARG;
    }

    platform_audio_device_config[device_id].sample_rate = (uint32_t)sr;
    return WICED_SUCCESS;
}

wiced_result_t platform_audio_device_set_volume(const platform_audio_device_id_t device_id,
                                                int32_t volume_in_db)
{
    if (!platform_audio_device_valid(device_id))
    {
        return WICED_BADARG;
    }

    platform_audio_device_volume[device_id] = volume_in_db;
    return WICED_SUCCESS;
}

wiced_result_t platform_audio_device_set_mic_gain(const platform_audio_device_id_t device_id,
                                                  int32_t volume_in_db)
{
    if (!platform_audio_device_valid(device_id))
    {
        return WICED_BADARG;
    }

    platform_audio_device_mic_gain[device_id] = volume_in_db;
    return WICED_SUCCESS;
}

wiced_result_t platform_audio_device_get_volume(const platform_audio_device_id_t device_id,
                                                int32_t *volume_in_db)
{
    if (!platform_audio_device_valid(device_id) || (volume_in_db == NULL))
    {
        return WICED_BADARG;
    }

    *volume_in_db = platform_audio_device_volume[device_id];
    return WICED_SUCCESS;
}

wiced_result_t platform_audio_device_get_volume_range(const platform_audio_device_id_t device_id,
                                                      int32_t *min_volume_in_db,
                                                      int32_t *max_volume_in_db)
{
    if (!platform_audio_device_valid(device_id) ||
        (min_volume_in_db == NULL) ||
        (max_volume_in_db == NULL))
    {
        return WICED_BADARG;
    }

    *min_volume_in_db = 0;
    *max_volume_in_db = 100;
    return WICED_SUCCESS;
}

wiced_result_t platform_audio_device_deinit(const platform_audio_device_id_t device_id)
{
    if (!platform_audio_device_valid(device_id))
    {
        return WICED_BADARG;
    }

    return WICED_SUCCESS;
}

wiced_result_t platform_audio_device_start(const platform_audio_device_id_t device_id)
{
    if (!platform_audio_device_valid(device_id))
    {
        return WICED_BADARG;
    }

    WICED_BT_TRACE("CS4344 audio_device_start id=%u sr=%lu ch=%u\n",
                   device_id,
                   (unsigned long)platform_audio_device_config[device_id].sample_rate,
                   platform_audio_device_config[device_id].channels);
    return WICED_SUCCESS;
}

wiced_result_t platform_audio_device_stop(const platform_audio_device_id_t device_id)
{
    if (!platform_audio_device_valid(device_id))
    {
        return WICED_BADARG;
    }

    WICED_BT_TRACE("CS4344 audio_device_stop id=%u\n", device_id);
    return WICED_SUCCESS;
}

wiced_result_t platform_audio_device_ioctl(const platform_audio_device_id_t device_id,
                                           platform_audio_device_ioctl_t cmd,
                                           platform_audio_device_ioctl_data_t *cmd_data)
{
    UNUSED_VARIABLE(cmd);
    UNUSED_VARIABLE(cmd_data);

    if (!platform_audio_device_valid(device_id))
    {
        return WICED_BADARG;
    }

    return WICED_SUCCESS;
}
