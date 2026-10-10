#include <stdint.h>
volatile uint32_t app_data[16] = {
    0x13579BDFu,0x2468ACE0u,0x00FF55AAu,0xA55A3CC3u,
    0x52564C44u,0x000A0DFFu,0x11223344u,0x55667788u,
    1,2,3,4,5,6,7,8
};
volatile uint32_t app_bss[24];
const uint8_t image_tail[3] __attribute__((section(".image_tail"),used)) = {0x5a,0xc3,0x7e};
static void print(const char *text)
{
    while (*text) {
        while (!(*(volatile uint32_t *)0x10001008u & 1u)) {}
        *(volatile uint8_t *)0x10001000u = (uint8_t)*text++;
    }
}
int main(void)
{
    uint32_t error = 0;
    for (unsigned i = 0; i < 24; ++i) error |= app_bss[i];
    if (app_data[0] != 0x13579BDFu || app_data[3] != 0xA55A3CC3u || app_data[15] != 8u) error |= 1u;
    app_bss[23] = app_data[0] ^ app_data[3];
    print(error ? "HELLO_LOADER_DATA_BSS_FAIL\r\n" : "Hello World\r\n");
    for (;;) {}
}
