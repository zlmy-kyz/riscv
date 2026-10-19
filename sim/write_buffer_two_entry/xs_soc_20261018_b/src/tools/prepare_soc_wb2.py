"""Task043 SoC integration stimulus: two tiny real-CPU programs.

Epoch A (ordering):
  two posted DDR stores -> UART TX store -> on-chip RAM store -> FENCE ->
  camera x2 -> PP x2 -> DDR done marker. The two camera/PP results are stored
  back into DDR so the checker sees the values the CPU actually received; a
  second read returning different data is the external proof that the aperture
  is neither cached nor filled by the bridge.
  The UART/RAM stores must not be accepted while the posted queue is not empty,
  and FENCE must not retire before the last W beat.

Epoch B (interrupt):
  set mtvec, enable MEIE + MIE, two posted DDR stores, then spin while the
  harness raises irq_external with the queue provably busy. The trap must be
  taken only after the whole queue is drained; the handler writes a DDR marker
  and mrets.

Both programs are placed at DDR local word 0 (CPU 0x4000_0000).
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ------------------------------------------------------------ RV32I assembler
def rtype(f7, rs2, rs1, f3, rd, op):
    return (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


def itype(imm, rs1, f3, rd, op):
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


def stype(imm, rs2, rs1, f3, op):
    imm &= 0xFFF
    return ((imm >> 5) << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | \
        ((imm & 0x1F) << 7) | op


def utype(imm20, rd, op):
    return ((imm20 & 0xFFFFF) << 12) | (rd << 7) | op


def lui(rd, imm20):
    return utype(imm20, rd, 0x37)


def addi(rd, rs1, imm):
    return itype(imm, rs1, 0, rd, 0x13)


def lw(rd, rs1, imm):
    return itype(imm, rs1, 2, rd, 0x03)


def sw(rs2, rs1, imm):
    return stype(imm, rs2, rs1, 2, 0x23)


def jal(rd, off):
    return (((off >> 20) & 1) << 31) | (((off >> 1) & 0x3FF) << 21) | \
        (((off >> 11) & 1) << 20) | (((off >> 12) & 0xFF) << 12) | (rd << 7) | 0x6F


def csrrw(rd, csr, rs1):
    return itype(csr, rs1, 1, rd, 0x73)


def csrrs(rd, csr, rs1):
    return itype(csr, rs1, 2, rd, 0x73)


FENCE = 0x0FF0000F
MRET = 0x30200073
NOP = 0x00000013

MMIO_STATUS = 0x1000_0010
UART_TX = 0x1000_1000
RAM_ADDR = 0x0000_1000
DATA_A = 0x4000_1000
DATA_B = 0x4000_2000
CAMERA = 0x4100_0000
PP = 0x4200_0000
HANDLER = 0x4000_0100
FENCE_PC = 0x4000_003C

# DDR words the checker compares, in local-byte terms.
A_MARK = DATA_A + 0x40        # 0x4000_1040 <- 1
A_CAM1 = DATA_A + 0x60        # 0x4000_1060 <- camera read 1
A_CAM2 = DATA_A + 0x80        # 0x4000_1080 <- camera read 2
A_PP1 = DATA_A + 0xA0         # 0x4000_10A0 <- pp read 1
A_PP2 = DATA_A + 0xC0         # 0x4000_10C0 <- pp read 2
B_MARK = DATA_B + 0x40        # 0x4000_2040 <- 7

CAM_W1 = 0xC0DE_0001
CAM_W2 = 0xC0DE_0002
PP_W1 = 0xB0B0_0001
PP_W2 = 0xB0B0_0002

WORDS_A = 0x68
WORDS_B = 0x110


def program_a():
    img = {}

    def put(off, w):
        assert off % 4 == 0 and off not in img
        img[off] = w & 0xFFFFFFFF

    put(0x000, lui(22, 0x10001))        # x22 = UART TX
    put(0x004, lui(1, 0x40001))         # x1  = 0x4000_1000 DDR data
    put(0x008, lui(24, 0x41000))        # x24 = camera aperture
    put(0x00C, lui(25, 0x42000))        # x25 = PP aperture
    put(0x010, lui(5, 0x00001))         # x5  = 0x1000 on-chip RAM
    put(0x014, addi(2, 0, 0x11))
    put(0x018, addi(3, 0, 0x22))
    put(0x01C, addi(23, 0, 0x33))
    put(0x020, addi(6, 0, 0x44))
    put(0x024, addi(7, 0, 1))
    put(0x028, sw(2, 1, 0))             # DDR store A -> 0x4000_1000 = 0x11
    put(0x02C, sw(3, 1, 0x20))          # DDR store B -> 0x4000_1020 = 0x22
    put(0x030, sw(23, 22, 0))           # UART TX: side effect, must wait
    put(0x034, sw(6, 5, 0))             # on-chip RAM: must wait
    put(0x038, NOP)                     # keep FENCE at the pinned PC
    put(0x03C, FENCE)                   # FENCE_PC
    put(0x040, lw(8, 24, 0))            # camera read 1
    put(0x044, sw(8, 1, 0x60))          # -> 0x4000_1060
    put(0x048, lw(9, 24, 0))            # camera read 2 (must re-read DDR)
    put(0x04C, sw(9, 1, 0x80))          # -> 0x4000_1080
    put(0x050, lw(10, 25, 0))           # PP read 1
    put(0x054, sw(10, 1, 0xA0))         # -> 0x4000_10A0
    put(0x058, lw(11, 25, 0))           # PP read 2 (must re-read DDR)
    put(0x05C, sw(11, 1, 0xC0))         # -> 0x4000_10C0
    put(0x060, sw(7, 1, 0x40))          # done marker -> 0x4000_1040 = 1
    put(0x064, jal(0, 0))               # spin
    return img


def program_b():
    img = {}

    def put(off, w):
        assert off % 4 == 0 and off not in img
        img[off] = w & 0xFFFFFFFF

    put(0x000, lui(5, 0x40002))         # x5 = 0x4000_2000
    put(0x004, addi(2, 0, 0x55))
    put(0x008, addi(3, 0, 0x66))
    put(0x00C, lui(27, 0x40000))        # mtvec base
    put(0x010, addi(27, 27, 0x100))
    put(0x014, csrrw(0, 0x305, 27))     # mtvec = 0x4000_0100
    put(0x018, addi(28, 0, 0x800))      # MEIE
    put(0x01C, csrrw(0, 0x304, 28))     # mie |= MEIE
    put(0x020, addi(29, 0, 0x8))        # MIE
    put(0x024, csrrs(0, 0x300, 29))     # mstatus.MIE = 1
    put(0x028, sw(2, 5, 0))             # DDR store A -> 0x4000_2000
    put(0x02C, sw(3, 5, 0x20))          # DDR store B -> 0x4000_2020
    put(0x030, jal(0, 0))               # spin: IRQ comes from the harness
    put(0x100, lui(30, 0x40002))        # handler: x30 = 0x4000_2000
    put(0x104, addi(31, 0, 7))
    put(0x108, sw(31, 30, 0x40))        # marker 0x4000_2040 = 7
    put(0x10C, MRET)
    return img


def write_hex(path, img, words):
    lines = ['%08x' % img.get(i * 4, 0) for i in range(words)]
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')


def main():
    a, b = program_a(), program_b()
    write_hex(HERE / 'soc_wb2_a.hex', a, WORDS_A)
    write_hex(HERE / 'soc_wb2_b.hex', b, WORDS_B)
    info = {
        'task': 'TASK043_SOC_ORDER',
        'program_a': {'path': 'sim/write_buffer_two_entry/soc_wb2_a.hex',
                      'words': WORDS_A,
                      'sha256': hashlib.sha256((HERE / 'soc_wb2_a.hex').read_bytes()).hexdigest()},
        'program_b': {'path': 'sim/write_buffer_two_entry/soc_wb2_b.hex',
                      'words': WORDS_B,
                      'sha256': hashlib.sha256((HERE / 'soc_wb2_b.hex').read_bytes()).hexdigest()},
        'addresses': {
            'reset_pc': '0x40000000', 'mmio_status': hex(MMIO_STATUS),
            'uart_tx': hex(UART_TX), 'ram': hex(RAM_ADDR),
            'data_a': hex(DATA_A), 'data_b': hex(DATA_B),
            'camera': hex(CAMERA), 'pp': hex(PP),
            'handler': hex(HANDLER), 'fence_pc': hex(FENCE_PC)},
        'expected': {
            'ddr_a': [[hex(DATA_A), 0x11], [hex(DATA_A + 0x20), 0x22],
                      [hex(A_MARK), 1]],
            'ddr_b': [[hex(DATA_B), 0x55], [hex(DATA_B + 0x20), 0x66],
                      [hex(B_MARK), 7]],
            'camera_words': [[hex(A_CAM1), hex(CAM_W1)], [hex(A_CAM2), hex(CAM_W2)]],
            'pp_words': [[hex(A_PP1), hex(PP_W1)], [hex(A_PP2), hex(PP_W2)]],
            'uart_byte': '0x33', 'ram_word': '0x44',
            'irq_cause': '0x8000000b (external)'},
        'watchdog_cycles': 200000,
    }
    (HERE / 'soc_wb2_inputs.json').write_text(json.dumps(info, indent=2) + '\n',
                                              encoding='utf-8')
    print('A words=%d sha=%s' % (WORDS_A, info['program_a']['sha256'][:16]))
    print('B words=%d sha=%s' % (WORDS_B, info['program_b']['sha256'][:16]))
    for name, img in (('A', a), ('B', b)):
        print(name, ' '.join('%03x:%08x' % (k, v) for k, v in sorted(img.items())[:6]))


if __name__ == '__main__':
    main()
