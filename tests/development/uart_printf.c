#include "uart_printf.h"
#include <stdarg.h>
#include <stdint.h>

#define UART_TX_DATA (*(volatile uint8_t *)0x10001000u)
#define UART_STATUS  (*(volatile uint32_t *)0x10001008u)

void uart_flush(void)
{
    while ((UART_STATUS & 1u) == 0) {}
}

static void uart_putchar(char value)
{
    uart_flush();
    UART_TX_DATA = (uint8_t)value;
}

static int print_decimal(int value)
{
    static const uint32_t places[] = {
        1000000000u, 100000000u, 10000000u, 1000000u, 100000u,
        10000u, 1000u, 100u, 10u, 1u
    };
    uint32_t magnitude = (uint32_t)value;
    int count = 0, started = 0;
    if (value < 0) {
        uart_putchar('-');
        ++count;
        magnitude = 0u - magnitude; /* Also valid for INT_MIN. */
    }
    /* Repeated subtraction avoids division and any dependency on M instructions. */
    for (unsigned i = 0; i < 10; ++i) {
        unsigned digit = 0;
        while (magnitude >= places[i]) {
            magnitude -= places[i];
            ++digit;
        }
        if (digit || started || i == 9) {
            uart_putchar((char)('0' + digit));
            started = 1;
            ++count;
        }
    }
    return count;
}

int printf(const char *format, ...)
{
    va_list args;
    va_start(args, format);
    int count = 0;
    while (*format) {
        if (*format != '%') {
            uart_putchar(*format++);
            ++count;
        } else {
            ++format;
            if (*format == 'd') {
                count += print_decimal(va_arg(args, int));
            } else if (*format == '%') {
                uart_putchar('%');
                ++count;
            } else {
                va_end(args);
                return -1; /* Unsupported conversion, width or trailing percent. */
            }
            ++format;
        }
    }
    va_end(args);
    return count;
}
