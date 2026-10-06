#ifndef UART_PRINTF_H
#define UART_PRINTF_H

#include <stdio.h>

/* This freestanding printf supports literal text, %d and %% only. */
void uart_flush(void);

#endif
