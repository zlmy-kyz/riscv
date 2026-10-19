"""Task032 independent raw trace and command checks. No HDL execution."""
from collections import Counter
from pathlib import Path
import json
import re
from prepare_program import event_line


def read(path):
    return Path(path).read_text(encoding='utf-8').replace('\r\n', '\n')


def unit_trace(path, enabled):
    pending = None
    counts = Counter()
    last_response_cycle = -1
    turns = 0
    for line in read(path).splitlines():
        row = line.split()
        kind, cycle = row[0], int(row[1])
        counts[kind] += 1
        if kind == 'URESET':
            assert pending is not None
            pending = None
        elif kind == 'URSP':
            assert pending is not None and int(row[2]) == pending['target']
            assert int(row[4]) in (0, 1)
            if pending['target'] == 4:
                assert int(row[4]) == 1
            if not int(row[4]):
                assert int(row[3], 16) == pending['token']
            last_response_cycle = cycle
            last_response_error = int(row[4])
            pending = None
        elif kind == 'UREQ':
            assert pending is None
            target, addr = int(row[2]), int(row[3], 16)
            decoded = 0 if addr < 0x4000 else 1 if 0x10000000 <= addr < 0x10001000 else \
                2 if 0x40000000 <= addr < 0x60000000 else 3 if 0x10001000 <= addr < 0x10001010 else 4
            assert target == decoded
            if cycle == last_response_cycle:
                assert enabled and not last_response_error
                turns += 1
            pending = dict(target=target, token=0 if target == 4 else 0x51000000 | target << 16 | addr & 65535)
        else:
            raise ValueError('Unexpected unit record ' + kind)
    assert pending is None and counts['URESET'] == 1
    assert counts['UREQ'] == counts['URSP'] + counts['URESET']
    assert turns == (51 if enabled else 0)
    return dict(counts=dict(counts), turns=turns)


def soc_trace(path, reference, image):
    words = [int(w, 16) for w in read(image).split()]
    memory = {i * 4: word for i, word in enumerate(words[:1024])}
    cpu_pending = None
    writes = []
    accepted_aw = None
    accepted_ar = None
    req_index = 0
    counts = Counter()
    turn_cycles = set()
    last_rsp_cycle = -1
    previous_cycle = -1
    for line in read(path).splitlines():
        row = line.split()
        kind, cycle = row[0], int(row[1])
        assert cycle >= previous_cycle
        previous_cycle = cycle
        counts[kind] += 1
        if kind == 'CPU_RSP':
            assert cpu_pending is not None
            assert int(row[3]) == cpu_pending['error']
            if not cpu_pending['write'] and not cpu_pending['error']:
                assert int(row[2], 16) == cpu_pending['value']
            last_rsp_cycle, last_error = cycle, cpu_pending['error']
            cpu_pending = None
        elif kind == 'CPU_REQ':
            assert cpu_pending is None
            expected = reference['requests'][req_index]
            req_index += 1
            assert [int(row[2]), int(row[3]), int(row[4], 16)] == [expected[k] for k in ('write', 'size', 'addr')]
            if expected['write']:
                assert [int(row[5], 16), int(row[6], 16)] == [expected['data'], expected['strobe']]
            cpu_pending = expected
            if cycle == last_rsp_cycle:
                assert not last_error
                turn_cycles.add(cycle)
            if expected['write'] and 0x40000000 <= expected['addr'] < 0x60000000:
                assert not writes
                writes.append(expected)
        elif kind == 'TURN':
            assert cycle in turn_cycles
        elif kind == 'AW':
            assert writes and accepted_aw is None
            entry = writes[0]
            local = entry['addr'] - 0x40000000
            lane = local >> 2 & 7
            expected = [local >> 5 << 3, entry['data'] << (lane * 32), entry['strobe'] << (lane * 4)]
            assert [int(v, 16) for v in row[2:]] == expected
            accepted_aw = expected
        elif kind == 'W':
            assert writes and accepted_aw is not None
            assert [int(v, 16) for v in row[2:]] == accepted_aw
            entry = writes.pop(0)
            addr = (entry['addr'] - 0x40000000) & ~3
            mask = sum(255 << (8 * lane) for lane in range(4) if entry['strobe'] >> lane & 1)
            memory[addr] = memory.get(addr, 0xa5a5a5a5) & ~mask | entry['data'] & mask
            accepted_aw = None
        elif kind == 'R':
            assert accepted_ar is not None
            addr, rid = accepted_ar
            assert int(row[2]) == rid
            beat = sum(memory.get(addr + 4 * lane, 0xa5a5a5a5) << (32 * lane) for lane in range(8))
            assert int(row[3], 16) == beat, 'Independent DDR read beat mismatch'
            accepted_ar = None
        elif kind == 'AR':
            assert accepted_ar is None
            ctrl, rid = int(row[2], 16), int(row[3])
            assert ctrl & 7 == 0 and rid in (0, 1)
            accepted_ar = ctrl * 4, rid
        elif kind == 'SIDE':
            assert not writes and row[3] == '0'
            counts['SIDE_' + row[2]] += 1
        elif kind == 'FENCE':
            assert not writes and row[2] == '0'
        else:
            raise ValueError('Unexpected SoC record ' + kind)
    assert cpu_pending is None and not writes and accepted_aw is None
    assert req_index == len(reference['requests']) == 49
    assert counts['CPU_REQ'] == counts['CPU_RSP'] == 49
    assert counts['AW'] == counts['W'] == 5
    assert counts['SIDE_MMIO'] == 6 and counts['SIDE_UART'] == 1 and counts['SIDE_RAM'] == 2 and counts['FENCE'] == 1
    assert counts['TURN'] == len(turn_cycles)
    assert memory[0x800] == 0x33444444 and memory[0x804] == memory[0x80c] == 0x11223344 and memory[0x808] == 0xa5a5a5a5
    # Unused speculative I read may remain after PASS; no data request/write may.
    assert accepted_ar is None or accepted_ar[1] == 0
    return dict(counts=dict(counts), turns=len(turn_cycles), CPU_requests=req_index)


def review_job(out, name, project):
    enabled = name == 'key'
    log = read(out / (name + '.log'))
    assert log.strip() == read(out / (name + '.transcript')).strip()
    assert '$finish' in log and 'Errors: 0, Warnings: 0' in log
    assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT', log)
    assert re.findall(r'IPSpecCheck: (\d+)', log) == ['04030130'] * 2
    assert re.findall(r'CHECK: (\w+) PASS cases=(\d+)', log) == [
        ('response_owner_matrix', '24'), ('old_error_blocks', '5'),
        ('posted_write_order', '5'), ('delayed_reset', '2'), ('consecutive_requests', '32')]
    unit_match = re.findall(r'UNIT: pairs=24 errors=5 order=5 burst=32 cycles=(\d+) turns=(\d+) cancelled=1', log)
    assert unit_match == [(str(33 if enabled else 64), str(51 if enabled else 0))]
    summary = re.findall(r'SOC: (.*)', log)
    assert len(summary) == 1
    fields = {k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', summary[0])}
    assert {k: fields[k] for k in ('events','fault','error_rsp','mmio','uart','ram','fence','aw','w')} == \
        dict(events=82, fault=1, error_rsp=1, mmio=5, uart=1, ram=1, fence=1, aw=5, w=5)
    assert fields['fence_wait'] > 0
    assert fields['turns'] > 0 if enabled else fields['turns'] == 0
    here = project / 'sim/data_bus_turnover'
    reference = json.loads(read(here / 'reference.json'))
    assert read(out / (name + '.events.log')).splitlines() == [event_line(e) for e in reference['events']]
    unit = unit_trace(out / (name + '.unit.log'), enabled)
    soc = soc_trace(out / (name + '.bus.log'), reference, here / 'program.dat')
    assert soc['turns'] == fields['turns']
    assert re.findall(r'RESULT: PASS data_bus_turnover key_group TURNOVER=(\d+)', log) == ['1' if enabled else '0']
    return dict(unit=unit, unit_cycles=33 if enabled else 64, soc=soc, fields=fields, Errors=0, Warnings=0)
