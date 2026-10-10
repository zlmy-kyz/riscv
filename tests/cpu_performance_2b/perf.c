#include "bsp.h"
#include "perf.h"
void perf_dump(void) {
    volatile uint32_t *r=(volatile uint32_t *)0x10000100u;
    static const char *names[]={"cycles","instret","if_stall_cycles","mem_stall_cycles",
        "branch_flush_cycles","control_redirect_cycles","control_hold_cycles",
        "load_use_cycles","other_cycles","ddr_transactions","branch_redirects",
        "ddr_ar_commands","ddr_aw_commands"};
    uint32_t state=r[1]&3u;
    printf("PERF2B version=%u state=%u start=%u stop=%u\n",
        (unsigned)(r[0]&255u),(unsigned)state,
        (unsigned)r[5],(unsigned)r[6]);
    if(state!=3u) { printf("ERROR! PERF2B snapshot is not frozen\n"); return; }
    for(unsigned i=0;i<13;i++) {
        uint32_t lo=r[16+i*2],hi=r[17+i*2];
        printf("PERF2B %s=%08x%08x\n",names[i],(unsigned)hi,(unsigned)lo);
    }
    printf("PERF2B_DONE\n");
}
