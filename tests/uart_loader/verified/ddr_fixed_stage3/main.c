#include "uart_loader.h"
#include "uart_io.h"
#include "crc32.h"

/* Volatile accesses prove constants are fetched through the RAM data bus. */
const uint32_t loader_constant_probe[4] = {0x13579BDFu, 0x2468ACE0u, 0x00FF55AAu, 0xA55A3CC3u};
static const uint8_t check_string[] = "123456789";
volatile uint32_t loader_diagnostics[4] __attribute__((section(".diagnostics")));

int main(void)
{
    uint32_t observed = 0;
    for (unsigned i = 0; i < 8; ++i)
        if (loader_bss_probe[i] != 0) loader_boot_error |= 1u;
    for (unsigned i = 0; i < 4; ++i)
        observed ^= ((const volatile uint32_t *)loader_constant_probe)[i];
    loader_diagnostics[0] = observed;
    loader_diagnostics[1] = loader_crc32(check_string, 9);
    loader_diagnostics[2] = loader_crc32(check_string, 0);
    if (observed != 0x929A5E56u) loader_boot_error |= 2u;
    if (loader_diagnostics[1] != 0xCBF43926u || loader_diagnostics[2] != 0)
        loader_boot_error |= 4u;
    loader_diagnostics[3] = loader_boot_error;
    if (loader_boot_error) for (;;) {}
    for (unsigned i = 0; i < 8; ++i) loader_bss_probe[i] = 0xB5500000u + i;
    UART_CONTROL = (1u << 9) | 3u;
    loader_ready = 0x52454144u;
    loader_ping_loop();
}
