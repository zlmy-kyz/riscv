#include "uart_echo.h"

/* Infinite, byte-exact polling echo. No banner, newline conversion or IRQ. */
volatile uint32_t echo_count;
volatile uint32_t echo_error;
int main(void)
{
    UART_CONTROL = (1u << 9) | 3u; /* Disable RX IRQ and clear sticky errors. */
    for (;;) {
        if (UART_STATUS & UART_ERRORS) {
            echo_error = UART_STATUS & UART_ERRORS;
            for (;;) {} /* Preserve diagnostic evidence until reset. */
        }
        if (UART_STATUS & (1u << 2)) {
            uint8_t byte = uart_getchar();
            uart_putchar(byte);
            ++echo_count;
        }
    }
}
