#ifndef BB10_AK4531_CODEC_H
#define BB10_AK4531_CODEC_H
#include <stdint.h>
typedef void (*ak_write_t)(void *,uint16_t,uint16_t);
typedef struct {
    void *hardware;
    ak_write_t write;
    uint8_t regs[0x1a];
} ak_codec_t;
int ak_reset(ak_codec_t *);
int ak_volume(ak_codec_t *,unsigned,int,uint32_t [2]);
int ak_mute(ak_codec_t *,unsigned,int,uint32_t *);
#endif
