#ifndef CPU_PERF_2B_H
#define CPU_PERF_2B_H
#include <stdint.h>
/* ARM and configuration are outside the measured [CYCLE start, CYCLE stop). */
static inline void perf_arm_timer_pair(void) {
    volatile uint32_t *r=(volatile uint32_t *)0x10000100u;
    r[2]=2; r[3]=0; r[4]=0; r[2]=1;
}
void perf_dump(void);
#endif
