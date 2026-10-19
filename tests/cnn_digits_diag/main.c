/* One actual Camera/PP/CNN job, nontrained diagnostic. CN01 RGB96 export. */
#include <stdint.h>
#include "pp01_wire.h"


#ifdef PP_NATIVE
uint32_t diag_read(uint32_t address);
void diag_write(uint32_t address, uint32_t value);
void diag_halt(void) __attribute__((noreturn));
#define R32(a) diag_read(a)
#define W32(a,v) diag_write(a,v)
#else
#define R32(a) (*(volatile uint32_t *)(a))
#define W32(a,v) (*(volatile uint32_t *)(a)=(v))
#endif

#define CAM   0x10002000u
#define PP    0x10003000u
#define UART  0x10001000u
#define CYCLE 0x10000008u
#define TEST_STATUS 0x10000010u
#define HZ    93750000u

#define SRC_A 0x41000000u
#define SRC_B 0x41200000u
#define SRC_BYTES 1843200u
#define SRC_PIXELS 921600u
#define SRC_BEATS 57600u
#define OUT_BASE 0x42000000u
#define OUT_BYTES 27648u
#define OUT_PIXELS 9216u
#define OUT_BEATS 864u
#define OUT_SIZE 0x00600060u
#define CHUNK 1024u
#define GROUPS 1u
#define MAX_LEDGER 16u

/* Fixed upper bounds, decided before the run and never extended at runtime. */
#define TX_LIMIT       (5ull * HZ)    /* one UART TX byte must become sendable  */
#define ACK_LIMIT      (5ull * HZ)    /* PC 'K' for one complete packet        */
#define CMD_LIMIT      (30ull * HZ)   /* command the PC sends without a user   */
#define CMD_LIMIT_USER (600ull * HZ)  /* group-2 command after the scene change*/
#define CONFIG_LIMIT   (5ull * HZ)    /* SCCB configuration (CONFIG_DONE)      */
#define READY_LIMIT    (5ull * HZ)    /* Camera ready frame / STOP drain       */
#define PP_LIMIT       (5ull * HZ)    /* normal PP DONE                        */
#define CPU_LIMIT      (20ull * HZ)   /* CPU reference / CRC verification      */

/* Camera ABI2 (0x10002000), see doc/camera/OV5640双缓冲所有权与CPU并发读取. */
#define CAM_CTRL        0x04u
#define CAM_STATUS      0x08u
#define CAM_FRAME_BASE  0x0cu
#define CAM_FRAME_BYTES 0x10u
#define CAM_FRAME_SEQ   0x14u
#define CAM_PIXELS      0x18u
#define CAM_ERROR       0x1cu
#define CAM_SENSOR      0x20u
#define CAM_BEATS       0x24u
#define CAM_CRC         0x28u
#define CAM_SELECT      0x2cu
#define CAM_BUFSTATE    0x30u
#define CAM_GLOBAL_SEQ  0x34u
#define CAM_TOKEN       0x38u
#define CAM_OK_ID       0x43414d02u

#define CAM_CMD_STREAM_START 0x08u
#define CAM_CMD_STREAM_STOP  0x10u
#define CAM_CMD_CLAIM        0x20u
#define CAM_CMD_RELEASE      0x40u

/* Preprocess MMIO (0x10003000), see doc/camera/OV5640预处理96RGB888与DDR接口. */
#define PP_ID         0x00u
#define PP_CTRL       0x04u
#define PP_STATUS     0x08u
#define PP_SOURCE_BUF 0x0cu
#define PP_EXPECTED   0x10u
#define PP_RESULT_SEQ 0x14u
#define PP_OUT_BASE   0x18u
#define PP_OUT_BYTES  0x1cu
#define PP_OUT_CRC    0x20u
#define PP_ERROR      0x24u
#define PP_READS      0x28u
#define PP_WRITES     0x2cu
#define PP_PRODUCED   0x30u
#define PP_CYCLES     0x34u
#define PP_OUT_SIZE   0x38u
#define PP_RESULT_BUF 0x3cu
#define PP_OK_ID      0x50525001u

#define UART_TX_DATA 0x00u
#define UART_RX_DATA 0x04u
#define UART_STATUS  0x08u

/* ---------------------------------------------------------------- diagnostics */
volatile uint32_t boot_cookie = 0x50505531u; /* keeps .data non-empty, checked */
static uint8_t payload[CHUNK];
static uint8_t packet[32];
static uint8_t failing;
static uint64_t elapsed, previous_tick, program_start;

static uint32_t group_no, cur_buf, cur_seq, cur_pp_crc;
static uint32_t ledger_seq[MAX_LEDGER], ledger_buf[MAX_LEDGER];
static uint32_t ledger_n, target_claims, discard_claims, last_discard;

static void halt(void) __attribute__((noreturn));
static void halt(void) {
#ifdef PP_NATIVE
    diag_halt();
#else
    for (;;) { }
#endif
}
static void fail(const char *why) __attribute__((noreturn));

static uint64_t ticks(void)
{
    uint32_t value = R32(CYCLE);
    elapsed += (uint32_t)(value - previous_tick);
    previous_tick = value;
    return elapsed;
}

static void uart_put(uint8_t byte)
{
    uint64_t start = ticks();
    while (!(R32(UART + UART_STATUS) & 1u)) {
        if (ticks() - start >= TX_LIMIT) {
            if (failing) {
                return; /* never recurse while reporting a failure */
            }
            fail("UART_TX_DEADLINE");
        }
    }
#ifdef PP_NATIVE
    diag_write(UART + UART_TX_DATA, byte);
#else
    *(volatile uint8_t *)(UART + UART_TX_DATA) = byte;
#endif
}

static void text(const char *s) { while (*s) { uart_put((uint8_t)*s++); } }

static void hex(uint32_t value)
{
    for (int i = 7; i >= 0; i--) {
        uart_put((uint8_t)"0123456789abcdef"[(value >> (i * 4)) & 15u]);
    }
}

static void dec(uint64_t value)
{
    char buf[21];
    unsigned n = 20;
    buf[n] = '\0';
    do {
        buf[--n] = (char)('0' + (int)(value % 10u));
        value /= 10u;
    } while (value);
    text(buf + n);
}

static void hfield(const char *key, uint32_t value) { text(key); hex(value); }

static void fail(const char *why)
{
    failing = 1;
    text("CNN_FAIL REASON=");
    text(why);
    text(" GROUP=");
    dec(group_no);
    text(" BUF=");
    dec(cur_buf);
    text(" SEQ=");
    dec(cur_seq);
    text(" CLAIMS=");
    dec(ledger_n);
    text(" TARGET_CLAIMS=");
    dec(target_claims);
    text(" DISCARD_CLAIMS=");
    dec(discard_claims);
    text(" LAST_DISCARD=");
    dec(last_discard);
    hfield(" CAM_STATUS=", R32(CAM + CAM_STATUS));
    hfield(" CAM_ERR=", R32(CAM + CAM_ERROR));
    hfield(" CAM_BUFSTATE=", R32(CAM + CAM_BUFSTATE));
    hfield(" CAM_GLOBAL_SEQ=", R32(CAM + CAM_GLOBAL_SEQ));
    hfield(" PP_STATUS=", R32(PP + PP_STATUS));
    hfield(" PP_ERR=", R32(PP + PP_ERROR));
    hfield(" UART_STATUS=", R32(UART + UART_STATUS));
    hfield(" CNN_STATUS=",R32(0x10004008u));hfield(" CNN_ERROR=",R32(0x1000403cu));
    text(" LOAD_COUNT=");dec(R32(0x10004018u));hfield(" MODEL_CRC=",R32(0x10004014u));hfield(" MODEL_ID=",R32(0x1000400cu));
    text(" ELAPSED_TICKS=");
    dec(ticks() - program_start);
    text("\n");
    W32(TEST_STATUS, 3u);
    halt();
}

void camera_trap(uint32_t cause, uint32_t pc, uint32_t value)
{
    text("CNN_TRAP CAUSE=");
    hex(cause);
    text(" PC=");
    hex(pc);
    text(" TVAL=");
    hex(value);
    text("\n");
    fail("CPU_TRAP");
}

/* ------------------------------------------------------------------- CRC32 */
/* Reflected IEEE CRC32 and the CN01 byte layout live in pp01_wire.c, which is
 * compiled unchanged into the host check program. */

/* --------------------------------------------------------------- UART layer */
static void uart_bytes(const uint8_t *p, uint32_t n)
{
    while (n--) {
        uart_put(*p++);
    }
}

static void send_packet(uint32_t kind, uint32_t seq, uint32_t offset, uint32_t length,
                        uint32_t total, uint32_t data_crc)
{
    pp01_build_header(packet, kind, seq, offset, length, total, data_crc);
    uart_bytes(packet, PP01_HEADER_BYTES);
    if (length) {
        uart_bytes(payload, length);
    }
    uint64_t start = ticks();
    for (;;) {
        uint32_t status = R32(UART + UART_STATUS);
        if (status & 0x30u) {
            fail("UART_RX_ERROR");
        }
        if (status & 4u) {
            break;
        }
        if (ticks() - start >= ACK_LIMIT) {
            fail("EXPORT_ACK_TIMEOUT");
        }
    }
    if ((uint8_t)(R32(UART + UART_RX_DATA) & 0xffu) != 0x4bu) {
        fail("EXPORT_ACK_BYTE");
    }
}

static uint8_t wait_command(uint64_t limit)
{
    uint64_t start = ticks();
    for (;;) {
        uint32_t status = R32(UART + UART_STATUS);
        if (status & 0x30u) {
            fail("UART_RX_ERROR");
        }
        if (status & 4u) {
            return (uint8_t)(R32(UART + UART_RX_DATA) & 0xffu);
        }
        if (ticks() - start >= limit) {
            fail("COMMAND_TIMEOUT");
        }
    }
}

/* ---------------------------------------------------------------- DDR blocks */
static void load_words(uint32_t base, uint32_t offset, uint32_t words)
{
    const volatile uint32_t *src = (const volatile uint32_t *)(base + offset);
    for (uint32_t i = 0; i < words; i++) {
        uint32_t w = src[i];
        payload[4u * i] = (uint8_t)w;
        payload[4u * i + 1u] = (uint8_t)(w >> 8);
        payload[4u * i + 2u] = (uint8_t)(w >> 16);
        payload[4u * i + 3u] = (uint8_t)(w >> 24);
    }
}

static uint32_t output_reread(void)
{
    uint32_t c = 0xffffffffu;
    uint64_t start = ticks();
    for (uint32_t off = 0; off < OUT_BYTES; off += CHUNK) {
        load_words(OUT_BASE, off, CHUNK / 4u);
        for (uint32_t i = 0; i < CHUNK; i++) {
            c = pp01_crc_step(c, payload[i]);
        }
        if (ticks() - start >= CPU_LIMIT) {
            fail("CPU_OUTPUT_REREAD_TIMEOUT");
        }
    }
    return pp01_crc_finish(c);
}

/* --------------------------------------------------------------- Camera ABI2 */
static void cam_write(uint32_t offset, uint32_t value) { W32(CAM + offset, value); }

static uint32_t cam_state(uint32_t buf)
{
    return (R32(CAM + CAM_BUFSTATE) >> (2u * buf)) & 3u;
}

static void cam_healthy(void)
{
    uint32_t s = R32(CAM + CAM_STATUS);
    if ((s & 1u) == 0u) {
        fail("CAMERA_CONFIG_LOST");
    }
    if (s & 8u) {
        fail("CAMERA_OVERFLOW");
    }
    if (s & 16u) {
        fail("CAMERA_ERROR");
    }
    if (R32(CAM + CAM_ERROR) != 0u) {
        fail("CAMERA_ERROR_CODE");
    }
}

/* Both buffers FREE, no capture in flight, stream disabled.  BUFFER_STATE bit4
 * (SELECT) is deliberately not part of this check. */
static void cam_idle_state(void)
{
    uint32_t st = R32(CAM + CAM_BUFSTATE);
    if (st & 0x2cfu) {
        fail("CAMERA_NOT_IDLE_FREE");
    }
    if (R32(CAM + CAM_STATUS) & 2u) {
        fail("CAMERA_BUSY");
    }
    if (R32(CAM + CAM_STATUS) & 0x40u) {
        fail("CAMERA_STREAM_ENABLED");
    }
}

static void cam_claim(uint32_t buf, uint32_t seq)
{
    cam_write(CAM_SELECT, buf);
    cam_write(CAM_TOKEN, seq);
    if (cam_state(buf) != 2u) {
        fail("CLAIM_STATE");
    }
    if (R32(CAM + CAM_FRAME_SEQ) != seq) {
        fail("CLAIM_SEQ");
    }
    cam_write(CAM_CTRL, CAM_CMD_CLAIM);
    if (cam_state(buf) != 3u) {
        fail("CLAIM_NOT_ACCEPTED");
    }
}

static void cam_release(uint32_t buf, uint32_t seq)
{
    cam_write(CAM_SELECT, buf);
    cam_write(CAM_TOKEN, seq);
    if (cam_state(buf) != 3u) {
        fail("RELEASE_STATE");
    }
    if (R32(CAM + CAM_FRAME_SEQ) != seq) {
        fail("RELEASE_SEQ");
    }
    cam_write(CAM_CTRL, CAM_CMD_RELEASE);
    if (cam_state(buf) == 3u) {
        fail("RELEASE_NOT_ACCEPTED");
    }
}

static void ledger_add(uint32_t buf, uint32_t seq, uint32_t target)
{
    if (ledger_n >= MAX_LEDGER) {
        fail("LEDGER_OVERFLOW");
    }
    for (uint32_t i = 0; i < ledger_n; i++) {
        if (ledger_buf[i] == buf && ledger_seq[i] == seq) {
            fail("LEDGER_DUPLICATE");
        }
    }
    ledger_seq[ledger_n] = seq;
    ledger_buf[ledger_n] = buf;
    ledger_n++;
    if (target) {
        target_claims++;
    } else {
        discard_claims++;
        last_discard = seq;
    }
}

/* Wait for the target READY frame, read its frozen layout/sequence, then claim it
 * with its own token.  No statement here assumes the two groups' SEQ are
 * consecutive: only the per-selection token match is required. */
static uint32_t wait_target(uint32_t buf)
{
    uint64_t start = ticks();
    for (;;) {
        cam_healthy();
        if (cam_state(buf) == 2u) {
            cam_write(CAM_SELECT, buf);
            uint32_t seq = R32(CAM + CAM_FRAME_SEQ);
            if (R32(CAM + CAM_FRAME_BYTES) != SRC_BYTES ||
                R32(CAM + CAM_PIXELS) != SRC_PIXELS ||
                R32(CAM + CAM_BEATS) != SRC_BEATS ||
                R32(CAM + CAM_FRAME_BASE) != (buf ? SRC_B : SRC_A)) {
                fail("SOURCE_LAYOUT");
            }
            cam_claim(buf, seq);
            ledger_add(buf, seq, 1u);
            return seq;
        }
        if (ticks() - start >= READY_LIMIT) {
            fail("TARGET_READY_TIMEOUT");
        }
    }
}

static void stop_and_drain(void)
{
    cam_write(CAM_CTRL, CAM_CMD_STREAM_STOP);
    uint64_t start = ticks();
    for (;;) {
        cam_healthy();
        if (!(R32(CAM + CAM_BUFSTATE) & 0x40u) && !(R32(CAM + CAM_STATUS) & 2u)) {
            break;
        }
        if (ticks() - start >= READY_LIMIT) {
            fail("STOP_DRAIN_TIMEOUT");
        }
    }
}

/* Every non-selected / STOP tail frame is claimed with its own token, recorded
 * as DISCARD in the in-RAM ledger and released; READY is never treated as FREE
 * and is never carried into the next group. */
static void drain_unselected(uint32_t target)
{
    for (uint32_t buf = 0; buf < 2u; buf++) {
        if (buf == target) {
            continue;
        }
        for (;;) {
            cam_healthy();
            if (cam_state(buf) != 2u) {
                break;
            }
            cam_write(CAM_SELECT, buf);
            uint32_t seq = R32(CAM + CAM_FRAME_SEQ);
            if (cam_state(buf) != 2u) {
                fail("DISCARD_STATE");
            }
            cam_claim(buf, seq);
            ledger_add(buf, seq, 0u);
            cam_release(buf, seq);
            if (cam_state(buf) == 3u) {
                fail("DISCARD_NOT_RELEASED");
            }
        }
    }
}

/* ------------------------------------------------------------- preprocessing */
static void pp_start(uint32_t buf, uint32_t seq)
{
    if (R32(PP + PP_STATUS) & 1u) {
        fail("PP_BUSY");
    }
    W32(PP + PP_SOURCE_BUF, buf);
    W32(PP + PP_EXPECTED, seq);
    if (R32(PP + PP_SOURCE_BUF) != buf || R32(PP + PP_EXPECTED) != seq) {
        fail("PP_CONFIG_READBACK");
    }
    W32(PP + PP_CTRL, 1u);
    /* Source lock: the PP is busy and the claimed buffer must stay CPU-owned. */
    if ((R32(PP + PP_STATUS) & 1u) == 0u) {
        fail("PP_NOT_BUSY");
    }
    if (R32(PP + PP_SOURCE_BUF) != buf) {
        fail("PP_ACTIVE_SOURCE");
    }
    if (cam_state(buf) != 3u) {
        fail("SOURCE_LOCK_LOST");
    }
    if (R32(CAM + CAM_ERROR) != 0u || (R32(CAM + CAM_STATUS) & 16u)) {
        fail("SOURCE_LOCK_ERROR");
    }
}

static void pp_wait_done(void)
{
    uint64_t start = ticks();
    for (;;) {
        uint32_t status = R32(PP + PP_STATUS);
        if (status & 4u) {
            fail("PP_ERROR");
        }
        if (status & 2u) {
            break;
        }
        if (ticks() - start >= PP_LIMIT) {
            fail("PP_TIMEOUT");
        }
    }
}

static void pp_check(uint32_t buf, uint32_t seq, uint32_t *pp_crc)
{
    if (R32(PP + PP_STATUS) != 2u) fail("PP_NOT_EXACT_DONE");
    if (R32(PP + PP_RESULT_BUF) != buf) {
        fail("PP_RESULT_BUF");
    }
    if (R32(PP + PP_RESULT_SEQ) != seq) {
        fail("PP_RESULT_SEQ");
    }
    if (R32(PP + PP_OUT_BASE) != OUT_BASE) {
        fail("PP_OUTPUT_BASE");
    }
    if (R32(PP + PP_OUT_BYTES) != OUT_BYTES) {
        fail("PP_OUTPUT_BYTES");
    }
    if (R32(PP + PP_OUT_SIZE) != OUT_SIZE) {
        fail("PP_OUTPUT_SIZE");
    }
    if (R32(PP + PP_READS) != OUT_PIXELS) {
        fail("PP_READ_BEATS");
    }
    if (R32(PP + PP_WRITES) != OUT_BEATS) {
        fail("PP_WRITE_BEATS");
    }
    if (R32(PP + PP_PRODUCED) != OUT_BYTES) {
        fail("PP_PRODUCED_BYTES");
    }
    if (R32(PP + PP_ERROR) != 0u) {
        fail("PP_ERROR_CODE");
    }
    *pp_crc = R32(PP + PP_OUT_CRC);
}


#include "diag.h"
int main(void){
    failing=0;previous_tick=R32(CYCLE);program_start=ticks();W32(TEST_STATUS,1u);
    if(boot_cookie!=0x50505531u)fail("DATA_INIT");
    pp01_crc_init();
    if(R32(CAM)!=CAM_OK_ID || R32(PP)!=PP_OK_ID || R32(0x10004000u)!=0x434e4e01u)fail("DEVICE_ABI_IDS");
    text("CNN_DIAG_APP=1 CONTRACT=digits10_int8_v1 HZ=93750000 DIAGNOSTIC=1 TIMING=PENDING\n");
    cnn_load();uint64_t start=ticks();
    while(!(R32(CAM+CAM_STATUS)&1u)){
        if(R32(CAM+CAM_STATUS)&24u)fail("CAMERA_CONFIG");
        if(ticks()-start>5ull*HZ)fail("CONFIG_TIMEOUT");
    }
    if(R32(CAM+CAM_STATUS)!=1u || R32(CAM+CAM_SENSOR)!=0x5640u || R32(CAM+CAM_GLOBAL_SEQ)!=0u || R32(PP+8)!=0u)fail("FRESH_CAMERA_PP_REQUIRED");
    text("SENSOR_ID=00005640 CONFIG=OK\nCNN_READY\n");
    if(wait_command(CMD_LIMIT)!='G')fail("GO_COMMAND");
    if(wait_command(CMD_LIMIT)!='C')fail("CAPTURE_COMMAND");
    group_no=1;capture_group(0);
    if(wait_command(CMD_LIMIT)!='D')fail("EXPORT_COMMAND");
    export_group();
    if(wait_command(CMD_LIMIT)!='Q')fail("FINISH_COMMAND");
    cam_healthy();cam_idle_state();
    if(R32(PP+8)!=2u || R32(PP+20)!=cur_seq || R32(PP+60)!=cur_buf || R32(CNN+8)!=10u || R32(CNN+12)!=MODEL_ID)fail("FINAL_STATE");
    text("CNN_DIAG_DONE JOBS=1 CPU_CONTROL=PASS MODEL=");hex(MODEL_ID);text("\n");W32(TEST_STATUS,2);halt();
}
