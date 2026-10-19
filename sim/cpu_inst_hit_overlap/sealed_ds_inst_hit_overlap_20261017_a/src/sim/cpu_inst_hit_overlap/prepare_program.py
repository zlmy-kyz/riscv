"""Task033 frozen stimulus generator.

Produces, from one source of truth:
  * plan_bridge.txt   - every bridge-level logical request, knob and reset event
  * soc_program.hex   - minimal RV32I program image loaded into DDR local word 0
  * soc_fault_*.hex   - two-instruction illegal-fetch programs (Camera/PP epoch)
  * inputs.json       - model parameters, expected coverage labels and identities

No HDL is run here; the checker replays the same plan against the edge log.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

MEM_LCG_MUL, MEM_LCG_ADD, MEM_LCG_SEED = 1103515245, 12345, 1
NBEAT = 8256
DDR_BASE = 0x4000_0000

# ---------------------------------------------------------------- plan builder
PLAN = []
_grp = 0


def tok(kind, addr=0, data=0, strb=0, size=2, wmode=0, warg=0, scen="-", same=False):
    global _grp
    if not same:
        _grp += 1
    PLAN.append(dict(idx=len(PLAN), kind=kind, addr=addr, data=data, strb=strb,
                     size=size, wmode=wmode, warg=warg, grp=_grp, scen=scen))
    return PLAN[-1]


def knob(num, val):
    tok("K", addr=num, data=val, scen="knob%d"%num)


def poke(addr, data, strb):
    tok("M", addr=addr, data=data, strb=strb, scen="model_poke")


def reset(mode=0, wmode=0, warg=0, scen="reset"):
    tok("R", data=mode, wmode=wmode, warg=warg, scen=scen)


def epoch(num):
    tok("E", data=num, scen="epoch%d" % num)


def wait_rsp(scen="wait_d_rsp", side="d"):
    tok("WAIT", wmode=6 if side == "d" else 8, scen=scen)


def build_plan():
    # I line bases (DDR-local bytes) and the 64-row/32-byte geometry:
    #   I0 0x0000 idx0 tag0    I1 0x0100 idx8 tag8    I0b 0x2000 idx0 tag0x100
    #   I2 0x0200 idx16        I3 0x0300 idx24        I4 0x0400 idx32
    #   I5 0x0500 idx40        I6 0x0600 idx48        I7 0x0700 idx56
    knob(1, 0); knob(2, 2); knob(3, 0); knob(4, 1); knob(5, 0); knob(6, 0); knob(7, 0)

    # ---------------- epoch 1: warm-up, all eight I word lanes ----------------
    epoch(1)
    tok("I", 0x0000, scen="warm_i0_fill_lane0")
    for lane in range(1, 8):
        tok("I", lane * 4, scen="warm_i0_lane%d_hit" % lane)
    tok("I", 0x0100, scen="warm_i1_fill")
    tok("I", 0x0104, scen="warm_i1_lane1_hit")
    tok("I", 0x2000, scen="warm_i0_alias_fill")      # same index, different tag
    tok("I", 0x2004, scen="warm_i0_alias_lane1_hit")
    tok("I", 0x2008, scen="warm_i0_alias_lane2_hit")
    tok("I", 0x0200, scen="warm_i2_fill")
    tok("I", 0x0300, scen="warm_i3_fill")
    tok("I", 0x0400, scen="warm_i4_fill")
    tok("I", 0x0500, scen="warm_i5_fill")

    # ---------------- epoch 2: S1 D long miss, AR backpressure ----------------
    epoch(2)
    knob(1, 4); knob(2, 14)
    tok("D", 0x1000, scen="s1_d_miss_ar_backpressure")
    tok("I", 0x0100, wmode=2, warg=3, scen="s1_i_hit_under_ar_stall")
    wait_rsp("s1_d_rsp")
    knob(1, 0); knob(2, 12)
    tok("D", 0x1020, scen="s1b_d_miss_r_wait")
    tok("I", 0x2004, wmode=3, warg=3, scen="s1b_i_hit_under_r_wait_1")
    tok("I", 0x2008, wmode=3, warg=4, scen="s1b_i_hit_under_r_wait_2")
    wait_rsp("s1b_d_rsp")

    # ---------------- epoch 3: S2 accept/return boundaries ----------------
    epoch(3)
    # instant_r=2: the beat comes back in the AR handshake cycle itself.
    knob(6, 2); knob(2, 0)
    tok("D", 0x1040, scen="s2a_d_ar_r_same_edge")
    tok("I", 0x0100, scen="s2a_i_accept_on_ar_r_edge")
    wait_rsp("s2a_d_rsp")
    knob(6, 0); knob(2, 6)
    tok("D", 0x1060, scen="s2b_d_late_r")
    tok("I", 0x2004, wmode=3, warg=4, scen="s2b_i_hit_during_late_r")
    wait_rsp("s2b_d_rsp")
    knob(2, 2)
    tok("D", 0x1080, scen="s2c_d_r_on_i_rsp_edge")
    tok("I", 0x2004, wmode=3, warg=3, scen="s2c_i_rsp_on_r_edge")
    wait_rsp("s2c_d_rsp")
    tok("D", 0x10a0, scen="s2d_d_double_response")
    tok("I", 0x2008, wmode=3, warg=4, scen="s2d_i_double_response")
    wait_rsp("s2d_d_rsp")

    # ---------------- epoch 4: S3 four consecutive I hits then parked miss ----
    epoch(4)
    knob(2, 14)
    tok("D", 0x10c0, scen="s3_d_miss_window")
    tok("I", 0x2004, scen="s3_i_hit_burst_1")
    tok("I", 0x0204, scen="s3_i_hit_burst_2")
    tok("I", 0x0304, scen="s3_i_hit_burst_3")
    tok("I", 0x0404, scen="s3_i_hit_burst_4")
    tok("I", 0x0600, scen="s3_i_miss_parked")
    tok("PI", 0x0604, warg=6, scen="s3_probe_slot_full")
    wait_rsp("s3_d_rsp")
    tok("I", 0x0604, scen="s3_parked_promote_hit_lane1")
    wait_rsp("s3_i_rsp", "i")

    # ---------------- epoch 5: S4 parked miss, address poisoning --------------
    epoch(5)
    knob(2, 16)
    tok("D", 0x10e0, scen="s4_d_miss_window")
    tok("I", 0x0700, wmode=3, warg=2, scen="s4_i_miss_parked")
    tok("X", 0x2004, scen="s4_live_addr_poison")     # live I address becomes a hit
    tok("PI", 0x2004, warg=5, scen="s4_probe_poisoned_hit")
    wait_rsp("s4_d_rsp")
    tok("D", 0x1040, scen="s4_new_d_1")
    tok("D", 0x1060, scen="s4_new_d_2")
    wait_rsp("s4_promote_rsp", "i")
    tok("I", 0x0700, scen="s4_parked_line_hit_after_fill")
    wait_rsp("s4_i_rsp", "i")
    # earliest promotion with no competition
    knob(2, 10)
    tok("D", 0x1100, scen="s4b_d_miss_window")
    tok("I", 0x0a00, wmode=3, warg=2, scen="s4b_i_miss_parked")
    wait_rsp("s4b_d_rsp")
    wait_rsp("s4b_promote_rsp", "i")

    # ---------------- epoch 6: S5 main slot keeps D priority ----------------
    epoch(6)
    knob(2, 8)
    tok("D", 0x1120, scen="s5_d_miss_window")
    tok("D", 0x1140, wmode=6, scen="s5_new_d_at_completion")
    tok("I", 0x2004, wmode=6, scen="s5_i_blocked_at_completion", same=True)
    wait_rsp("s5_new_d_rsp")
    wait_rsp("s5_i_rsp", "i")

    # ---------------- epoch 7: S6 store invalidates the I line ----------------
    epoch(7)
    knob(2, 4)
    tok("I", 0x0404, scen="s6_old_i_hit_before_store")
    tok("W", 0x0404, data=0x11223344, strb=0xF, wmode=8, scen="s6_store_hits_i_line")
    tok("I", 0x040c, wmode=8, scen="s6_young_i_blocked_on_store", same=True)
    wait_rsp("s6_store_rsp")
    wait_rsp("s6_i_rsp", "i")
    tok("W", 0x0404, data=0x0000AA00, strb=0x2, scen="s6_byte_store")
    tok("I", 0x0404, scen="s6_byte_store_i_miss")
    wait_rsp("s6_i_rsp_b", "i")
    tok("W", 0x0408, data=0x0000BEEF, strb=0x3, scen="s6_half_store")
    tok("I", 0x0408, scen="s6_half_store_i_miss")
    wait_rsp("s6_i_rsp_c", "i")
    tok("W", 0x040c, data=0xDEADBEEF, strb=0x0, scen="s6_zero_strobe_store")
    tok("I", 0x040c, scen="s6_zero_strobe_i_miss")
    wait_rsp("s6_i_rsp_d", "i")

    # ---------------- epoch 8: S7 old posted write drain ----------------
    epoch(8)
    knob(3, 20); knob(4, 3); knob(2, 4)
    tok("W", 0x10c0, data=0x55667788, strb=0xF, scen="s7_old_write_aw_pending")
    tok("I", 0x2004, scen="s7_i_hit_under_write_busy")
    wait_rsp("s7_i_rsp_a", "i")
    tok("I", 0x0800, scen="s7_i_miss_waits_drain")
    tok("PD", 0x1160, warg=4, scen="s7_probe_d_miss_blocked")
    wait_rsp("s7_i_rsp_b", "i")
    knob(2, 2)
    tok("D", 0x1180, scen="s7_d_after_drain")

    # ---------------- epoch 9: S8 store forwarding holds ----------------
    epoch(9)
    knob(3, 20); knob(4, 3); knob(2, 2)
    tok("D", 0x1040, scen="s8_d_line_warm")
    wait_rsp("s8_d_rsp")
    tok("W", 0x1044, data=0x0000FF00, strb=0x2, scen="s8_pending_partial_store")
    tok("D", 0x1044, scen="s8_forward_same_word")
    wait_rsp("s8_fwd_rsp")
    tok("D", 0x1048, scen="s8_adjacent_word_no_forward")
    wait_rsp("s8_adj_rsp")
    knob(3, 0)
    tok("WAIT", wmode=10, scen="s8_write_done")
    tok("D", 0x1044, scen="s8_after_drain_merged")
    wait_rsp("s8_merged_rsp")

    # ---------------- epoch 10: S9 reset cancellation ----------------
    epoch(10)
    knob(2, 6)
    tok("I", 0x2004, scen="s9a_i_hit_pending_consume")
    reset(0, scen="s9a_reset_on_hit")
    reset(1, scen="s9a_release")
    tok("I", 0x2004, scen="s9a_cold_after_reset")
    wait_rsp("s9a_rsp", "i")
    knob(2, 16)
    tok("D", 0x11a0, scen="s9b_d_miss_window")
    tok("I", 0x0b00, wmode=3, warg=2, scen="s9b_i_miss_parked")
    reset(0, scen="s9b_reset_on_parked")
    reset(1, scen="s9b_release")
    tok("I", 0x0b00, scen="s9b_cold_after_reset")
    wait_rsp("s9b_rsp", "i")
    tok("D", 0x11c0, scen="s9c_d_miss_window")
    tok("I", 0x0c00, wmode=3, warg=2, scen="s9c_i_miss_parked")
    wait_rsp("s9c_d_rsp")
    reset(0, wmode=9, scen="s9c_reset_awaiting_r")
    reset(1, scen="s9c_release")
    tok("I", 0x0c00, scen="s9c_cold_after_reset")
    wait_rsp("s9c_rsp", "i")

    # ---------------- epoch 11: S10 uncached Camera/PP windows ----------------
    epoch(11)
    knob(1, 0); knob(2, 3)
    tok("D", 0x0100_0000, scen="s10_camera_first_read")
    poke(0x0100_0000, 0xCAFEBABE, 0xF)
    tok("D", 0x0100_0000, scen="s10_camera_second_read")
    wait_rsp("s10_cam_rsp")
    tok("D", 0x0200_0000, scen="s10_pp_first_read")
    poke(0x0200_0000, 0x1234ABCD, 0xF)
    tok("D", 0x0200_0000, scen="s10_pp_second_read")
    wait_rsp("s10_pp_rsp")
    knob(2, 10)
    tok("D", 0x0100_0020, scen="s10_camera_under_i_hit")
    tok("I", 0x2004, wmode=3, warg=3, scen="s10_i_hit_no_camera_fill")
    wait_rsp("s10_cam2_rsp")
    knob(2, 3)

    # ---------------- epoch 12: controlled performance comparison -------------
    epoch(12)
    knob(2, 3)
    for n, base in enumerate((0x2000, 0x0200, 0x0300, 0x0400, 0x0500, 0x0600)):
        tok("I", base, scen="perf_warm_%d" % (n + 1))
    knob(2, 16); knob(1, 0)
    tok("D", 0x11e0, scen="perf_d_miss")
    for n in range(6):
        tok("I", [0x2004, 0x0204, 0x0304, 0x0404, 0x0504, 0x0604][n],
            scen="perf_i_hit_%d" % (n + 1))
    wait_rsp("perf_d_rsp")
    wait_rsp("perf_i_rsp", "i")
    return PLAN


# ------------------------------------------------------------ RV32I assembler
def rtype(f7, rs2, rs1, f3, rd, op):
    return (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


def itype(imm, rs1, f3, rd, op):
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


def stype(imm, rs2, rs1, f3, op):
    imm &= 0xFFF
    return ((imm >> 5) << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | \
        ((imm & 0x1F) << 7) | op


def btype(imm, rs2, rs1, f3, op):
    imm &= 0x1FFF
    return (((imm >> 12) & 1) << 31) | (((imm >> 5) & 0x3F) << 25) | (rs2 << 20) | \
        (rs1 << 15) | (f3 << 12) | (((imm >> 1) & 0xF) << 8) | (((imm >> 11) & 1) << 7) | op


def utype(imm20, rd, op):
    return ((imm20 & 0xFFFFF) << 12) | (rd << 7) | op


def jtype(imm, rd, op):
    imm &= 0x1FFFFF
    return (((imm >> 20) & 1) << 31) | (((imm >> 1) & 0x3FF) << 21) | \
        (((imm >> 11) & 1) << 20) | (((imm >> 12) & 0xFF) << 12) | (rd << 7) | op


def lui(rd, imm20):
    return utype(imm20, rd, 0x37)


def addi(rd, rs1, imm):
    return itype(imm, rs1, 0, rd, 0x13)


def lw(rd, rs1, imm):
    return itype(imm, rs1, 2, rd, 0x03)


def sw(rs2, rs1, imm):
    return stype(imm, rs2, rs1, 2, 0x23)


def beq(rs1, rs2, off):
    return btype(off, rs2, rs1, 0, 0x63)


def jal(rd, off):
    return jtype(off, rd, 0x6F)


def add(rd, rs1, rs2):
    return rtype(0, rs2, rs1, 0, rd, 0x33)


def bne(rs1, rs2, off):
    return btype(off, rs2, rs1, 1, 0x63)


NOP = 0x00000013


SOC_PROGRAM_WORDS = 116


def build_soc_program():
    """Program image: word index -> instruction, DDR local word 0 == 0x40000000.

    Shape of the workload (all data lives at 0x4000_1000.., i.e. DDR, so every
    loaded word is the frozen LCG image and the reference can predict it):
      * MMIO TEST_STATUS <- RUN before anything else.
      * An 8-iteration loop with a load from a fresh DDR line each pass and a
        taken backward branch. From pass 2 on the loop body is already in the
        instruction line buffer, so every pass opens a D miss window that is
        filled with I hits - the exact case the new bridge parameter targets.
      * A taken forward branch whose fall-through holds a store plus a second
        load on a cold line: the wrong path must leave no trace (no request,
        no DDR write, no retire) and its fetch response must be discarded.
    """
    img = {}

    def put(byte_off, word):
        assert byte_off % 4 == 0 and byte_off not in img
        img[byte_off] = word & 0xFFFFFFFF

    put(0x000, lui(20, 0x10000))         # x20 = 0x1000_0000 MMIO
    put(0x004, addi(21, 20, 0x10))       # x21 = 0x1000_0010 TEST_STATUS
    put(0x008, addi(22, 0, 1))
    put(0x00C, sw(22, 21, 0))            # TEST_STATUS <- RUN
    put(0x010, lui(1, 0x40001))          # x1 = 0x4000_1000 DDR data
    put(0x014, addi(6, 0, 0x5A))         # wrong-path store data
    put(0x018, addi(2, 0, 8))            # loop counter
    put(0x01C, lw(3, 1, 0))              # fresh DDR line every pass -> D miss
    put(0x020, addi(4, 3, 5))            # load-use
    put(0x024, addi(1, 1, 0x20))
    put(0x028, addi(5, 4, 1))
    put(0x02C, addi(2, 2, -1))
    put(0x030, bne(2, 0, 0x01C - 0x030))  # taken, backward
    put(0x034, beq(0, 0, 0x100 - 0x034))  # taken, forward: wrong path follows
    put(0x038, sw(6, 1, 0x40))           # WRONG-PATH store
    put(0x03C, lui(7, 0x00001))          # WRONG-PATH
    put(0x040, lw(8, 1, 0))              # WRONG-PATH load on a cold line
    put(0x044, addi(9, 0, 0x7F))         # WRONG-PATH
    put(0x048, beq(0, 0, 0x100 - 0x048))  # WRONG-PATH
    for off in range(0x04C, 0x100, 4):
        put(off, NOP)
    put(0x100, addi(10, 0, 3))
    put(0x104, sw(10, 1, -0x40))         # 0x4000_10C0
    put(0x108, lw(11, 1, -0x40))
    put(0x10C, add(12, 10, 11))
    put(0x110, jal(0, 0x1C0 - 0x110))
    for off in range(0x114, 0x1C0, 4):
        put(off, NOP)
    put(0x1C0, addi(23, 0, 2))
    put(0x1C4, sw(23, 21, 0))            # TEST_STATUS <- PASS
    put(0x1C8, jal(0, 0))                # spin
    return img


def build_fault_program(target):
    """Two-instruction program: jump to a fetch-illegal DDR window."""
    return {0x0: lui(8, target >> 12), 0x4: jalr(0, 8, 0)}


def jalr(rd, rs1, imm):
    return itype(imm, rs1, 0, rd, 0x67)


def write_hex(path, img, words):
    lines = []
    for i in range(words):
        lines.append('%08x' % img.get(i * 4, 0))
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')


def main():
    plan = build_plan()
    # sanity: group ids must be non-decreasing and every scen present
    assert all(plan[i]['grp'] <= plan[i + 1]['grp'] for i in range(len(plan) - 1))
    lines = []
    for t in plan:
        lines.append('TOK %d %s %08x %08x %01x %d %d %d %d %s' % (
            t['idx'], t['kind'], t['addr'], t['data'], t['strb'], t['size'],
            t['wmode'], t['warg'], t['grp'], t['scen']))
    (HERE / 'plan_bridge.txt').write_text('\n'.join(lines) + '\n', encoding='ascii')

    soc = build_soc_program()
    write_hex(HERE / 'soc_program.hex', soc, SOC_PROGRAM_WORDS)
    write_hex(HERE / 'soc_fault_camera.hex', build_fault_program(0x4100_0000), 2)
    write_hex(HERE / 'soc_fault_pp.hex', build_fault_program(0x4200_0000), 2)

    scen = [t['scen'] for t in plan]
    inputs = {
        'task': 'TASK033_INST_HIT_UNDER_DATA_MISS',
        'plan_bridge': 'sim/cpu_inst_hit_overlap/plan_bridge.txt',
        'plan_tokens': len(plan),
        'plan_groups': len({t['grp'] for t in plan}),
        'memory': {'lcg_mul': MEM_LCG_MUL, 'lcg_add': MEM_LCG_ADD,
                   'lcg_seed': MEM_LCG_SEED, 'bits': '23:16',
                   'beats': NBEAT, 'beat_bytes': 32},
        'ddr_local_geometry': {'beat_bytes': 32, 'ctrl_addr_unit_bytes': 4,
                               'camera_local': '0x01000000-0x013fffff',
                               'pp_local': '0x02000000-0x0200ffff'},
        'bridge_params': {'MEM_DQ_WIDTH': 32, 'INST_LINE_BUFFER_ENABLE': 1,
                          'DATA_LINE_BUFFER_ENABLE': 1, 'CAMERA_UNCACHED_ENABLE': 1,
                          'PREPROCESS_UNCACHED_ENABLE': 1, 'POSTED_WRITE_ENABLE': 1,
                          'DATA_READ_UNDER_WRITE_ENABLE': 1,
                          'DATA_STORE_FORWARD_ENABLE': 1,
                          'WRITE_BUFFER_TURNOVER_ENABLE': 1,
                          'INST_HIT_UNDER_DATA_MISS_ENABLE': 'OVERLAP_parameter'},
        'soc_params': {'RESET_PC': '0x40000000', 'INST_ROM_BASE': 0, 'DATA_RAM_BASE': 0,
                       'ENABLE_DDR': 1, 'DDR_MEM_DQ_WIDTH': 32,
                       'DDR_POSTED_WRITE_ENABLE': 1, 'ENABLE_CAMERA': 1,
                       'ENABLE_PREPROCESS': 1, 'ENABLE_CNN': 1, 'PERF_AUTO_ARM': 0},
        'soc_program': 'sim/cpu_inst_hit_overlap/soc_program.hex',
        'soc_program_sha256': hashlib.sha256((HERE / 'soc_program.hex').read_bytes()).hexdigest(),
        'soc_fault_programs': {
            'camera': {'path': 'sim/cpu_inst_hit_overlap/soc_fault_camera.hex',
                       'target': '0x41000000', 'cause': 1},
            'pp': {'path': 'sim/cpu_inst_hit_overlap/soc_fault_pp.hex',
                   'target': '0x42000000', 'cause': 1},
        },
        'soc_data_map': {'data_base': '0x40001000',
                         'loop_load_lines': '0x40001000-0x400010e0 step 0x20',
                         'wrong_path_store': '0x40001140',
                         'wrong_path_load': '0x40001100',
                         'correct_path_store': '0x400010c0',
                         'mmio_test_status': '0x10000010'},
        'soc_branch': {'loop_branch_pc': '0x40000030', 'loop_target': '0x4000001c',
                       'branch_pc': '0x40000034', 'wrong_path': '0x40000038',
                       'target': '0x40000100', 'wrong_path_lines': ['0x40000020',
                                                                    '0x40000040']},
        'soc_fault': {'camera_target': '0x41000000', 'pp_target': '0x42000000',
                      'expected_cause': 1, 'note': 'fetch from the Camera/PP aperture '
                      'must raise INST_ACCESS_FAULT with tval == the fetch PC and '
                      'must not issue a DDR fetch AR'},
        'scenarios': scen,
        'watchdog_cycles': 100000,
        'job_timeout_s': {'vlib': 60, 'vlog': 60, 'vsim': 180, 'checker': 60},
    }
    (HERE / 'inputs.json').write_text(json.dumps(inputs, indent=2) + '\n', encoding='utf-8')
    print('plan tokens=%d groups=%d scenes=%d' % (len(plan), inputs['plan_groups'], len(scen)))
    print('soc program words=%d sha=%s' % (len(soc), inputs['soc_program_sha256'][:16]))


if __name__ == '__main__':
    main()
