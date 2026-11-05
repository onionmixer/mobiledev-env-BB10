/* Minimal documented QNX 6.x DDS declarations; no private structure layouts.
 * The BB10 SDK omits audio_driver.h. Types/ranges come from its asound headers;
 * function declarations follow QNX 6.4 Audio DDK API reference, checked against
 * the simulator's exported io-audio symbols and its deva-mixer-ac97 call sites.
 * This is an experimental ABI boundary, not a replacement full DDK header.
 */
#ifndef BB10_DDS_ABI_H
#define BB10_DDS_ABI_H
#include <stdint.h>
#include <sys/asound_common.h>
typedef struct ado_mixer ado_mixer_t;
typedef struct ado_mixer_delement ado_mixer_delement_t;
typedef struct ado_mixer_dgroup ado_mixer_dgroup_t;
typedef struct ak_context MIXER_CONTEXT_T;
typedef void HW_CONTEXT_T;
#include <mixer/ak4531_dll.h>
typedef int32_t control_t(MIXER_CONTEXT_T *,ado_mixer_delement_t *,uint8_t,uint32_t *,void *);
extern ado_mixer_delement_t *ado_mixer_element_volume1(ado_mixer_t *,char *,int32_t,snd_mixer_element_volume1_range_t *,control_t *,void *,void (*)(void *));
extern ado_mixer_delement_t *ado_mixer_element_sw2(ado_mixer_t *,char *,control_t *,void *,void (*)(void *));
extern ado_mixer_delement_t *ado_mixer_element_pcm1(ado_mixer_t *,char *,int32_t,uint32_t,int32_t *);
extern ado_mixer_delement_t *ado_mixer_element_accu1(ado_mixer_t *,char *,int32_t);
extern ado_mixer_delement_t *ado_mixer_element_io(ado_mixer_t *,char *,int32_t,int32_t,uint32_t,snd_mixer_voice_t *);
extern int32_t ado_mixer_element_route_add(ado_mixer_t *,ado_mixer_delement_t *,ado_mixer_delement_t *);
extern ado_mixer_dgroup_t *ado_mixer_playback_group_create(ado_mixer_t *,char *,uint32_t,ado_mixer_delement_t *,ado_mixer_delement_t *);
extern ado_mixer_dgroup_t *ado_mixer_capture_group_create(ado_mixer_t *,char *,uint32_t,ado_mixer_delement_t *,ado_mixer_delement_t *,ado_mixer_delement_t *,ado_mixer_delement_t *);
extern void ado_mixer_set_reset_func(ado_mixer_t *,int32_t (*)(MIXER_CONTEXT_T *));
extern void ado_mixer_set_destroy_func(ado_mixer_t *,int32_t (*)(MIXER_CONTEXT_T *));
#endif
