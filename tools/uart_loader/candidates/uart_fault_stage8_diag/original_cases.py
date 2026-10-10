"""Stage 8 wire cases for the unchanged stage 7 fixed64 diagnostic firmware."""
import struct
from protocol import packet, expected_response, crc32, FIXED_DATA, DDR_TEST, DDR_CRC_TEST, RX_TEST, DDR_BASE
CRC = crc32(FIXED_DATA)

def cases(native=False, uart_faults=True):
    result = []
    seq = 1
    last = 0
    def add(name, raw, cmd, sequence, status=0, **kw):
        result.append(dict(name=name, tx_hex=raw.hex(), cmd=cmd, seq=sequence, status=status, **kw))
    add('seed_fixed_ddr', packet(DDR_TEST, seq, DDR_BASE, FIXED_DATA), DDR_TEST, seq, attempt=True)
    last = seq; seq += 1
    add('seed_readback_crc', packet(DDR_CRC_TEST, seq, DDR_BASE, image_crc=CRC, length=64), DDR_CRC_TEST, seq, crc_read=True)
    last = seq; seq += 1
    negatives = [
        ('bad_header_crc', 'header_crc', 0x8001),
        ('bad_data_crc', 'data_crc', 0x8001),
        ('bad_empty_data_crc', 'empty_crc', 0x8001),
        ('address_before_base', {'address': DDR_BASE-4}, 0x8002),
        ('address_unaligned1', {'address': DDR_BASE+1}, 0x8002),
        ('address_unaligned2', {'address': DDR_BASE+2}, 0x8002),
        ('address_other_aligned', {'address': DDR_BASE+4}, 0x8002),
        ('address_after_window', {'address': 0x60000000}, 0x8002),
        ('address_wrap', {'address': 0xfffffffc}, 0x8002),
        ('length_zero', {'length': 0}, 0x8003),
        ('length63', {'length': 63}, 0x8003),
        ('length65', {'length': 65}, 0x8003),
        ('length256', {'length': 256}, 0x8003),
        ('length257', {'length': 257}, 0x8003),
        ('length_u32_max', {'length': 0xffffffff}, 0x8003),
        ('total_nonzero', {'total': 64}, 0x8003),
        ('version0', {'version': 0}, 0x8006),
        ('version2', {'version': 2}, 0x8006),
        ('flags_low', {'flags': 1}, 0x8007),
        ('flags_high', {'flags': 0x100}, 0x8007),
        ('load_rejected', {'cmd': 2}, 0x8007),
        ('verify_rejected', {'cmd': 3}, 0x8007),
        ('run_rejected', {'cmd': 4}, 0x8007),
        ('unknown_cmd', {'cmd': 0xff}, 0x8007),
        ('image_state', {'image_crc': 1}, 0x8008),
        ('wrong_fixed_vector', 'wrong_vector', 0x800a),
        ('sequence_stale', 'stale', 0x8009),
        ('sequence_same_other_command', 'same_cmd', 0x8009),
        ('sequence_same_other_crc', 'same_crc', 0x8009),
        ('wrong_ddr_crc_expected', 'wrong_expected', 0x8001),
        ('truncated_magic', 'magic_short', 0x8004),
        ('truncated_header', 'header_short', 0x8004),
        ('truncated_body', 'body_short', 0x8004),
        ('truncated_data_crc', 'tail_short', 0x8004),
        ('bad_header_embedded_valid_packet', 'embedded', 0x8001),
    ]
    if native:
        negatives = [x for x in negatives if x[0] in ('bad_header_crc', 'truncated_body')]
    elif uart_faults:
        negatives += [('uart_low_stop', 'frame', 0x8005), ('uart_fifo_overflow', 'overflow', 0x8005)]
    for name, change, status in negatives:
        params = dict(cmd=DDR_TEST, seq=seq, address=DDR_BASE, payload=FIXED_DATA)
        response_cmd, response_seq = DDR_TEST, seq
        fault = 0
        recover = status != 0x8009 and change != 'wrong_expected'
        read = False
        if isinstance(change, dict): params.update(change); response_cmd = params['cmd']
        elif change == 'empty_crc': params.update(cmd=DDR_CRC_TEST, payload=b'', image_crc=CRC, length=64); response_cmd=DDR_CRC_TEST
        elif change == 'wrong_vector': params['payload'] = FIXED_DATA[:20]+bytes([FIXED_DATA[20]^1])+FIXED_DATA[21:]
        elif change == 'stale': params['seq']=last-1; response_seq=last-1
        elif change == 'same_cmd': params.update(cmd=1, seq=last, address=0, payload=b''); response_cmd=1; response_seq=last
        elif change == 'same_crc': params.update(cmd=DDR_CRC_TEST, seq=last, payload=b'', image_crc=CRC^1, length=64); response_cmd=DDR_CRC_TEST; response_seq=last
        elif change == 'wrong_expected': params.update(cmd=DDR_CRC_TEST, payload=b'', image_crc=CRC^1, length=64); response_cmd=DDR_CRC_TEST; read=True
        raw = packet(**params)
        if change in ('header_crc', 'embedded'):
            raw=raw[:28]+bytes([raw[28]^1])+raw[29:]; response_cmd=response_seq=0
            if change=='embedded': raw += packet(4, 0x12345678) + packet(DDR_TEST, 0x12345679, DDR_BASE, FIXED_DATA)
        elif change in ('data_crc', 'empty_crc'): raw=raw[:-1]+bytes([raw[-1]^1])
        elif change=='magic_short': raw=b'RV'; response_cmd=response_seq=0
        elif change=='header_short': raw=raw[:18]; response_cmd=response_seq=0
        elif change=='body_short': raw=raw[:49]
        elif change=='tail_short': raw=raw[:-2]
        elif change=='frame': raw=b''; response_cmd=response_seq=0; fault=1
        elif change=='overflow': raw=bytes(range(17)); response_cmd=response_seq=0; fault=2
        add(name, raw, response_cmd, response_seq, status, recover=recover, crc_read=read,
            expected_crc=CRC^1 if read else CRC if response_cmd==DDR_CRC_TEST else 0,
            fault=fault, negative=True)
        # Failed new sequence is retried unchanged: proves rejection did not advance sequence.
        if change=='wrong_expected':
            add(name+'_correct_same_seq', packet(DDR_CRC_TEST, seq, DDR_BASE, image_crc=CRC, length=64), DDR_CRC_TEST, seq, crc_read=True)
            last=seq; seq+=1
        add(name+'_recover_ping', packet(1, seq), 1, seq)
        last=seq; seq+=1
        add(name+'_recover_crc', packet(DDR_CRC_TEST, seq, DDR_BASE, image_crc=CRC, length=64), DDR_CRC_TEST, seq, crc_read=True)
        last=seq; seq+=1
    return result

def materialize(folder, selected):
    import json
    requests=bytearray(); responses=bytearray(); lengths=[]; state=[]; ddr=[]; crc=[]; faults=[]
    pings=tests=nacks=last=ddrc=ddrs=crcc=crcr=actual=expected=crcs=0
    for c in selected:
        raw=bytes.fromhex(c['tx_hex']); requests+=raw; lengths.append(len(raw)); faults.append(c.get('fault',0))
        if c.get('attempt'): ddrs=c['status']
        if c.get('crc_read'):
            crcr+=1; actual=CRC; expected=c.get('expected_crc',CRC); crcs=c['status']
        c['actual_crc']=CRC if c.get('crc_read') else 0
        if c['status']: nacks+=1
        else:
            last=c['seq']
            if c['cmd']==1: pings+=1
            elif c['cmd']==DDR_TEST: ddrc+=1
            elif c['cmd']==DDR_CRC_TEST: crcc+=1
        responses+=expected_response(c['seq'], c['cmd'], c['status'], c['actual_crc'], c.get('uart_error_flags',0))
        state += [pings, tests, nacks, last, int(c.get('recover',False)), int(c.get('attempt',False))]
        ddr += [ddrc, int(c.get('attempt',False)), 0, ddrs]
        crc += [crcc, crcr, actual, expected, crcs, int(c.get('crc_read',False)), CRC]
    for name,data in [('requests',requests),('responses',responses)]:
        (folder/(name+'.bin')).write_bytes(data)
        (folder/(name+'.hex')).write_text(''.join(f'{x:02x}\n' for x in data),encoding='ascii')
    for name,values in [('frame_lengths',lengths),('case_state',state),('ddr_state',ddr),('crc_state',crc),('faults',faults)]:
        (folder/(name+'.hex')).write_text(''.join(f'{x:08x}\n' for x in values),encoding='ascii')
    (folder/'cases.json').write_text(json.dumps(selected,indent=2)+'\n',encoding='utf8')
    return bytes(requests), bytes(responses)
