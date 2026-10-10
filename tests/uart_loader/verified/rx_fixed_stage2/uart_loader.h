#ifndef UART_LOADER_H
#define UART_LOADER_H
#include <stdint.h>
enum {
    LOADER_ACK = 0, LOADER_CRC_ERROR = 0x8001,
    LOADER_ADDRESS_ERROR = 0x8002, LOADER_LENGTH_ERROR = 0x8003,
    LOADER_TIMEOUT = 0x8004, LOADER_UART_ERROR = 0x8005,
    LOADER_VERSION_ERROR = 0x8006, LOADER_COMMAND_ERROR = 0x8007,
    LOADER_STATE_ERROR = 0x8008, LOADER_SEQUENCE_ERROR = 0x8009,
    LOADER_DATA_ERROR = 0x800A, LOADER_RX_TEST = 0x10, LOADER_TEST_LENGTH = 64
};
extern volatile uint32_t loader_ready, loader_ping_count, loader_nack_count;
extern volatile uint32_t loader_rx_count, loader_last_seq, loader_boot_error;
extern volatile uint32_t loader_recovering;
extern volatile uint32_t loader_test_count, loader_test_bytes, loader_test_crc;
extern volatile uint32_t loader_bss_probe[8];
extern volatile uint32_t loader_trap_cause, loader_trap_pc, loader_trap_value;
void loader_ping_loop(void);
#endif
