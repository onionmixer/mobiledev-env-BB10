#include "codec.h"
#include <assert.h>
#include <stdio.h>
typedef struct {unsigned writes;uint8_t values[0x1a];} recorder_t;
static void record(void *p,uint16_t r,uint16_t v) {recorder_t *t=p;assert(r<0x1a);t->writes++;t->values[r]=(uint8_t)v;}
int main(void) {
    recorder_t r={0};ak_codec_t c={&r,record,{0}};uint32_t v[2]={31,0},m;
    assert(ak_reset(&c)==0 && r.writes>25);
    assert(r.values[0x16]==3 && r.values[0x17]==0);
    assert(r.values[0x10]==0x60 && r.values[0x11]==0x0c);
    assert(r.values[0]==0x10 && r.values[1]==0x10);
    assert(r.values[2]==0 && r.values[5]==0 && r.values[8]==0x9f);
    assert(ak_volume(&c,0,1,v)==1 && r.values[0]==0 && r.values[1]==31);
    v[0]=v[1]=999;assert(ak_volume(&c,0,0,v)==0 && v[0]==31 && v[1]==0);
    m=1;assert(ak_mute(&c,0,1,&m)==1 && r.values[0]==0x80 && r.values[1]==0x9f);
    v[0]=10;v[1]=20;assert(ak_volume(&c,0,1,v)==1 && r.values[0]==0x95 && r.values[1]==0x8b);
    m=0;assert(ak_mute(&c,0,1,&m)==1 && r.values[0]==21 && r.values[1]==11);
    v[0]=31;v[1]=999;assert(ak_volume(&c,1,1,v)==0 && r.values[2]==0 && r.values[5]==0);
    m=1;assert(ak_mute(&c,1,1,&m)==1 && r.values[2]==0x80 && r.values[5]==0x80);
    m=0;assert(ak_mute(&c,1,0,&m)==0 && m==1);
    assert(ak_volume(&c,2,1,v)==-1 && ak_reset(NULL)==-1);
    puts("PASS: real codec callback writes, reset/routing, stereo attenuation, mute preservation, clamping, shadow readback");
    return 0;
}
