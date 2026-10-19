#include "bsp.h"
#include "perf.h"

/* Independent PERF27 image: never linked into the frozen 13-counter BINs. */
static const char *const names[] = {
    "cycles", "instret", "if_stall_cycles", "mem_stall_cycles",
    "branch_flush_cycles", "control_redirect_cycles", "control_hold_cycles",
    "load_use_cycles", "other_cycles", "ddr_transactions", "branch_redirects",
    "ddr_ar_commands", "ddr_aw_commands", "icache_requests", "icache_hits",
    "icache_misses", "dcache_read_requests", "dcache_read_hits", "dcache_read_misses",
    "icache_miss_wait_cycles", "dcache_read_miss_wait_cycles", "write_buffer_block_cycles",
    "old_i_block_cycles", "ex_branch_mem_wait_cycles", "other_with_retire_cycles",
    "target_buffer_match", "target_response_match"
};
static uint64_t counts[27];

static uint64_t read64(volatile uint32_t *p) {
    uint32_t lo = p[0];
    uint32_t hi = p[1];
    return ((uint64_t)hi << 32) | lo;
}
static void failed(unsigned code) {
    printf("PERF27_FAILED code=%u\nPERF2B_DONE\n", code);
}
static void rate(const char *name, unsigned enabled, uint64_t hits, uint64_t misses) {
    /* All six cache counters were checked <= cycles < 2^32, so this scale
       and the sum cannot overflow uint64_t. Printing is outside the ROI. */
    if (!enabled || hits + misses == 0)
        printf("PERF27 %s=NA\n", name);
    else
        printf("PERF27 %s=%u\n", name, (unsigned)((hits * 10000u) / (hits + misses)));
}
void perf_dump(void) {
    volatile uint32_t *r = (volatile uint32_t *)0x10000100u;
    uint32_t cache_status, diag_status;
    if (r[0] != 0x50524601u || (r[1] & 3u) != 3u) { failed(1); return; }
    if (r[8] != 0x43414301u || r[10] != 6u ||
        r[12] != 0x44494101u || r[14] != 8u) { failed(2); return; }
    uint32_t begin = timer_cycles();
    do {
        cache_status = r[9];
        diag_status = r[13];
        if ((cache_status & 8u) && (diag_status & 8u)) break;
        if ((uint32_t)(timer_cycles() - begin) >= CLOCKS_PER_SEC / 2u) {
            failed(3); return;
        }
    } while (1);
    if ((cache_status & ~15u) || (diag_status & ~11u)) { failed(4); return; }
    for (unsigned i = 0; i < 13; ++i) counts[i] = read64(r + 16 + 2*i);
    for (unsigned i = 0; i < 6; ++i) counts[13+i] = read64(r + 64 + 2*i);
    for (unsigned i = 0; i < 8; ++i) counts[19+i] = read64(r + 96 + 2*i);
    if (counts[0] == 0 || counts[0] > 0xffffffffu) { failed(5); return; }
    for (unsigned i = 13; i < 27; ++i)
        if (counts[i] > counts[0]) { failed(6); return; }
    if (counts[13] != counts[14] + counts[15] ||
        counts[16] != counts[17] + counts[18]) { failed(7); return; }
    printf("PERF2B version=1 state=3 start=%u stop=%u\n", (unsigned)r[5], (unsigned)r[6]);
    for (unsigned i = 0; i < 13; ++i)
        printf("PERF2B %s=%08x%08x\n", names[i], (unsigned)(counts[i] >> 32), (unsigned)counts[i]);
    printf("PERF27 version=1 count=27 clock_hz=%u\n", (unsigned)CLOCKS_PER_SEC);
    printf("PERF27 cache_id=43414301 cache_status=%08x cache_count=6 diag_id=44494101 diag_status=%08x diag_count=8\n",
           (unsigned)cache_status, (unsigned)diag_status);
    for (unsigned i = 13; i < 27; ++i)
        printf("PERF27 %s=%08x%08x\n", names[i], (unsigned)(counts[i] >> 32), (unsigned)counts[i]);
    rate("icache_hit_rate_bp", (cache_status & 3u) == 3u, counts[14], counts[15]);
    rate("dcache_read_hit_rate_bp", (cache_status & 5u) == 5u, counts[17], counts[18]);
    printf("PERF27_DONE\nPERF2B_DONE\n");
}
