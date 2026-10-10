#include "uart_loader.h"
#include "uart_io.h"
#include "crc32.h"
#include "ddr_test.h"

volatile uint32_t loader_ready, loader_ping_count, loader_nack_count;
volatile uint32_t loader_rx_count, loader_last_seq, loader_boot_error;
volatile uint32_t loader_recovering;
volatile uint32_t loader_test_count, loader_test_bytes, loader_test_crc;
volatile uint32_t loader_ddr_count, loader_ddr_bytes, loader_ddr_status;
volatile uint32_t loader_bss_probe[8];
volatile uint32_t loader_trap_cause, loader_trap_pc, loader_trap_value;
static uint32_t have_sequence, last_command;
static uint8_t rx_buffer[256] __attribute__((section(".rx_buffer"), aligned(4)));
static const uint8_t magic[4] = {'R', 'V', 'L', 'D'};

static uint32_t get32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static void put32(uint8_t *p, uint32_t v)
{
    for (unsigned i = 0; i < 4; ++i) p[i] = (uint8_t)(v >> (8u * i));
}
/* A diagnostic command, not LOAD: only this 64-byte pattern is accepted.
   Embedded RVLD, zero, FF and control bytes must remain ordinary payload. */
static int fixed_data_matches(const uint8_t *data)
{
    static const uint8_t prefix[16] = {0, 255, 0x55, 0xAA, 'R', 'V', 'L', 'D',
                                      10, 13, 128, 127, 254, 1, 2, 0};
    uint32_t different = 0;
    for (unsigned i = 0; i < LOADER_TEST_LENGTH; ++i) {
        uint8_t expected = i < 16 ? prefix[i] : (uint8_t)(i * 37u + 11u);
        different |= data[i] ^ expected;
    }
    return different == 0;
}
static int respond(uint32_t seq, uint32_t cmd, uint32_t status, uint32_t accepted)
{
    uint8_t frame[60];
    for (unsigned i = 0; i < sizeof frame; ++i) frame[i] = 0;
    for (unsigned i = 0; i < 4; ++i) frame[i] = magic[i];
    frame[4] = 1; frame[5] = 0x80;
    put32(frame + 8, seq);
    put32(frame + 12, cmd == LOADER_RX_TEST ? 0 : 0x40000000u);
    put32(frame + 16, 24);
    put32(frame + 20, 61440);
    put32(frame + 28, loader_crc32(frame, 28));
    put32(frame + 32, status);
    put32(frame + 36, cmd);
    put32(frame + 40, accepted);
    /* accepted is this fixed diagnostic only; DDR CRC stays zero.
       Capability 3 advertises CRC and ROM residency, NOT LOAD or RUN. */
    put32(frame + 48, 3);
    put32(frame + 52, 256);
    put32(frame + 56, loader_crc32(frame + 32, 24));
    for (unsigned i = 0; i < sizeof frame; ++i)
        if (uart_write_byte(frame[i]) != UART_OK) return UART_TIMEOUT;
    return UART_OK;
}
static int receive_header(void)
{
    unsigned matched = 0;
    uint8_t byte;
    while (matched < 4) {
        int result = uart_read_byte(&byte, matched != 0);
        if (result != UART_OK) return result;
        ++loader_rx_count;
        if (byte == magic[matched]) ++matched;
        else matched = byte == magic[0] ? 1u : 0u;
    }
    for (unsigned i = 0; i < 4; ++i) rx_buffer[i] = magic[i];
    for (unsigned i = 4; i < 32; ++i) {
        int result = uart_read_byte(rx_buffer + i, 1);
        if (result != UART_OK) return result;
        ++loader_rx_count;
    }
    return UART_OK;
}
void loader_ping_loop(void)
{
    for (;;) {
        int result = receive_header();
        uint32_t status = LOADER_ACK, seq = 0, cmd = 0, length = 0, accepted = 0;
        int recover = 0;
        if (result != UART_OK) {
            status = result == UART_ERROR ? LOADER_UART_ERROR : LOADER_TIMEOUT;
            recover = 1;
        } else if (loader_crc32(rx_buffer, 28) != get32(rx_buffer + 28)) {
            status = LOADER_CRC_ERROR; recover = 1;
        } else {
            seq = get32(rx_buffer + 8); cmd = rx_buffer[5];
            length = get32(rx_buffer + 16);
            if (rx_buffer[4] != 1) status = LOADER_VERSION_ERROR;
            else if ((cmd != 1 && cmd != LOADER_RX_TEST && cmd != LOADER_DDR_TEST) || rx_buffer[6] || rx_buffer[7]) status = LOADER_COMMAND_ERROR;
            else if (get32(rx_buffer + 12) != (cmd == LOADER_DDR_TEST ? LOADER_DDR_TEST_BASE : 0)) status = LOADER_ADDRESS_ERROR;
            else if (length != (cmd == 1 ? 0 : LOADER_TEST_LENGTH) || get32(rx_buffer + 20)) status = LOADER_LENGTH_ERROR;
            else if (get32(rx_buffer + 24)) status = LOADER_STATE_ERROR;
            if (status != LOADER_ACK) recover = 1;
            else {
                /* length has been validated before any buffer write. */
                for (unsigned i = 0; i < length + 4; ++i) {
                    result = uart_read_byte(rx_buffer + 32 + i, 1);
                    if (result != UART_OK) break;
                    ++loader_rx_count;
                }
                if (result != UART_OK) {
                    status = result == UART_ERROR ? LOADER_UART_ERROR : LOADER_TIMEOUT;
                    recover = 1;
                } else if (loader_crc32(rx_buffer + 32, length) != get32(rx_buffer + 32 + length)) {
                    status = LOADER_CRC_ERROR; recover = 1;
                } else if (cmd != 1 && !fixed_data_matches(rx_buffer + 32)) {
                    status = LOADER_DATA_ERROR; recover = 1;
                } else if (have_sequence && (seq < loader_last_seq ||
                           (seq == loader_last_seq && cmd != last_command))) {
                    status = LOADER_SEQUENCE_ERROR;
                } else {
                    int fresh = !have_sequence || seq != loader_last_seq;
                    if (cmd == LOADER_DDR_TEST && fresh) {
                        loader_ddr_status = ddr_fixed_compare(rx_buffer + 32, rx_buffer + 128)
                                            ? LOADER_ACK : LOADER_DDR_ERROR;
                        status = loader_ddr_status;
                    }
                    if (status == LOADER_ACK && cmd != 1) accepted = LOADER_TEST_LENGTH;
                    if (status == LOADER_ACK && fresh) {
                        loader_last_seq = seq; last_command = cmd; have_sequence = 1;
                        if (cmd == 1) ++loader_ping_count;
                        else if (cmd == LOADER_RX_TEST) {
                            ++loader_test_count; loader_test_bytes += LOADER_TEST_LENGTH;
                            loader_test_crc = loader_crc32(rx_buffer + 32, length);
                        } else {
                            ++loader_ddr_count; loader_ddr_bytes += LOADER_TEST_LENGTH;
                        }
                    }
                }
            }
        }
        if (status != LOADER_ACK) ++loader_nack_count;
        /* A rejected header can still have a body arriving at full rate.
           Drain before the blocking TX response, otherwise the 16-byte FIFO
           overflows while NACK is being sent. */
        if (recover) {
            loader_recovering = 1;
            uart_recover();
            loader_recovering = 0;
        }
        if (respond(seq, cmd, status, accepted) != UART_OK) {
            loader_recovering = 1;
            uart_recover();
            loader_recovering = 0;
        }
    }
}
