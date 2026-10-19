"""Offline independent EV/BUS review; no simulator, PDS or serial calls."""
from collections import Counter
from pathlib import Path
import json
import re
from check_inputs import HERE
from completion_reference import event_line


def text(path):
    return Path(path).read_text(encoding='utf-8').replace('\r\n', '\n')


def overlay_word(memory, address, entry):
    value = memory.get(address & ~3, 0)
    if entry and entry['addr'] & ~3 == address & ~3:
        for lane in range(4):
            if entry['strobe'] >> lane & 1:
                value = (value & ~(255 << (lane * 8))) | (entry['data'] & (255 << (lane * 8)))
    return value


def review_bus(path, reference, image, enabled):
    rows = [line.split() for line in text(path).splitlines() if line.strip()]
    assert rows, 'BUS trace empty'
    words = [int(line, 16) for line in Path(image).read_text().split()]
    memory = {row * 32 + lane * 4: 0x81000000 + row * 32 + lane
              for row in range(128) for lane in range(8)}
    entry = None
    pending_i = pending_d = pending_cpu = None
    short_requests, short_aw, short_w, opportunities = [], [], [], []
    counts, waits = Counter(), Counter()
    soc_request_index = 0
    previous_cycle = -1
    for row in rows:
        kind, cycle = row[0], int(row[1])
        assert cycle >= previous_cycle, 'Nonmonotonic BUS trace'
        previous_cycle = cycle
        counts[kind] += 1
        if kind == 'RESET':
            if entry:
                counts['cancelled'] += 1
            entry = pending_i = pending_d = pending_cpu = None
            if int(row[2]):
                memory = {i * 4: value for i, value in enumerate(words)}
            continue
        if kind == 'INIT':
            continue
        if kind == 'CPU_RSP':
            assert pending_cpu is not None and int(row[3]) == 0
            if not pending_cpu['write']:
                assert int(row[2], 16) == pending_cpu['value'], 'CPU load response mismatch'
            pending_cpu = None
            continue
        if kind == 'CPU_REQ':
            assert pending_cpu is None, 'CPU request slot overwritten'
            expected = reference['requests'][soc_request_index]
            soc_request_index += 1
            assert [int(row[2]), int(row[3]), int(row[4], 16)] == [expected[n] for n in ('write', 'size', 'addr')]
            if expected['write']:
                assert int(row[5], 16) == expected['data'] and int(row[6], 16) == expected['strobe']
            pending_cpu = expected
            continue
        if kind == 'SIDE':
            assert int(row[3]) == 0, 'Non-DDR side effect crossed buffered write'
            counts['SIDE_' + row[2]] += 1
            continue
        if kind == 'SERIAL':
            assert int(row[2]) == 0, 'Serial instruction crossed buffered write'
            continue
        if kind == 'WAIT':
            waits[row[2]] += 1
            continue
        mode, short = int(row[2]), int(row[3])
        if kind == 'OP':
            state, accepted, new_addr, old_addr = int(row[4]), int(row[5]), int(row[6], 16), int(row[7], 16)
            assert entry is None, 'W must be recorded before its OP'
            # W has already cleared the verifier entry; use that W's ownership record.
            assert last_write['addr'] == old_addr and last_write_cycle == cycle
            eligible = state in (0, 5)
            assert accepted == int(enabled and eligible), 'Wrong turnover edge acceptance'
            opportunities.append(dict(cycle=cycle, mode=mode, short=short, state=state,
                                      accepted=accepted, old_addr=old_addr, new_addr=new_addr))
        elif kind == 'AW':
            assert entry is not None and not entry['aw'], 'Duplicate/unowned AW'
            control_addr = int(row[4], 16)
            assert control_addr == (entry['addr'] >> 5) << 3
            entry['aw'] = True
            if short:
                short_aw.append(control_addr)
            if mode:
                counts['SOC_AW'] += 1
        elif kind == 'W':
            assert entry is not None and entry['aw'], 'Unowned W or W before AW'
            control_addr, data, strobe = (int(value, 16) for value in row[4:7])
            lane = entry['addr'] >> 2 & 7
            assert control_addr == (entry['addr'] >> 5) << 3
            assert data == entry['data'] << (lane * 32) and strobe == entry['strobe'] << (lane * 4)
            word = overlay_word(memory, entry['addr'], entry)
            memory[entry['addr'] & ~3] = word
            last_write, last_write_cycle = dict(entry), cycle
            entry = None
            if short:
                short_w.append([last_write['addr'], last_write['data'], last_write['strobe']])
            if mode:
                counts['SOC_W'] += 1
        elif kind == 'CACHE':
            if 'last_write_cycle' in locals() and last_write_cycle == cycle:
                index, data, mask = (int(value, 16) for value in row[4:7])
                lane = last_write['addr'] >> 2 & 7
                assert index == last_write['addr'] >> 5 & 63
                assert data == last_write['data'] << (lane * 32)
                assert mask == last_write['strobe'] << (lane * 4)
                counts['cache_store_updates'] += 1
            else:
                assert int(row[6], 16) == 0xffffffff, 'Fill must write every byte'
                counts['cache_fills'] += 1
        elif kind == 'DREQ':
            assert pending_d is None, 'D response slot overwritten'
            write, size, address, data, mask = int(row[4]), int(row[5]), int(row[6], 16), int(row[7], 16), int(row[8], 16)
            pending_d = 0 if write else overlay_word(memory, address, entry)
            if write:
                assert entry is None, 'Second posted write accepted before completion'
                entry = dict(addr=address, data=data, strobe=mask, aw=False)
                counts['stores'] += 1
                if short:
                    short_requests.append([address, data, mask])
                if mode:
                    counts['SOC_stores'] += 1
        elif kind == 'DRSP':
            assert pending_d is not None and int(row[5]) == 0
            assert int(row[4], 16) == pending_d, 'D response value mismatch'
            pending_d = None
        elif kind == 'IREQ':
            assert pending_i is None
            pending_i = overlay_word(memory, int(row[4], 16), entry)
        elif kind == 'IRSP':
            assert pending_i is not None and int(row[5]) == 0
            assert int(row[4], 16) == pending_i, 'I response value mismatch'
            pending_i = None
        else:
            raise ValueError('Unknown BUS row: ' + str(row))
    assert entry is None and pending_d is None and pending_cpu is None, 'Unfinished data transaction'
    # An unused instruction fetch may remain after the software's final PASS store.
    assert counts['stores'] == counts['W'] + counts['cancelled']
    assert counts['AW'] == counts['W'], 'Cancelled fixture store must not have acquired AW'
    expected_short = [[0x800, 0xa1, 15], [0x804, 0xa2, 15], [0x808, 0xa3, 15],
                      [0x80c, 0xa4, 15], [0x810, 0x5000, 3], [0x814, 0x6000, 12]]
    assert short_requests == short_w == expected_short and len(short_aw) == 6
    short_op = [row for row in opportunities if row['short']]
    assert len(short_op) == 5 and sum(row['accepted'] for row in short_op) == (5 if enabled else 0)
    if enabled:
        assert soc_request_index == len(reference['requests'])
        assert counts['SOC_stores'] == counts['SOC_AW'] == counts['SOC_W'] == 73
        assert counts['cancelled'] == 1 and len(opportunities) == 82
        assert sum(row['accepted'] for row in opportunities) == 81
        late = [row for row in opportunities if not row['accepted']]
        assert len(late) == 1 and late[0]['mode'] == 1 and late[0]['state'] not in (0, 5)
        for address, value in reference['final_words'].items():
            assert memory[int(address, 16) - 0x40000000] == value
        assert waits == dict(IRQ=26, FENCE=49, STOP=26)
        assert all(counts['SIDE_' + name] > 0 for name in ('MMIO', 'UART', 'RAM'))
        assert counts['cache_store_updates'] == 203 and counts['cache_fills'] == 12
    soc_opportunities = [row for row in opportunities if row['mode']]
    return dict(counts=dict(counts), waits=dict(waits), opportunities=opportunities,
                SoC_opportunities=len(soc_opportunities),
                SoC_accepted=sum(row['accepted'] for row in soc_opportunities),
                short_complete_writes=short_w, CPU_requests_checked=soc_request_index)


def review_job(out, name, manifest):
    log = text(out / (name + '.log'))
    assert log.strip() == text(out / (name + '.transcript')).strip()
    assert '$finish' in log and 'Errors: 0, Warnings: 0' in log
    assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT', log)
    assert re.findall(r'IPSpecCheck: (\d+)', log) == ['04030130'] * 4
    groups = re.findall(r'CHECK: (\w+) PASS checks=(\d+)', log)
    events = text(out / (name + '.events.log')).splitlines()
    enabled = name == 'key'
    if enabled:
        assert groups == [(g['name'], str(g['checks'])) for g in manifest['groups']]
        assert events == [event_line(event) for event in json.loads(text(HERE / 'completion_reference.json'))['events']]
        expected = manifest['key_result_fields']
        result_lines = [line for line in log.splitlines() if 'RESULT: PASS write_buffer_turnover_x32 ' in line]
        assert len(result_lines) == 1
        fields = {k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', result_lines[0])}
        assert fields == expected, (fields, expected)
    else:
        assert not groups and not events
        assert re.findall(r'RESULT: PASS write_buffer_turnover_control tests=(\d+)', log) == ['6']
    short = re.findall(r'SHORT: cycles=(\d+) stores=(\d+) opportunities=(\d+) accepted=(\d+) late=(\d+) aw=(\d+) w=(\d+)', log)
    assert len(short) == 1
    assert list(map(int, short[0][:5])) == ([44, 6, 5, 5, 0] if enabled else [49, 6, 5, 0, 5])
    reference = json.loads(text(HERE / 'completion_reference.json'))
    bus = review_bus(out / (name + '.bus.log'), reference, HERE / manifest['image_relative_to_here'], enabled)
    return dict(cycles=int(short[0][0]), events_checked=len(events), tests=889 if enabled else 6,
                bus=bus, Errors=0, Warnings=0)
