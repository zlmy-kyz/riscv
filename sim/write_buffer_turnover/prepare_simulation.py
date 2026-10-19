"""Task031 simulation design freeze (DeepSeek). Static only: no HDL, no PDS, no board.

Builds the CPU image for the real-SoC sub-case, checks the offline architectural
path, statically re-checks the bridge parameter compatibility this design relies on,
and freezes simulation_inputs.json with the SHA256 of every design input.
"""
from pathlib import Path
import json
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANIFEST = HERE / 'inputs.json'
DESIGN = HERE / 'simulation_inputs.json'
VENDOR = Path('C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation')
BRIDGE = 'myriscv/dual_sram_to_pango_ddr_bridge.v'
TB = 'sim/write_buffer_turnover/tb_write_buffer_turnover_x32.sv'
CASES = 'sim/write_buffer_turnover/turnover_cases.svh'
SOC_ASM = 'sim/write_buffer_turnover/turnover_soc.S'
RUNNER = 'sim/write_buffer_turnover/simulation_runner.py'
PREPARE = 'sim/write_buffer_turnover/prepare_simulation.py'
DISPATCH = 'sim/write_buffer_turnover/run.py'
IMAGE = 'sim/write_buffer_turnover/build/simulation_design_20261014_a/turnover_soc.hex'


def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return Path(path).read_text(encoding='utf-8')


def sext(value, bits):
    value &= (1 << bits) - 1
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def offline_program(program, expect_stores):
    """Mirror of the TB golden interpreter: architectural path/count only."""
    regs = [0] * 32
    mem = {}
    pc = 0
    total = 0
    irq = False
    mepc = mtvec = 0
    stores = loads = 0
    perf = 0
    test_status = 0
    uart = ram = 0
    for _ in range(4000):
        ins = program.get(pc, 0)
        op = ins & 0x7F
        rd = (ins >> 7) & 31
        rs1 = (ins >> 15) & 31
        rs2 = (ins >> 20) & 31
        f3 = (ins >> 12) & 7
        nextpc = pc + 4
        value = None
        address = None
        total += 1
        if op == 0x37:
            value = ins & 0xFFFFF000
        elif op == 0x13:
            value = regs[rs1] + sext(ins >> 20, 12)
        elif op == 0x33:
            value = regs[rs1] + regs[rs2]
        elif op == 3:
            address = regs[rs1] + sext(ins >> 20, 12)
            value = mem.get(address, 0)
            loads += 1
        elif op == 0x23:
            address = (regs[rs1] + sext(((ins >> 25) << 5) | ((ins >> 7) & 31), 12)) & 0xFFFFFFFF
            if address >> 12 == 0x40000:
                if f3 == 0:
                    shift = (address & 3) * 8
                    old = mem.get(address & ~3, 0)
                    mem[address & ~3] = (old & ~(0xFF << shift)) | ((regs[rs2] & 0xFF) << shift)
                elif f3 == 1:
                    shift = (address & 2) * 8
                    old = mem.get(address & ~3, 0)
                    mem[address & ~3] = (old & ~(0xFFFF << shift)) | ((regs[rs2] & 0xFFFF) << shift)
                else:
                    mem[address & ~3] = regs[rs2] & 0xFFFFFFFF
                stores += 1
            elif address == 0x10000108:
                if regs[rs2] == 3:
                    assert perf == 0, 'PERF START not first'
                    perf = 1
                else:
                    assert regs[rs2] == 4 and perf == 1, 'PERF STOP ordering'
                    assert stores == expect_stores, 'PERF STOP before all stores drained'
                    perf = 2
            elif address == 0x10000010:
                command = regs[rs2] & 0xFF
                if command == 1:
                    assert test_status == 0, 'TEST_STATUS RUN only from IDLE'
                    test_status = 1
                elif command in (2, 3):
                    assert test_status == 1, 'TEST_STATUS PASS/FAIL only from RUN'
                    assert command == 2, 'the program must end in PASS'
                    test_status = command
                else:
                    raise AssertionError('illegal TEST_STATUS command %d' % command)
            elif address == 0x10001000:
                uart += 1
            elif address < 0x4000:
                ram += 1
            else:
                raise AssertionError('unsupported store address %x' % address)
        elif op == 0x63:
            assert f3 == 4, 'only blt is supported'
            imm = sext(((ins >> 31) << 12) | (((ins >> 7) & 1) << 11) |
                       (((ins >> 25) & 63) << 5) | (((ins >> 8) & 15) << 1), 13)
            if regs[rs1] < regs[rs2]:
                nextpc = pc + imm
        elif op == 0x73:
            if ins == 0x30200073:
                nextpc = mepc
            elif ins >> 20 == 0x305:
                assert regs[rs1] == 0x40000100, 'mtvec must be 0x40000100'
                mtvec = regs[rs1] - 0x40000000
            elif ins >> 20 == 0x304:
                assert regs[rs1] == 0x800
            else:
                assert ins == 0x30046073, 'unexpected CSR op %x' % ins
        elif op == 0x0F:
            assert f3 == 0
        else:
            raise AssertionError('unsupported opcode %x' % op)
        if value is not None and rd:
            regs[rd] = value & 0xFFFFFFFF
        pc = nextpc
        # IRQ is asserted by the TB on the first accepted store to local 0x800.
        if op == 0x23 and address == 0x40000800 and not irq:
            mepc = pc
            pc = mtvec
            irq = True
            total += 1
        if address == 0x10000010 and test_status == 2:
            break
    words = [mem.get(0x40000800, 0), mem.get(0x40000804, 0),
             mem.get(0x40000820, 0), mem.get(0x40000824, 0)]
    return dict(events=total, loads=loads, ddr_stores=stores, irq=1 if irq else 0,
                uart_writes=uart, ram_writes=ram, final_words=words,
                reg20=regs[20], reg4=regs[4], mtvec=mtvec, mepc=mepc,
                test_status=test_status, perf_start_stop='3/4 at 0x108')


def static_bridge_checks():
    text = read(ROOT / BRIDGE)
    checks = []
    assert re.search(r'parameter integer WRITE_BUFFER_TURNOVER_ENABLE\s*=\s*1', text), \
        'turnover parameter default'
    checks.append('WRITE_BUFFER_TURNOVER_ENABLE default 1')
    assert 'assign write_buffer_turnover_ready = (WRITE_BUFFER_TURNOVER_ENABLE != 0) &&' in text
    checks.append('turnover ready gated by the new parameter')
    assert 'data_req_write && write_buffer_complete;' in text
    checks.append('turnover requires a store and a completing entry')
    ready = re.search(r'assign data_req_ready = idle_ready && \(!write_buffer_busy \|\|\s*'
                      r'write_buffer_turnover_ready \|\|', text)
    assert ready, 'data_req_ready must consult turnover_ready'
    checks.append('data_req_ready consults turnover_ready on the completion edge')
    assert re.search(r'localparam integer POSTED_WRITE_ACTIVE = '
                     r'\(POSTED_WRITE_ENABLE != 0\) && \(MEM_DQ_WIDTH == 32\);', text)
    checks.append('POSTED_WRITE_ACTIVE stays x32-only (x16 ignores posted)')
    assert re.search(r'assign write_buffer_busy = POSTED_WRITE_ACTIVE && write_buffer_valid;', text)
    checks.append('busy/write buffer remain posted-x32 only')
    complete = re.search(r'assign write_buffer_complete = POSTED_WRITE_ACTIVE && resetn && '
                         r'ddr_init_done &&\s*write_buffer_valid && axi_wready &&\s*'
                         r'\(write_buffer_aw_sent \|\| axi_awready\);', text)
    assert complete, 'completion must depend on the old AW/W fields only'
    checks.append('completion depends on the old AW/W fields only')
    tail = text[text.index('else if (POSTED_WRITE_ACTIVE) begin'):]
    assert tail.index('if (write_buffer_complete)') < tail.index('if (write_buffer_push)'), \
        'push must be written after completion so the new entry wins'
    checks.append('push wins over completion in the same edge')
    # The frozen design relies on the cpu-side default being on in soc_top.
    soc = read(ROOT / 'myriscv/soc_top.v')
    assert '.POSTED_WRITE_ENABLE(DDR_WRITE_ORDER_ACTIVE)' in soc
    checks.append('soc_top keeps the existing POSTED_WRITE_ENABLE instance form')
    assert 'WRITE_BUFFER_TURNOVER_ENABLE' not in soc
    checks.append('SoC uses the bridge turnover default (no new SoC parameter)')
    return checks


def main():
    assert not DESIGN.exists(), 'design already frozen; do not rewrite the freeze'
    assert not (HERE / 'build' / 'simulation_design_20261014_a').exists()
    codex = json.loads(read(MANIFEST))
    assert sha(MANIFEST) == '1b19dad3e2c9321b6729d42cd2455ea49fcb3f7bf7e1e3cbc5cc0406b403b692', \
        'Codex input manifest changed'

    # --- CPU program -------------------------------------------------------
    sys.path.insert(0, str(ROOT / 'difftest/golden'))
    from rvtool import Assembler
    asm = Assembler()
    program = asm.assemble(read(HERE / 'turnover_soc.S'))
    assert len(program) <= 1024
    assert asm.sym['handler'] == 256 and asm.sym['loop'] < asm.sym['done'], asm.sym
    review = offline_program(program, expect_stores=73)
    assert review['ddr_stores'] == 73, review
    assert review['final_words'] == [0x007B0040, 2080, 0x00005A11, 0x11], review
    assert review['irq'] == 1 and review['reg20'] == 1 and review['reg4'] == 2080, review
    assert review['uart_writes'] == 1 and review['ram_writes'] == 1, review
    assert review['mtvec'] == 0x100, review
    image_dir = HERE / 'build' / 'simulation_design_20261014_a'
    image_dir.mkdir(parents=True, exist_ok=True)
    (ROOT / IMAGE).write_text(''.join('%08x\n' % program.get(a, 0)
                                      for a in range(0, 4096, 4)), encoding='ascii')

    # --- compile set -------------------------------------------------------
    core = json.loads(read(ROOT / 'sim/cpu_zmmul/coremark_crc_inputs.json'))
    sources = [n for n in core['compile_sources'] if not n.startswith('sim/')]
    sources += ['ipcore/inst_rom/inst_rom.v', 'ipcore/inst_rom/rtl/ipm2l_rom_v1_8_inst_rom.v',
                'ipcore/inst_rom/rtl/ipm2l_spram_v1_8_inst_rom.v',
                'ipcore/data_ram/data_ram.v', 'ipcore/data_ram/rtl/ipm2l_spram_v1_8_data_ram.v',
                TB]
    sources = list(dict.fromkeys(sources))
    vendor = ['GTP_GRS.v', 'GTP_DRM36K_E1.v', 'GTP_APM_E2.v']
    modules = []
    for path in [*[VENDOR / n for n in vendor], *[ROOT / n for n in sources]]:
        modules += re.findall(r'^\s*module\s+(\w+)', read(path), re.M)
    assert len(modules) == len(set(modules)), 'duplicate module names in the compile set'
    assert 'tb_write_buffer_turnover_x32' in modules
    assert 'dual_sram_to_pango_ddr_bridge' in modules

    checks = static_bridge_checks()
    design = dict(
        status='WRITE_BUFFER_TURNOVER_SIMULATION_DESIGN_FROZEN_HDL_NOT_RUN',
        fixed_tag=codex['fixed_tag'],
        input_manifest_sha256=sha(MANIFEST),
        sha256={
            'sim/write_buffer_turnover/run.py': sha(ROOT / DISPATCH),
            'sim/write_buffer_turnover/simulation_runner.py': sha(ROOT / RUNNER),
            'sim/write_buffer_turnover/tb_write_buffer_turnover_x32.sv': sha(ROOT / TB),
            'sim/write_buffer_turnover/turnover_cases.svh': sha(ROOT / CASES),
            'sim/write_buffer_turnover/turnover_soc.S': sha(ROOT / SOC_ASM),
            'sim/write_buffer_turnover/prepare_simulation.py': sha(ROOT / PREPARE),
            'sim/write_buffer_turnover/build/simulation_design_20261014_a/turnover_soc.hex': sha(ROOT / IMAGE),
        },
        compile_sources=sources,
        vendor_compile_sources=vendor,
        expected_modules=modules,
        module_count=len(modules),
        control=dict(name='control', posted=1, turnover=0, defines=['-gPOSTED=1', '-gTURNOVER=0']),
        key=dict(name='key', posted=1, turnover=1, defines=['-gPOSTED=1', '-gTURNOVER=1']),
        cpu_image=IMAGE,
        program_review=review,
        plusargs=dict(
            CPU_IMAGE=IMAGE,
            EXPECT_EVENTS=review['events'],
            EXPECT_STORES=review['ddr_stores'],
            EXPECT_IRQ=review['irq'],
            EXPECT_W0=review['final_words'][0],
            EXPECT_W1=review['final_words'][1],
            EXPECT_W2=review['final_words'][2],
            EXPECT_W3=review['final_words'][3],
            EXPECT_R20=review['reg20'],
            EXPECT_R4=review['reg4'],
        ),
        groups=['turnover_accept_eligibility', 'front_slot_priority', 'consecutive_turnover',
                'lane_strobe_dcache_ownership', 'forward_read_boundaries', 'reset_init_cancel',
                'non_ddr_order_gate', 'real_soc_turnover_fence_irq'],
        positive_key_coverage=['OPPORTUNITIES', 'ACCEPTED', 'EARLY', 'I_OVERLAP', 'OVERLAP',
                               'GATE', 'FENCE_WAIT', 'IRQ_WAIT', 'STOP_WAIT', 'UART', 'RAM',
                               'SOC_TURNOVER', 'fills', 'updates', 'cancelled'],
        static_checks=checks,
        controlled_comparison=dict(
            program='short_program (6 held stores, 2 backpressured, 1 same-edge AW/W, 2 partial)',
            expectation='control SHORT cycles - key SHORT cycles == key opportunities',
            opportunity_rule='store presented on the cycle the old entry W beat is accepted',
        ),
        scope=('x32 posted single write entry reused on the W completion edge: direct bridge '
               'eligibility/ownership/lane/strobe/reset/init cases, D-hit forwarding and read '
               'drain boundaries, non-DDR request gate, and a minimal real SoC turnover/FENCE/'
               'IRQ/PERF-STOP program. No PHY, no PDS, no board, ISA=0, CPU unchanged.'),
        HDL_started=False, PDS_started=False, serial_opened=False,
    )
    DESIGN.write_text(json.dumps(design, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('DESIGN FROZEN', len(modules), 'modules;', DESIGN.name, sha(DESIGN))
    print('program:', {k: review[k] for k in
                       ('events', 'ddr_stores', 'loads', 'irq', 'final_words', 'reg20', 'reg4')})


if __name__ == '__main__':
    main()
