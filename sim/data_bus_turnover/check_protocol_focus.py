"""Compact independent reference for Task032's critical bridge cases."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BRIDGE_SHA = 'f14b16cb97fa24fd17050995a1b254933aea5bca3b4a071a33712c7a17c52ba0'
# Addresses are DDR-local byte addresses, as at the actual bridge input.
PLAN = []


def add(case, target, addr, write=0, size=2, data=0, strobe=0, cancel=False):
    PLAN.append(dict(id=len(PLAN), case=case, target=target, addr=addr, write=write,
                     size=size, data=data, strobe=strobe, cancel=bool(cancel)))


add(1, 0, 0)
for lane in range(8):
    add(1, 0, lane * 4)
add(2, 0, 0)                         # old hit response
add(2, 0, 12)                        # younger I loses to the D request
add(2, 1, 13, 1, 0, 0x0000b700, 2)   # SB in word lane 3, byte lane 1
add(3, 1, 0x100, 1, 2, 0x11223344, 15)
add(3, 0, 0)
add(3, 0, 0x100)
add(3, 0, 0x100)
add(4, 0, 0x180)
add(5, 0, 0, cancel=True)
add(5, 0, 0)
add(6, 0, 0x200, cancel=True)
add(6, 0, 0x200)
add(7, 0, 0x280, cancel=True)
add(7, 0, 0x280)
CONTRACT = dict(cases=7, tokens=23, responses=20, cancels=[17,19,21],
                immediate_read_tokens=[0,10,14], delayed_read_token=16,
                priority_old=9, priority_i=10, priority_d=11,
                partial_store=11, blocked_store=12, blocked_read=14,
                snapshot_miss=16, lane_hits=list(range(1,9)))
FIELDS = 'edge case rst init itok iv ir ia dtok dv dr dw ds da dd dstrb ip idata ie dp ddata de arv arr ara ari awv awr awa wd ws wr rv rd ri rl busy'.split()
HEX_FIELDS = set('ia da dd dstrb idata ddata ara awa wd ws rd'.split())


def emit_plan(path):
    lines = ['// Generated from the sealed, pre-execution stimulus contract.',
             'localparam integer TOKEN_COUNT = 23;', 'task automatic load_plan;', 'begin']
    for p in PLAN:
        i = p['id']
        lines += [f"p_case[{i}]={p['case']}; p_tgt[{i}]={p['target']}; p_cancel[{i}]={int(p['cancel'])};",
                  f"p_addr[{i}]=32'h{p['addr']:08x}; p_wr[{i}]={p['write']}; p_size[{i}]={p['size']};",
                  f"p_data[{i}]=32'h{p['data']:08x}; p_strb[{i}]=4'h{p['strobe']:x};"]
    lines += ['end', 'endtask', '']
    text = '\n'.join(lines)
    path = Path(path)
    if path.exists():
        assert path.read_text(encoding='utf-8') == text, 'Do not replace a different stimulus plan'
    else:
        path.write_text(text, encoding='utf-8')


def parse(path):
    edges, summary = [], None
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        f = line.split()
        if not f:
            continue
        if f[0] == 'E':
            assert len(f) == len(FIELDS) + 1, f
            edges.append({k:int(v,16 if k in HEX_FIELDS else 10) for k,v in zip(FIELDS,f[1:])})
        elif f[0] == 'SUM':
            assert summary is None
            summary = {k:int(v) for k,v in (x.split('=') for x in f[1:])}
        else:
            raise AssertionError('Unexpected trace record: ' + line)
    assert edges and summary is not None
    assert [e['edge'] for e in edges] == list(range(1,len(edges)+1))
    return edges, summary


def word(bs, lane):
    return sum(bs[4*lane+j] << (8*j) for j in range(4))


def review(edge_path, plan_path):
    expected_plan = [dict(p, cancel=int(p['cancel'])) for p in PLAN]
    printed = [json.loads(line) for line in Path(plan_path).read_text(encoding='utf-8').splitlines()]
    assert printed == expected_plan, 'Stimulus identity/scenario/cancel mismatch'
    edges, summary = parse(edge_path)
    memory = [((i & 255)*43+90)&255 for i in range(4096)]
    cache = {}                       # index -> (full local line address, 32 bytes)
    state = ['planned']*len(PLAN)
    accepted_at, responded_at, kind = {}, {}, {}
    cpu = None                       # one old front-slot owner
    read_owner = None
    store_owner = None               # posted physical owner, separate from CPU ACK
    aw_at = None
    read_beat, read_at, ar_at = {}, {}, {}
    counts = dict(accepts=0,responses=0,cancels=0,ar=0,r=0,aw=0,w=0)
    covers = dict(same_ar_r=[], dual=[], response_turns=0, ar_backpressure=0,
                  posted_block=0, lanes=[], partial_writes=0, reset_cases=[])
    old_reset = False
    previous = None
    for e in edges:
        for k in 'rst init iv ir dv dr dw ip ie dp de arv arr awv awr wr rv rl busy'.split():
            assert e[k] in (0,1), (e['edge'],k,e[k])
        reset_entry = not e['rst'] and not old_reset
        old_reset = not e['rst']
        if not e['rst']:
            assert not e['iv'] and not e['dv'], 'Requests held through reset'
            if cpu is not None:
                assert reset_entry and PLAN[cpu]['cancel']
                state[cpu] = 'cancelled'
                counts['cancels'] += 1
                covers['reset_cases'].append([PLAN[cpu]['case'],cpu,e['edge']])
            cpu = read_owner = store_owner = aw_at = None
            cache.clear()
            previous = e
            continue
        assert e['init'] == 1
        ia, da = bool(e['iv'] and e['ir']), bool(e['dv'] and e['dr'])
        assert not (ia and da), 'I and D accepted on the same edge'
        arp, awp = bool(e['arv'] and e['arr']), bool(e['awv'] and e['awr'])
        wp = bool(e['wr'] and (aw_at is not None or awp))
        rp = bool(e['rv'])
        if e['iv'] and e['dv'] and e['dr']:
            assert not e['ir'] and da
            covers['dual'].append([e['edge'],e['itok'],e['dtok']])
        # Stable request/AR/AW fields while their old owner is backpressured.
        if previous is not None and previous['rst']:
            for valid, ready, keys in [('iv','ir',['itok','ia']),
                                        ('dv','dr',['dtok','dw','ds','da','dd','dstrb']),
                                        ('arv','arr',['ara','ari']),
                                        ('awv','awr',['awa','wd','ws'])]:
                if previous[valid] and not previous[ready]:
                    assert e[valid] and all(e[k]==previous[k] for k in keys), (e['edge'],keys)
        # OLD CPU response before any invalidation/new acceptance this edge.
        if e['ip'] or e['dp']:
            assert not (e['ip'] and e['dp']) and cpu is not None
            p = PLAN[cpu]
            assert e['ip'] == int(p['target']==0) and e['dp'] == int(p['target']==1)
            assert not (e['ie'] if p['target']==0 else e['de'])
            if p['write']:
                assert e['edge']==accepted_at[cpu]+1
            elif kind[cpu][0]=='hit':
                assert e['idata']==kind[cpu][1] and e['edge']==accepted_at[cpu]+1
                if cpu in CONTRACT['lane_hits']:
                    covers['lanes'].append((p['addr']>>2)&7)
            else:
                assert cpu in read_beat and e['edge']==read_at[cpu]+1
                assert e['idata']==word(read_beat[cpu],(p['addr']>>2)&7)
            state[cpu] = 'responded'
            responded_at[cpu] = e['edge']
            counts['responses'] += 1
            if ia or da:
                covers['response_turns'] += 1
            if read_owner == cpu:
                read_owner = None
            cpu = None
        # Commands/R consume OLD memory; W is committed only afterwards.
        if arp:
            assert read_owner is not None and read_owner not in ar_at
            p = PLAN[read_owner]
            assert e['ara']==(p['addr']>>5)*8 and e['ari']==p['target']
            assert not e['busy']
            ar_at[read_owner] = e['edge']
            counts['ar'] += 1
        if rp:
            assert read_owner is not None and read_owner in ar_at
            p = PLAN[read_owner]
            bs = [memory[((p['addr'] & ~31)+j)&4095] for j in range(32)]
            assert e['rd']==sum(b<<(8*j) for j,b in enumerate(bs))
            assert e['ri']==p['target'] and e['rl']==1
            assert read_owner not in read_beat
            read_beat[read_owner], read_at[read_owner] = bs, e['edge']
            cache[(p['addr']>>5)&63] = (p['addr']>>5, list(bs))
            counts['r'] += 1
            if arp:
                covers['same_ar_r'].append([read_owner,e['edge']])
        if awp:
            assert store_owner is not None and aw_at is None
            p = PLAN[store_owner]
            assert e['awa']==(p['addr']>>5)*8
            aw_at = e['edge']
            counts['aw'] += 1
        if store_owner is not None and aw_at is not None:
            p = PLAN[store_owner]
            assert e['awa']==(p['addr']>>5)*8
            assert e['wd']==p['data'] << (32*((p['addr']>>2)&7))
            assert e['ws']==p['strobe'] << (4*((p['addr']>>2)&7))
        if wp:
            assert store_owner is not None
            p = PLAN[store_owner]
            for j in range(4):
                if (p['strobe']>>j)&1:
                    memory[((p['addr']&~3)+j)&4095]=(p['data']>>(8*j))&255
            covers['partial_writes'] += int(p['strobe']!=15)
            store_owner = aw_at = None
            counts['w'] += 1
        # NEW accepted token is named by the pre-edge presented stimulus.
        if ia or da:
            assert cpu is None
            tid = e['itok'] if ia else e['dtok']
            assert 0 <= tid < len(PLAN) and state[tid]=='planned'
            p = PLAN[tid]
            assert p['case']==e['case'] and p['target']==int(da)
            assert (e['ia'] if ia else e['da'])==p['addr']
            if da:
                assert [e[k] for k in ['dw','ds','dd','dstrb']]==[p[k] for k in ['write','size','data','strobe']]
            state[tid], accepted_at[tid], cpu = 'accepted', e['edge'], tid
            counts['accepts'] += 1
            if p['write']:
                assert store_owner is None
                store_owner = tid
                idx = (p['addr']>>5)&63
                if idx in cache and cache[idx][0]==p['addr']>>5:
                    del cache[idx]
                kind[tid] = ('store',None)
            else:
                idx = (p['addr']>>5)&63
                if idx in cache and cache[idx][0]==p['addr']>>5:
                    kind[tid] = ('hit',word(cache[idx][1],(p['addr']>>2)&7))
                else:
                    kind[tid] = ('miss',None)
                    assert read_owner is None
                    read_owner = tid
        if read_owner is not None and read_owner not in ar_at and e['edge']>accepted_at[read_owner]:
            if e['busy']:
                assert not e['arv']
                covers['posted_block'] += 1
            else:
                assert e['arv'], 'Missing earliest eligible AR'
                covers['ar_backpressure'] += int(not e['arr'])
            assert not e['ip']
        if cpu is None and not (e['iv'] or e['dv']):
            assert not (e['ip'] or e['dp']) or (e['edge'] in responded_at.values())
        previous = e
    assert cpu is None and read_owner is None and store_owner is None
    assert state == ['cancelled' if p['cancel'] else 'responded' for p in PLAN]
    assert counts['accepts']==23 and counts['responses']==20 and counts['cancels']==3
    assert counts['ar']==counts['r']+1 and counts['aw']==counts['w']==2
    assert set(covers['lanes'])==set(range(8))
    assert {tid for tid,_ in covers['same_ar_r']} >= set(CONTRACT['immediate_read_tokens'])
    assert any(i==10 and d==11 for _,i,d in covers['dual'])
    assert covers['partial_writes']==1 and covers['ar_backpressure']>=3 and covers['posted_block']>=3
    assert [tid for _,tid,_ in covers['reset_cases']]==CONTRACT['cancels']
    assert ar_at[14] > accepted_at[14]+1
    assert responded_at[1]+1==responded_at[2]             # truly consecutive hits
    assert set(summary)=={'accepts','responses','cancels','edges'}
    assert summary==dict(accepts=23,responses=20,cancels=3,edges=len(edges))
    return dict(status='PROTOCOL_FOCUS_REFERENCE_PASS', counts=counts, coverage=covers, edges=len(edges))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--emit-plan', type=Path)
    p.add_argument('--edge-log', type=Path)
    p.add_argument('--plan-log', type=Path)
    a = p.parse_args()
    if a.emit_plan:
        emit_plan(a.emit_plan)
        print('Static stimulus include prepared; HDL NOT_RUN')
    else:
        print(json.dumps(review(a.edge_log,a.plan_log),indent=2))


if __name__=='__main__':
    main()
