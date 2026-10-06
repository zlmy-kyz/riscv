#include <stdint.h>
#include "uart_printf.h"

volatile int uart_result;

int main(void)
{
    volatile uint32_t *const test_status = (volatile uint32_t *)0x10000010u;
    *test_status = 1; /* RUN */
    volatile int a = 10;
    volatile int b = 20;
    volatile int c = a + b;

    uart_result = c;
    int printed = printf("%d\r\n", c);
    uart_flush(); /* Complete the final stop bit before reporting PASS. */
    *test_status = (c == 30 && printed == 4) ? 2u : 3u;
    __asm__ volatile (".global c_done\nc_done:\nj c_done");
    return 0;
}
