#ifndef UART_ECHO_H
#define UART_ECHO_H
#include <stdint.h>
#define UART_TX_DATA (*(volatile uint8_t *)0x10001000u)
#define UART_RX_DATA (*(volatile uint8_t *)0x10001004u)
#define UART_STATUS (*(volatile uint32_t *)0x10001008u)
#define UART_CONTROL (*(volatile uint32_t *)0x1000100cu)
#define UART_ERRORS ((1u << 4) | (1u << 5))
uint8_t uart_getchar(void);
void uart_putchar(uint8_t value);
#endif
