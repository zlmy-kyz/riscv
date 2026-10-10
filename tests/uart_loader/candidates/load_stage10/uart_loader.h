#ifndef UART_LOADER_H
#define UART_LOADER_H
#include <stdint.h>
enum {
    LOADER_ACK = 0, LOADER_READY = 1, LOADER_LOAD = 2, LOADER_CRC_ERROR = 0x8001,
    LOADER_ADDRESS_ERROR = 0x8002, LOADER_LENGTH_ERROR = 0x8003,
    LOADER_TIMEOUT = 0x8004, LOADER_UART_ERROR = 0x8005,
    LOADER_VERSION_ERROR = 0x8006, LOADER_COMMAND_ERROR = 0x8007,
    LOADER_STATE_ERROR = 0x8008, LOADER_SEQUENCE_ERROR = 0x8009,
    LOADER_DATA_ERROR = 0x800A, LOADER_DDR_ERROR = 0x800B,
    LOADER_RX_TEST = 0x10, LOADER_DDR_TEST = 0x11, LOADER_DDR_CRC_TEST = 0x12,
    LOADER_RANDOM_WRITE = 0x13, LOADER_RANDOM_CRC = 0x14,
    LOADER_RANDOM_MAX = 61440, LOADER_RANDOM_CHUNK = 256,
    LOADER_TEST_LENGTH = 64
};
extern volatile uint32_t loader_ready, loader_ping_count, loader_nack_count;
extern volatile uint32_t loader_rx_count, loader_last_seq, loader_boot_error;
extern volatile uint32_t loader_recovering;
extern volatile uint32_t loader_test_count, loader_test_bytes, loader_test_crc;
extern volatile uint32_t loader_ddr_count, loader_ddr_bytes, loader_ddr_status;
extern volatile uint32_t loader_crc_count, loader_crc_reads, loader_crc_actual;
extern volatile uint32_t loader_crc_expected, loader_crc_status;
extern volatile uint32_t loader_bss_probe[8];
extern volatile uint32_t loader_trap_cause, loader_trap_pc, loader_trap_value;
extern volatile uint32_t loader_random_writes, loader_random_bytes, loader_random_reads;
void loader_ping_loop(void);
extern volatile uint32_t loader_image_active, loader_image_complete;
extern volatile uint32_t loader_image_total, loader_image_received, loader_image_crc;
int loader_session_expired(void);
#endif
