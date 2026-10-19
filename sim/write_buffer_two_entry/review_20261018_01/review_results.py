"""Sol read-only audit of existing Task043 evidence; never runs HDL/checker."""
from collections import Counter, deque
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = ROOT/'sim/write_buffer_two_entry'
COLS = ('cyc rstn init iv ir isv ia idata dv dw ds dr da wd ws dsv ddata '
        'av ardy aa wdata wstrb wrdy arv ardy2 ara rv rid rlast rdata busy').split()
HEX = set('ia idata da wd ws ddata aa wdata wstrb ara rdata'.split())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    assert not (HERE/'review.json').exists(), 'Preserve previous evidence review'
    path = BASE/'key_20261018_b/wb2.edges.log'
    rows, marks, dump = [], {}, {}
    summary = None
    for line_no,line in enumerate(path.read_text().splitlines(), 1):
        w = line.split()
        if w[0] == 'E':
            assert len(w) == len(COLS)+1
            row = {key:(None if any(c in token.lower() for c in 'xz') else int(token,16 if key in HEX else 10))
                   for key,token in zip(COLS,w[1:])}
            row['line'] = line_no
            rows.append(row)
        elif w[0] == 'M':
            marks[w[2]] = int(w[1])
        elif w[0] == 'P':
            dump[int(w[1])] = int(w[2],16)
        elif w[0] == 'S':
            summary = list(map(int,w[1:]))
    q, dfront, ifront = deque(), deque(), deque()
    caches = {0:{}, 1:{}}
    memory = {}  # Only bytes independently known from observed R/W, no invented initial image.
    read = None
    count = Counter()
    problems, cancelled, witnesses = [], [], {}
    load_checks = []

    def check(condition, row, message):
        if not condition:
            problems.append(dict(edge=row['cyc'], line=row['line'], message=message))

    def cache_hit(cache, addr):
        return (addr//32)%64 in cache and cache[(addr//32)%64][0] == addr//32

    for e in rows:
        c = e['cyc']
        if not e['rstn']:
            for ent in q:
                cancelled.append(dict(kind='physical_store', accepted=ent['edge'], reset=c, aw_sent=ent['aw']))
                count['store_cancel'] += 1
                count['aw_cancel'] += bool(ent['aw'])
            for front,name in [(dfront,'D'),(ifront,'I')]:
                for ent in front:
                    cancelled.append(dict(kind=name+'_response', accepted=ent['edge'], reset=c, request_kind=ent['kind']))
                count[name+'_cancel'] += len(front)
                front.clear()
            q.clear()
            caches = {0:{},1:{}}
            read = None
            continue
        check(all(e[key] is not None for key in COLS),e,'undefined live external signal')
        before = len(q)
        check(e['busy'] == bool(before),e,'busy disagrees with PRE-edge independent queue')
        check(not e['arv'] or not q,e,'AR valid before whole queue drained')
        check(not e['av'] or bool(q),e,'AW valid with no head')
        for flag,data,front,name in [('dsv','ddata',dfront,'D'),('isv','idata',ifront,'I')]:
            if e[flag]:
                count[name+'_response'] += 1
                check(bool(front),e,name+' response without a request')
                if front:
                    ent = front.popleft()
                    if ent['kind'] != 'store':
                        check(ent['expected'] is not None,e,'read response before expected R/hit snapshot')
                        check(e[data] == ent['expected'],e,name+' read byte mismatch')
                        load_checks.append(dict(port=name, accepted=ent['edge'], response=c, addr=ent['addr'],
                                                kind=ent['kind'], actual=e[data], expected=ent['expected']))
        aw = e['av'] and e['ardy'] and e['init']
        if aw:
            count['AW'] += 1
            if q:
                check(not q[0]['aw'],e,'AW repeated before head W')
                check(e['aa'] == (q[0]['addr']//32)*8,e,'AW not oldest store line')
                q[0]['aw'] = True
        commit = e['init'] and e['wrdy'] and q and q[0]['aw']
        if commit:
            head = q.popleft()
            count['W'] += 1
            lane = (head['addr']//4)%8
            check(e['wdata'] == head['data'] << (lane*32),e,'W not oldest store data/lane')
            check(e['wstrb'] == head['strb'] << (lane*4),e,'W not oldest store strobe/lane')
            check(e['aa'] == (head['addr']//32)*8,e,'W address not oldest store')
            cache = caches[1]
            for b in range(4):
                if (head['strb']>>b)&1:
                    addr = (head['addr']//4)*4+b
                    memory[addr] = (head['data']>>(8*b))&255
                    if head['hit'] and cache_hit(cache,head['addr']):
                        cache[(head['addr']//32)%64][1][addr%32] = memory[addr]
        accepted_store = bool(e['dv'] and e['dr'] and e['dw'])
        if e['dv'] and e['dr']:
            count['D_accept'] += 1
            addr = e['da']
            ent = dict(edge=c, addr=addr, kind='store' if e['dw'] else 'miss', expected=None)
            if e['dw']:
                count['store_accept'] += 1
                check(len(q)<2,e,'third store accepted without freeing head')
                q.append(dict(edge=c,addr=addr,data=e['wd'],strb=e['ws'],aw=False,hit=cache_hit(caches[1],addr)))
                if cache_hit(caches[0],addr):
                    del caches[0][(addr//32)%64]
            else:
                count['load_accept'] += 1
                if cache_hit(caches[1],addr):
                    ent['kind'] = 'hit'
                    value = list(caches[1][(addr//32)%64][1][(addr%32)//4*4:(addr%32)//4*4+4])
                    for store in q:
                        if store['addr']//4 == addr//4:
                            for b in range(4):
                                if (store['strb']>>b)&1:
                                    value[b] = (store['data']>>(8*b))&255
                    ent['expected'] = int.from_bytes(bytes(value),'little')
                count['D_'+ent['kind']] += 1
            dfront.append(ent)
        if e['iv'] and e['ir']:
            count['I_accept'] += 1
            addr = e['ia']
            hit = cache_hit(caches[0],addr) and not (accepted_store and addr//32==e['da']//32)
            expected = None
            if hit:
                beat = caches[0][(addr//32)%64][1]
                expected = int.from_bytes(bytes(beat[(addr%32)//4*4:(addr%32)//4*4+4]),'little')
            ifront.append(dict(edge=c,addr=addr,kind='hit' if hit else 'miss',expected=expected))
        if e['arv'] and e['ardy2']:
            count['AR'] += 1
            check(read is None,e,'multiple outstanding DDR reads')
            read = dict(base=(e['ara']//8)*32,owner=e['rid'] if e['rv'] else None)
            # Trace omits ARID. Resolve owner from the sole accepted miss's address.
            candidates = [(owner,ent) for owner,front in [(1,dfront),(0,ifront)] for ent in front
                          if ent['kind']=='miss' and ent['expected'] is None and ent['addr']//32==read['base']//32]
            check(len(candidates)==1,e,'AR has no unique accepted miss owner')
            if len(candidates)==1:
                read['owner'],read['request'] = candidates[0]
        if e['rv']:
            count['R'] += 1
            check(read is not None and 'request' in read,e,'R has no unique owned AR')
            if read is not None and 'request' in read:
                check(e['rid']==read['owner'] and e['rlast']==1,e,'R owner/last mismatch')
                beat = list(e['rdata'].to_bytes(32,'little'))
                for b,value in enumerate(beat):
                    addr = read['base']+b
                    if addr in memory:
                        check(memory[addr]==value,e,'R disagrees with previously known DDR byte')
                    memory[addr] = value
                caches[read['owner']][(read['base']//32)%64] = [read['base']//32,beat]
                off = (read['request']['addr']%32)//4*4
                read['request']['expected'] = int.from_bytes(bytes(beat[off:off+4]),'little')
            read = None
        if before==2 and commit and accepted_store:
            witnesses.setdefault('full_pop_push',[]).append(dict(edge=c,line=e['line']))
        count['max_occupancy'] = max(count['max_occupancy'],len(q))
    known_dump_mismatches = []
    for addr,value in memory.items():
        if addr//32 in dump and (dump[addr//32]>>(8*(addr%32)))&255 != value:
            known_dump_mismatches.append(addr)
    segments = {}
    ordered = sorted((v,k) for k,v in marks.items())
    for i,(start,name) in enumerate(ordered):
        end = ordered[i+1][0] if i+1<len(ordered) else rows[-1]['cyc']+1
        part = [e for e in rows if start<=e['cyc']<end]
        segments[name] = dict(start=start,end=end,
            D_accept=sum(bool(e['dv'] and e['dr']) for e in part),
            load_accept=sum(bool(e['dv'] and e['dr'] and not e['dw']) for e in part),
            aw_accept=sum(bool(e['av'] and e['ardy']) for e in part),
            w_ready=sum(bool(e['wrdy']) for e in part),
            same_edge_aw_w=sum(bool(e['av'] and e['ardy'] and e['wrdy']) for e in part),
            R=sum(bool(e['rv']) for e in part))
    assert count['store_accept']==count['W']+count['store_cancel']+len(q)
    assert count['D_accept']==count['D_response']+count['D_cancel']+len(dfront)
    assert count['I_accept']==count['I_response']+count['I_cancel']+len(ifront)
    current_manifest = []
    for line in (BASE/'key_20261018_c/inputs_before.sha256').read_text().splitlines():
        digest,size,name = line.split(None,2)
        p = Path(name)
        current_manifest.append(dict(path=name,recorded=digest,current=sha(p),size=int(size),matches=sha(p)==digest))
    evidence = [p for folder in ['key_20261018_b','key_20261018_c','tmp_probe'] for p in (BASE/folder).glob('*') if p.is_file()]
    sources = [BASE/n for n in ['tb_wb2_bridge.sv','run_wb2.ps1','check_wb2.py']]
    result = dict(status='TASK043_NOT_ACCEPTED_PARTIAL_UNSEALED_TRACE_ONLY',
        bridge_sha256=sha(ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v'),
        evidence_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in evidence+sources},
        raw_b=dict(edges=len(rows),summary=summary,counts=dict(count),
                   trace_consistency_problems=problems,byte_check_count=len(load_checks),
                   load_checks=load_checks,cancelled=cancelled,witnesses=witnesses,
                   known_DDR_bytes=len(memory),known_final_dump_mismatches=known_dump_mismatches,
                   final_pending=dict(stores=len(q),D=len(dfront),I=len(ifront),DDR_read=read is not None),segments=segments),
        c_compile_manifest_current_matches=current_manifest,
        limitations=['b has no sealed inputs/tool command/transcript/exit code; cannot bind it to current RTL or TB.',
                     'b has no initial N records: unobserved DDR bytes cannot be verified.',
                     'ARID/response errors absent from trace; owner inferred only where unique.',
                     'c has compile success, empty vsim.log and no simulation trace/check/meta.',
                     'probe shows RPC socket startup failure; no completed new simulation.',
                     'No user PDS timing-pass receipt recorded; this review authorizes no HDL execution.'])
    (HERE/'review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],counts=dict(count),problems=problems[:4],
                         checked_responses=len(load_checks),known_dump_mismatches=len(known_dump_mismatches),
                         full_pop_push=witnesses,manifest_matches=all(r['matches'] for r in current_manifest)),ensure_ascii=False))

if __name__ == '__main__':
    main()
