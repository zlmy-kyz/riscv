/* Independent C acceptance payload. All peripherals use the existing MMIO ABI. */
#include <stdint.h>

#ifndef INJECT_FAILURE
#define INJECT_FAILURE 0
#endif

volatile uint32_t initialized_a = 10;
volatile uint32_t initialized_b = 20;
volatile uint32_t bss_probe[5];
volatile uint32_t results[3];

int main(void)
{
    volatile uint32_t *const test_status = (volatile uint32_t *)0x10000010u;
    uint32_t ok = initialized_a == 10 && initialized_b == 20;
    for (uint32_t i = 0; i < 5; ++i)
        ok &= bss_probe[i] == 0;
    for (uint32_t i = 0; i < 3; ++i)
        ok &= results[i] == 0;
    *test_status = 1; /* RUN is required before a final result. */
    volatile uint32_t a = initialized_a;
    volatile uint32_t b = initialized_b;
    volatile uint32_t c = a + b;
    results[0] = a;
    results[1] = b;
    results[2] = c;
    /* Leave RUN visible long enough for the simulation to check its blink rate. */
    for (volatile uint32_t delay = 0; delay < 32; ++delay) {}
    ok &= c == (INJECT_FAILURE ? 31u : 30u);
    *test_status = ok ? 2u : 3u;
    __asm__ volatile (".global c_done\nc_done:\nj c_done");
    return 0;
}
