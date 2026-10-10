#include "uart_io.h"
#include "uart_loader.h"
volatile uint32_t loader_uart_error_status;
#define RX_DATA (*(volatile uint8_t *)0x10001004u)
#define TX_DATA (*(volatile uint8_t *)0x10001000u)
uint32_t loader_cycle(void) { return *(volatile uint32_t *)0x10000008u; }
int uart_read_byte(uint8_t *value, int timed)
{
    uint32_t start = loader_cycle();
    for (;;) {
        uint32_t status = UART_STATUS;
        if (status & UART_ERRORS) {
            /* Snapshot real sticky bits before recovery W1C, never inject flags. */
            loader_uart_error_status = status & UART_ERRORS;
            return UART_ERROR;
        }
        if (status & 4u) { *value = RX_DATA; return UART_OK; }
        if (timed && (uint32_t)(loader_cycle() - start) >= LOADER_TIMEOUT_CYCLES)
            return UART_TIMEOUT;
        if (loader_session_expired()) return UART_TIMEOUT;
    }
}
int uart_write_byte(uint8_t value)
{
    uint32_t start = loader_cycle();
    while (!(UART_STATUS & 1u)) {
        if ((uint32_t)(loader_cycle() - start) >= LOADER_TIMEOUT_CYCLES)
            return UART_TIMEOUT;
    }
    TX_DATA = value;
    return UART_OK;
}
void uart_recover(void)
{
    uint32_t idle = loader_cycle();
    /* A malformed frame cannot execute bytes embedded in its payload. */
    for (;;) {
        uint32_t status = UART_STATUS;
        if (status & 4u) { (void)RX_DATA; idle = loader_cycle(); }
        if (status & UART_ERRORS) {
            UART_CONTROL = (1u << 9) | 3u;
            idle = loader_cycle();
        }
        if ((uint32_t)(loader_cycle() - idle) >= LOADER_TIMEOUT_CYCLES) return;
    }
}
