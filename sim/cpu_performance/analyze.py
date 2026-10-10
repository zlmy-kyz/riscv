"""Independent retirement/metric checks and machine-readable summaries."""
from collections import Counter, defaultdict
from pathlib import Path
import csv
import json
import math

BASE = 0x40000000
HZ = 93750000


def metrics(folder):
    result = defaultdict(dict)
    for row in csv.DictReader((folder / 'metrics.csv').open()):
        w = int(row['window'])
        if row['metric'] in result[w]:
            raise ValueError('duplicate metric')
        result[w][row['metric']] = int(row['value'])
    return dict(result)


def check_partition(m):
    keys = ['if_stall_cycles', 'mem_stall_cycles', 'branch_flush_cycles',
            'control_redirect_cycles', 'control_hold_cycles', 'load_use_cycles', 'other_cycles']
    assert m['cycles'] == sum(m[k] for k in keys), 'exclusive partition'
    assert m['ddr_transactions'] == m['ddr_ar_commands'] + m['ddr_aw_commands']
    for c, prefix in enumerate(['if', 'data']):
        assert m[prefix + '_requests'] - m[prefix + '_responses'] == m[f'pending_{c}_end'] - m[f'pending_{c}_start']
    assert m['cycles'] == sum(m[k] for k in ['bridge_idle_cycles', 'bridge_raddr_cycles',
           'bridge_rdata_cycles', 'bridge_waddr_cycles', 'bridge_wdata_cycles', 'bridge_rsp_state_cycles'])


def signed(value, bits=32):
    return (value & ((1 << bits)-1)) - ((1 << bits) if value & (1 << (bits-1)) else 0)


def check_micro_trace(folder, binary):
    """Execute the actual linked RV32I stream against a separate byte memory.

    Timer values are deliberately ignored: they do not control the workload.
    Each other architectural RF write and the next retired PC must match.
    """
    memory = bytearray(65536)
    memory[:len(binary)] = binary
    regs = [0] * 32
    pc = BASE
    rows = list(csv.DictReader((folder / 'retire_trace.csv').open()))
    counts = Counter()
    for row in rows:
        actual_pc = int(row['pc'], 16)
        # The ROM jump can retire after the first DDR request has been accepted.
        if actual_pc < BASE:
            continue
        assert actual_pc == pc, f'PC expected={pc:08x} actual={actual_pc:08x}'
        w = int.from_bytes(memory[pc-BASE:pc-BASE+4], 'little')
        op, rd, f3, r1, r2, f7 = w&127, (w>>7)&31, (w>>12)&7, (w>>15)&31, (w>>20)&31, w>>25
        a, b = regs[r1], regs[r2]
        nxt, value, writes, timer = pc+4, 0, False, False
        imm_i = signed(w>>20, 12)
        if op == 0x37: value, writes = w & 0xfffff000, True
        elif op == 0x17: value, writes = pc + (w & 0xfffff000), True
        elif op == 0x13:
            writes = True
            if f3 == 0: value = a + imm_i
            elif f3 == 1: value = a << ((w>>20)&31)
            elif f3 == 2: value = int(signed(a) < imm_i)
            elif f3 == 3: value = int(a < (imm_i & 0xffffffff))
            elif f3 == 4: value = a ^ (imm_i & 0xffffffff)
            elif f3 == 5: value = (signed(a) if f7 == 32 else a) >> ((w>>20)&31)
            elif f3 == 6: value = a | (imm_i & 0xffffffff)
            elif f3 == 7: value = a & (imm_i & 0xffffffff)
        elif op == 0x33:
            assert f7 in (0,32), 'unexpected extension'
            writes = True
            if f3 == 0: value = a-b if f7==32 else a+b
            elif f3 == 1: value = a << (b&31)
            elif f3 == 2: value = int(signed(a)<signed(b))
            elif f3 == 3: value = int(a<b)
            elif f3 == 4: value = a^b
            elif f3 == 5: value = (signed(a) if f7==32 else a) >> (b&31)
            elif f3 == 6: value = a|b
            elif f3 == 7: value = a&b
        elif op in (0x03,0x23):
            imm_s = signed(((w>>25)<<5) | ((w>>7)&31),12)
            address = (a + (imm_i if op==3 else imm_s)) & 0xffffffff
            size = 1 << (f3&3)
            assert size in (1,2,4) and address % size == 0
            if op == 3:
                writes=True
                if address==0x10000008:
                    timer=True; value=0
                else:
                    assert BASE <= address <= BASE+65536-size
                    value=int.from_bytes(memory[address-BASE:address-BASE+size],'little')
                    if f3 < 4: value=signed(value,size*8)
            elif BASE <= address <= BASE+65536-size:
                memory[address-BASE:address-BASE+size]=(b&((1<<(8*size))-1)).to_bytes(size,'little')
            else:
                assert address in (0x10000000,0x10000010), 'unexpected MMIO store'
        elif op == 0x63:
            offset=signed(((w>>31)<<12)|(((w>>7)&1)<<11)|(((w>>25)&63)<<5)|(((w>>8)&15)<<1),13)
            taken = {0:a==b,1:a!=b,4:signed(a)<signed(b),5:signed(a)>=signed(b),6:a<b,7:a>=b}[f3]
            if taken: nxt=pc+offset
        elif op == 0x6f:
            offset=signed(((w>>31)<<20)|(((w>>12)&255)<<12)|(((w>>20)&1)<<11)|(((w>>21)&1023)<<1),21)
            value,writes,nxt=pc+4,True,pc+offset
        elif op == 0x67:
            value,writes,nxt=pc+4,True,(a+imm_i)&~1
        elif op == 0x0f: pass
        else: raise ValueError(f'unsupported opcode pc={pc:08x} word={w:08x}')
        effective_write = writes and rd != 0
        assert bool(int(row['write'])) == effective_write, f'write enable at {pc:08x}'
        if effective_write:
            assert int(row['rd']) == rd
            if not timer:
                assert int(row['value'],16) == value & 0xffffffff, f'RF write at {pc:08x}'
            regs[rd]=value&0xffffffff
        regs[0]=0
        pc=nxt&0xffffffff
        if int(row['window']): counts[int(row['window'])]+=1
    return dict(retired_ddr_instructions=sum(1 for r in rows if int(r['pc'],16)>=BASE),
                retire_count_by_window=dict(counts), final_a0=regs[10])


def summarize(folder, manifest, engine):
    measured=metrics(folder)
    timers={int(r['window']):int(r['ticks']) for r in csv.DictReader((folder/'timer.csv').open())}
    hist=defaultdict(list)
    for row in csv.DictReader((folder/'latency.csv').open()):
        hist[(int(row['window']),int(row['channel']))].append((int(row['latency_cycles']),int(row['count'])))
    rows=[]
    pc_counts=defaultdict(Counter)
    for row in csv.DictReader((folder/'retire_pc.csv').open()):
        pc_counts[int(row['window'])][int(row['pc'],16)] += int(row['count'])
    for case in manifest['cases']:
        w=case['id']; m=measured[w]
        check_partition(m)
        assert sum(pc_counts[w].values())==m['instret'], 'PC histogram and retirement count'
        assert m['cycles']==timers[w], 'accepted CYCLE reads and monitor window differ'
        lat={}
        for c,name in enumerate(['IF','data']):
            bins=sorted(hist[(w,c)])
            total=sum(n for x,n in bins)
            assert total==m[('if' if c==0 else 'data')+'_responses']
            def percentile(p):
                threshold=math.ceil(total*p)
                acc=0
                for value,n in bins:
                    acc+=n
                    if acc>=threshold: return value
                return None
            lat[name]=dict(completed_responses=total, min=bins[0][0] if bins else None,
                p50=percentile(.5), p95=percentile(.95), max=bins[-1][0] if bins else None,
                mean=sum(x*n for x,n in bins)/total if total else None,
                population='responses within [S,T); may include request before S; pending at T censored',
                overflow_bin_4096='latency >=4096 cycles')
        rows.append(dict(**case, **m, cpi=m['cycles']/m['instret'], seconds=m['cycles']/HZ,
                         cycles_per_unit=m['cycles']/case['units'], latency=lat))
    result=dict(status='PASS', engine=engine,
                performance_evidence=engine.startswith('physical'), clock_hz=HZ, windows=rows)
    if manifest['kind']=='micro':
        oracle=check_micro_trace(folder,Path(manifest['bin_path']).read_bytes())
        assert {r['id']:r['instret'] for r in rows}==oracle['retire_count_by_window']
        result['retirement_oracle']=oracle
    else:
        import re
        symbol_path=Path(manifest['original']['bin_path']).with_name('symbols.txt')
        symbol_path=Path(__file__).resolve().parents[2]/symbol_path
        aliases=defaultdict(list)
        for address,kind,name in re.findall(r'^([0-9a-f]+)\s+(\w)\s+(\S+)$',symbol_path.read_text(),re.M):
            if kind in ('t','T'): aliases[int(address,16)].append(name)
        ordered=sorted(aliases)
        function_counts=Counter()
        for pc,count in pc_counts[1].items():
            import bisect
            index=bisect.bisect_right(ordered,pc)-1
            assert index>=0
            function_counts['/'.join(aliases[ordered[index]])]+=count
        total=measured[1]['instret']
        result['instruction_profile']=[dict(function=name,instret=n,share=n/total)
            for name,n in function_counts.most_common()]
        result['profile_scope']='dynamic instruction counts in this exact one-iteration BIN; not physical stall/time shares'
    (folder/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
