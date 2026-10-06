#include "uart_echo.h"

uint8_t uart_getchar(void)
{
    while ((UART_STATUS & (1u << 2)) == 0) {}
    return UART_RX_DATA;
}

void uart_putchar(uint8_t value)
{
    while ((UART_STATUS & 1u) == 0) {}
    UART_TX_DATA = value;
}
