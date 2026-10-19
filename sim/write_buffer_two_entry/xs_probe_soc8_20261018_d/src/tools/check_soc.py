"""Task043 / 补正02 item 2 reference: real-CPU SoC ordering and drain fragment.

Reads only the two artefacts the testbench produced:
  soc.edges.log   one "E" line per rising edge plus "T" (retire) / "I" (IRQ)
  soc.mem.log     the DDR model's beat image after both epochs

Everything below is derived from the external ports of the DUT (CPU data bus,
DDR user port, retire/IRQ events). No RTL-internal bookkeeping is used as
evidence, and every claim is an assertion that fails the run when violated.

Checks
  A1  no non-DDR request (RAM/MMIO/UART) is accepted while the posted write
      queue is non-empty. The interconnect must hold them until it drains.
  A2  the first non-DDR acceptance happens with the queue empty and strictly
      after the last W beat that preceded it, i.e. also after the second queued
      store when the head had already completed.
  A3  the non-DDR request really was presented and refused first (a blocked
      window exists), so A1 is not vacuous.
  A4  FENCE retires only with the queue empty and strictly after the last W
      beat of the stores that preceded it.
  A5  camera and PP reads each reach DDR twice (two AR fires each) and return
      different data, i.e. they are neither cached nor filled.
  A6  both FENCE and the aperture reads keep program order after the stores.
  B1  the external interrupt is taken only with the queue empty, strictly after
      the last W beat, with mcause = 0x8000000b and a handler that ran.
  M1  final DDR image.
"""
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------- expectations
# The DDR user port carries the controller address, which is the local byte
# address divided by four (each unit is 4 bytes): 0x4100_0000 - 0x4000_0000.
CAM_CTRL = 0x0040_0000
PP_CTRL = 0x0080_0000
FENCE_PC = 0x4000_003C
IRQ_CAUSE = 0x8000_000B


def word_of(hexline):
    """%064h beat line -> lane-0 32-bit word (least significant 8 hex digits)."""
    return int(hexline.strip()[-8:], 16)


HEXCHARS = set('0123456789abcdefABCDEF')


def as_bit(tok):
    """A pre-reset edge samples X on some ports; treat anything but 1 as 0."""
    return 1 if tok == '1' else 0


def as_hex(tok):
    """X/Z-contaminated values are reported as None instead of crashing."""
    return int(tok, 16) if tok and set(tok) <= HEXCHARS else None


def parse_edges(path):
    edges, retires, irqs = [], [], []
    for raw in path.read_text(encoding='ascii', errors='replace').splitlines():
        parts = raw.split()
        if not parts:
            continue
        kind = parts[0]
        rec = {}
        for tok in parts[1:]:
            if '=' in tok:
                k, v = tok.split('=', 1)
                rec[k] = v
        if kind == 'E':
            rec['n'] = int(rec['n'], 10)
            rec['ep'] = int(rec['ep'], 10)
            rec['fst'] = as_hex(rec['fst']) or 0
            for k in ('rst', 'init', 'busy', 'dv', 'dr', 'dw', 'wf', 'fret',
                      'itk', 'arv', 'arr', 'rv', 'awv', 'awr', 'wr'):
                rec[k] = as_bit(rec[k])
            rec['ds'] = as_hex(rec['ds']) or 0
            for k in ('da', 'dwd', 'ddra', 'wdv', 'rdv', 'wsv', 'mcs', 'awa', 'ara',
                      'ari', 'rid'):
                rec[k] = as_hex(rec[k])
            edges.append(rec)
        elif kind == 'T':
            rec['n'] = int(rec['n'], 10)
            rec['ep'] = int(rec['ep'], 10)
            rec['pc'] = as_hex(rec['pc']) or 0
            rec['inst'] = as_hex(rec['inst']) or 0
            retires.append(rec)
        elif kind == 'I':
            rec['n'] = int(rec['n'], 10)
            rec['ep'] = int(rec['ep'], 10)
            rec['cause'] = as_hex(rec['cause']) or 0
            rec['epc'] = as_hex(rec['epc']) or 0
            rec['busy'] = as_bit(rec['busy'])
            irqs.append(rec)
    return edges, retires, irqs


def parse_mem(path):
    beats = {}
    for raw in path.read_text(encoding='ascii', errors='replace').splitlines():
        parts = raw.split()
        if len(parts) >= 3 and parts[0] == 'P':
            beats[int(parts[1], 10)] = word_of(parts[2])
    return beats


def accept(e):
    return e['dv'] == 1 and e['dr'] == 1


def non_ddr(e):
    return (e['ds'] & 0b0111) != 0


def main(argv):
    run = Path(argv[1]).resolve()
    edges, retires, irqs = parse_edges(run / 'soc.edges.log')
    mem = parse_mem(run / 'soc.mem.log')
    checks, detail, notes = {}, {}, []

    e1 = [e for e in edges if e['ep'] == 1]
    e2 = [e for e in edges if e['ep'] == 2]
    wf1 = [e['n'] for e in e1 if e['wf'] == 1]
    wf2 = [e['n'] for e in e2 if e['wf'] == 1]
    aw1 = [e['n'] for e in e1 if e['awv'] == 1 and e['awr'] == 1]
    nddr_acc = [e for e in e1 if accept(e) and non_ddr(e)]
    ddr_st_acc = [e for e in e1 if accept(e) and e['dw'] == 1 and e['ds'] & 0b1000]

    # ---- A1: non-DDR never accepted while the queue is busy -------------------
    viol = [e['n'] for e in e1 if accept(e) and non_ddr(e) and e['busy'] == 1]
    checks['A1_no_non_ddr_accept_while_busy'] = not viol
    detail['A1'] = dict(violations=viol[:8], count=len(viol))

    # ---- A2: first non-DDR acceptance lands after the queue drained ----------
    first_nd = nddr_acc[0]['n'] if nddr_acc else None
    before = [c for c in wf1 if first_nd is not None and c < first_nd]
    last_w = max(before) if before else None
    checks['A2_non_ddr_after_all_w_beats'] = (
        first_nd is not None and last_w is not None and first_nd > last_w and
        nddr_acc[0]['busy'] == 0)
    detail['A2'] = dict(first_non_ddr_accept=first_nd, last_w_before=last_w,
                        first_non_ddr_busy=(nddr_acc[0]['busy'] if nddr_acc else None),
                        w_beats_ep1=wf1)

    # the "head done, tail not W yet" window: second queued store still pending
    tail_w = wf1[1] if len(wf1) > 1 else None
    checks['A2b_non_ddr_after_tail_w'] = (
        first_nd is not None and tail_w is not None and first_nd > tail_w)
    detail['A2b'] = dict(tail_w_cycle=tail_w, first_non_ddr_accept=first_nd)

    # ---- A3: the request was presented and refused first (not vacuous) -------
    blocked = [e['n'] for e in e1
               if e['dv'] == 1 and e['dr'] == 0 and non_ddr(e) and e['busy'] == 1]
    checks['A3_non_ddr_was_blocked_first'] = bool(blocked)
    detail['A3'] = dict(blocked_edges=len(blocked), first_blocked=(blocked[0] if blocked else None),
                        last_blocked=(blocked[-1] if blocked else None))
    if tail_w is not None and detail['A3']['first_blocked'] is not None:
        in_window = [c for c in blocked if wf1[0] <= c <= tail_w]
        detail['A3']['blocked_inside_head_only_window'] = len(in_window)
        notes.append('blocked edges inside the head-complete/tail-pending window: %d'
                     % len(in_window))

    # ---- A4: FENCE retires after the drain ---------------------------------
    fret = [e for e in e1 if e['fret'] == 1]
    fcyc = fret[0]['n'] if fret else None
    before_f = [c for c in wf1 if fcyc is not None and c < fcyc]
    checks['A4_fence_retires_after_drain'] = (
        len(fret) == 1 and fcyc is not None and bool(before_f) and
        fcyc > max(before_f) and fret[0]['busy'] == 0 and fret[0]['awv'] == 0)
    detail['A4'] = dict(fence_retire=fcyc, last_w_before=max(before_f) if before_f else None,
                        fence_edge_busy=(fret[0]['busy'] if fret else None),
                        w_beats_before_fence=len(before_f))

    # ---- A5/A6: camera and PP are uncached, two reads each -----------------
    cam_ar = [e['n'] for e in e1 if e['arv'] == 1 and e['arr'] == 1 and e['ara'] == CAM_CTRL]
    pp_ar = [e['n'] for e in e1 if e['arv'] == 1 and e['arr'] == 1 and e['ara'] == PP_CTRL]
    checks['A5_camera_pp_read_ddr_twice'] = (len(cam_ar) == 2 and len(pp_ar) == 2)
    detail['A5'] = dict(camera_ar=cam_ar, pp_ar=pp_ar)
    checks['A6_aperture_after_fence'] = (
        fcyc is not None and bool(cam_ar) and bool(pp_ar) and
        min(cam_ar) > fcyc and min(pp_ar) > fcyc)
    detail['A6'] = dict(fence_retire=fcyc, first_camera_ar=(min(cam_ar) if cam_ar else None),
                        first_pp_ar=(min(pp_ar) if pp_ar else None))

    # ---- side-effect identity ----------------------------------------------
    uart_st = [e for e in e1 if accept(e) and e['dw'] == 1 and e['ds'] == 0b0100]
    ram_st = [e for e in e1 if accept(e) and e['dw'] == 1 and e['ds'] == 0b0010]
    checks['A7_uart_side_effect_once'] = (
        len(uart_st) == 1 and uart_st[0]['da'] == 0x1000_1000 and
        uart_st[0]['dwd'] == 0x0000_0033)
    checks['A8_ram_store_once'] = (
        len(ram_st) == 1 and ram_st[0]['da'] == 0x0000_1000 and
        ram_st[0]['dwd'] == 0x0000_0044)
    detail['A7'] = dict(uart=[(e['n'], hex(e['da']), hex(e['dwd'])) for e in uart_st],
                        ram=[(e['n'], hex(e['da']), hex(e['dwd'])) for e in ram_st])

    # ---- queue accounting: one AW per accepted DDR store -------------------
    checks['A9_aw_per_ddr_store'] = (len(aw1) == len(ddr_st_acc) and len(wf1) == len(aw1))
    detail['A9'] = dict(ddr_stores=len(ddr_st_acc), aw=len(aw1), w=len(wf1))

    # ---- B1: interrupt only after the drain --------------------------------
    irq_ok = len(irqs) == 1
    rec = irqs[0] if irqs else {}
    before_i = [c for c in wf2 if irqs and c < rec['n']]
    busy_before = [e['n'] for e in e2 if late_edge_busy(e) and e['n'] < (rec.get('n') or 0)]
    checks['B1_irq_after_drain'] = (
        irq_ok and rec.get('busy') == 0 and bool(before_i) and rec['n'] > max(before_i) and
        rec['cause'] == IRQ_CAUSE and bool(busy_before))
    checks['B2_irq_cause_external'] = irq_ok and rec.get('cause') == IRQ_CAUSE
    checks['B3_no_trap_while_busy'] = all(e['itk'] == 0 for e in edges if e['busy'] == 1)
    detail['B1'] = dict(traps=len(irqs), trap_edge=rec.get('n'), cause=(hex(rec['cause']) if rec else None),
                        epc=(hex(rec['epc']) if rec else None), busy_at_trap=rec.get('busy'),
                        last_w_before=(max(before_i) if before_i else None),
                        w_beats_ep2=wf2, aw_beats_ep2=len([e for e in e2 if e['awv'] == 1 and e['awr'] == 1]))

    # handler actually ran: MRET path retires back into the spin loop after 0x100
    handler_ret = [r for r in retires if r['ep'] == 2 and 0x4000_0100 <= r['pc'] < 0x4000_0110]
    checks['B4_handler_ran'] = len(handler_ret) >= 3
    detail['B4'] = dict(handler_retires=[hex(r['pc']) for r in handler_ret])

    # ---- M1: final DDR image ----------------------------------------------
    want = {
        0x80: 0x11,        # 0x4000_1000
        0x81: 0x22,        # 0x4000_1020
        0x82: 0x01,        # 0x4000_1040 epoch-1 marker
        0x83: 0xC0DE_0001,  # 0x4000_1060 camera read 1
        0x84: 0xC0DE_0002,  # 0x4000_1080 camera read 2 (uncached, re-read)
        0x85: 0xB0B0_0001,  # 0x4000_10A0 PP read 1
        0x86: 0xB0B0_0002,  # 0x4000_10C0 PP read 2 (uncached, re-read)
        0x100: 0x55,       # 0x4000_2000
        0x101: 0x66,       # 0x4000_2020
        0x102: 0x07,       # 0x4000_2040 handler marker
    }
    bad = {hex(k << 5): (hex(mem.get(k, 0)), hex(v)) for k, v in want.items() if mem.get(k) != v}
    checks['M1_final_ddr_image'] = not bad
    detail['M1'] = dict(mismatch=bad, beats_dumped=len(mem))

    ok = all(checks.values())
    out = dict(task='TASK043_SOC_ORDER', status='PASS' if ok else 'FAIL',
               checks=checks, detail=detail, notes=notes,
               edges=len(edges), retires=len(retires), traps=len(irqs))
    (run / 'check_soc.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    for k, v in checks.items():
        print('%-38s %s' % (k, 'PASS' if v else 'FAIL'))
    for n in notes:
        print('note:', n)
    if not ok:
        print('--- failing detail ---')
        print(json.dumps({k: detail[k.split('_')[0]] for k, v in checks.items() if not v}, indent=2))
    print('RESULT: %s' % out['status'])
    return 0 if ok else 1


def late_edge_busy(e):
    return e['busy'] == 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
