/* Experimental playback mixer for the BB10 simulator's existing audiopci DLL.
 * Real codec register writes and readback shadows; never reports a PCM transfer
 * successful itself. The unmodified controller/io-audio own PCM DMA/interrupts.
 * Capture exists as the controller's endpoint, without gain/input-route support.
 */
#include "dds_abi.h"
#include "codec.h"
#include <pthread.h>
#include <stdlib.h>
#include <errno.h>
struct ak_context {
    ado_mixer_dll_params_ak4531_t callbacks;
    ak_codec_t codec;
    pthread_mutex_t mutex;
};
void version(int *major,int *minor) {*major=5;*minor=AK4531_MINOR_VERSION;}
static int32_t reset(MIXER_CONTEXT_T *c) {
    int result;
    pthread_mutex_lock(&c->mutex);
    result=c->callbacks.init?c->callbacks.init(c->callbacks.hw_context):0;
    if(result==0) result=ak_reset(&c->codec);
    pthread_mutex_unlock(&c->mutex);return result;
}
static int32_t destroy(MIXER_CONTEXT_T *c) {
    if(c->callbacks.destroy)c->callbacks.destroy(c->callbacks.hw_context);
    pthread_mutex_destroy(&c->mutex);free(c);return 0;
}
static int32_t volume(MIXER_CONTEXT_T *c,ado_mixer_delement_t *e,uint8_t set,uint32_t *v,void *group) {
    int result;(void)e;pthread_mutex_lock(&c->mutex);
    result=ak_volume(&c->codec,(unsigned)(uintptr_t)group,set,v);
    pthread_mutex_unlock(&c->mutex);return result;
}
static int32_t mute(MIXER_CONTEXT_T *c,ado_mixer_delement_t *e,uint8_t set,uint32_t *v,void *group) {
    int result;(void)e;pthread_mutex_lock(&c->mutex);
    result=ak_mute(&c->codec,(unsigned)(uintptr_t)group,set,v);
    pthread_mutex_unlock(&c->mutex);return result;
}
static int route(ado_mixer_t *m,ado_mixer_delement_t *a,ado_mixer_delement_t *b) {
    return !a || !b || ado_mixer_element_route_add(m,a,b)!=0;
}
int mixer_dll_init(MIXER_CONTEXT_T **out,ado_mixer_t *m,void *params,void *unused,int api) {
    MIXER_CONTEXT_T *c;
    ado_mixer_delement_t *pcm,*pvol,*pmute,*acc,*mvol,*mmute,*output,*capture;
    int32_t device=0;
    snd_mixer_voice_t voices[2]={{0}};
    snd_mixer_element_volume1_range_t master[2]={{0}};
    snd_mixer_element_volume1_range_t input[2]={{0}};
    (void)unused;
    voices[0].voice=SND_MIXER_VOICE_LEFT;voices[1].voice=SND_MIXER_VOICE_RIGHT;
    master[0].max=master[1].max=input[0].max=input[1].max=31;
    master[0].min_dB=master[1].min_dB=-6200;
    input[0].min_dB=input[1].min_dB=-5000;
    input[0].max_dB=input[1].max_dB=1200;
    if(!out || !m || !params || api!=AK4531_MINOR_VERSION) {errno=EINVAL;return -1;}
    *out=NULL;c=calloc(1,sizeof *c);if(!c)return -1;
    c->callbacks=*(ado_mixer_dll_params_ak4531_t *)params;
    if(!c->callbacks.write) {free(c);errno=EINVAL;return -1;}
    c->codec.hardware=c->callbacks.hw_context;c->codec.write=c->callbacks.write;
    if(pthread_mutex_init(&c->mutex,NULL)!=0){free(c);return -1;}
    *out=c;
    /* Register cleanup immediately: io-audio destroys mixer on any later error. */
    ado_mixer_set_destroy_func(m,destroy);ado_mixer_set_reset_func(m,reset);
    if(reset(c)!=0)return -1;
    pcm=ado_mixer_element_pcm1(m,SND_MIXER_PCM_OUT,SND_MIXER_ETYPE_PLAYBACK1,1,&device);
    pvol=ado_mixer_element_volume1(m,"PCM Volume",2,input,volume,(void *)1,NULL);
    pmute=ado_mixer_element_sw2(m,"PCM Mute",mute,(void *)1,NULL);
    acc=ado_mixer_element_accu1(m,SND_MIXER_ELEMENT_OUTPUT_ACCU,0);
    mvol=ado_mixer_element_volume1(m,"Output Volume",2,master,volume,NULL,NULL);
    mmute=ado_mixer_element_sw2(m,"Output Mute",mute,NULL,NULL);
    output=ado_mixer_element_io(m,"Output",SND_MIXER_ETYPE_OUTPUT,0,2,voices);
    capture=ado_mixer_element_pcm1(m,SND_MIXER_ELEMENT_CAPTURE,SND_MIXER_ETYPE_CAPTURE1,1,&device);
    if(route(m,pcm,pvol)||route(m,pvol,pmute)||route(m,pmute,acc)||route(m,acc,mvol)||route(m,mvol,mmute)||route(m,mmute,output)||!capture)return -1;
    if(!ado_mixer_playback_group_create(m,SND_MIXER_PCM_OUT,SND_MIXER_CHN_MASK_STEREO,pvol,pmute))return -1;
    if(!ado_mixer_playback_group_create(m,SND_MIXER_MASTER_OUT,SND_MIXER_CHN_MASK_STEREO,mvol,mmute))return -1;
    if(!ado_mixer_capture_group_create(m,SND_MIXER_GRP_IGAIN,SND_MIXER_CHN_MASK_STEREO,NULL,NULL,NULL,NULL))return -1;
    return 0;
}
