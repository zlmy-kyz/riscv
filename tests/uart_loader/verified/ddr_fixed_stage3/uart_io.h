#ifndef LOADER_UART_IO_H
#define LOADER_UART_IO_H
#include <stdint.h>
#define UART_STATUS (*(volatile uint32_t *)0x10001008u)
#define UART_CONTROL (*(volatile uint32_t *)0x1000100Cu)
#define UART_ERRORS 0x30u
#define LOADER_TIMEOUT_CYCLES 9375000u /* 100 ms at configured 93.75 MHz */
enum { UART_OK = 0, UART_TIMEOUT = -1, UART_ERROR = -2 };
uint32_t loader_cycle(void);
int uart_read_byte(uint8_t *value, int timed);
int uart_write_byte(uint8_t value);
void uart_recover(void);
#endif
