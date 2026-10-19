"""Sol offline audit: sealed inputs, raw transactions, bytes and comparisons.

Does not execute HDL, the submitted checker, runner or environment scripts.
"""
from collections import Counter, deque
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = ROOT/'sim/write_buffer_two_entry'
COLS = ('cyc rstn init iv ir isv ia idata dv dw ds dr da wd ws dsv ddata '
        'av ardy aa wdata wstrb wrdy arv ardy2 ara rv rid rlast rdata busy').split()
HEX = set('ia idata da wd ws ddata aa wdata wstrb ara rdata'.split())
TAGS = ['xs_key_20261018_c', 'xs_short_old_20261018_c',
        'xs_short_new_d1_20261018_c', 'xs_short_new_d2_20261018_c',
        'xs_compat_noturnover_20261018_c', 'xs_compat_no_forward_20261018_c',
        'xs_compat_linebuf_off_20261018_c']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_trace(path):
    rows, marks, initial, final = [], {}, {}, {}
    summary = None
    for line_no,line in enumerate(path.read_text().splitlines(),1):
        w = line.split()
        if not w:
            continue
        if w[0]=='E':
            assert len(w)==len(COLS)+1
            row = {key:(None if any(c in token.lower() for c in 'xz') else int(token,16 if key in HEX else 10))
                   for key,token in zip(COLS,w[1:])}
            row['line']=line_no
            rows.append(row)
        elif w[0]=='M':
            assert w[2] not in marks
            marks[w[2]]=int(w[1])
        elif w[0] in ['N','P']:
            target = initial if w[0]=='N' else final
            assert int(w[1]) not in target
            target[int(w[1])]=int(w[2],16)
        elif w[0]=='S':
            summary=list(map(int,w[1:]))
    return rows,marks,initial,final,summary

def audit(tag):
    run=BASE/tag
    meta=json.loads((run/'run_meta.json').read_text(encoding='utf-8-sig'))
    manifest={}
    assert (run/'inputs_before.sha256').read_bytes()==(run/'inputs_after.sha256').read_bytes()
    for line in (run/'inputs_before.sha256').read_text().splitlines():
        digest,size,name=line.split(None,2)
        source=run/'src'/name
        assert sha(source)==digest and source.stat().st_size==int(size),source
        manifest[name]=digest
        if source.suffix in ['.v','.sv','.vh','.svh']:
            for include in re.findall(r'`include\s+"([^"]+)"',source.read_text(errors='replace')):
                assert (source.parent/include).exists(), (source,include)
    expected_bridge='57f13e335ebcbba9b1d45ff4712284f4786d8291041c0d80ad82138309a95b35' if meta['legacy'] else '855318eebf7fc75a0b17d15a620b6d8d08bb54ff9348d663cbcd6aca0883262f'
    assert manifest['myriscv\\dual_sram_to_pango_ddr_bridge.v']==expected_bridge
    assert meta['status']=='PASS' and all(v==0 for v in meta['exits'].values())
    assert meta['identity_drift']==0 and meta['check_status']=='PASS'
    for cmd in meta['commands']:
        if 'xvlog.bat' in cmd:
            assert 'src\\myriscv\\dual_sram_to_pango_ddr_bridge.v' in cmd
    raw=(run/'log_xsim.txt').read_text(errors='replace')
    assert 'RESULT: PASS' in raw and not any(t in raw for t in ['RESULT: FAIL','Fatal:','FATAL_ERROR'])
    diagnostic=[line for line in raw.splitlines() if 'IPSpecCheck:' in line]
    rows,marks,initial,final,summary=read_trace(run/'wb2.edges.log')
    assert set(initial)==set(final)==set(range(256))
    physical={32*line+b:(word>>(8*b))&255 for line,word in initial.items() for b in range(32)}
    architectural=dict(physical)
    q,dfront,ifront=deque(),deque(),deque()
    cache_tags={0:{},1:{}}
    count=Counter()
    issues,witness,reads,accepts,awbeats,wbeats=[],[],[],[],[],[]
    read=None
    cfg=meta['params']
    def check(condition,e,message):
        if not condition:
            issues.append(dict(edge=e['cyc'],line=e['line'],message=message))
    def word(memory,addr):
        return sum(memory[(addr//4)*4+b]<<(8*b) for b in range(4))
    prev=None
    for e in rows:
        c=e['cyc']
        if not e['rstn']:
            count['store_cancel']+=len(q)
            count['AW_cancel']+=sum(ent['aw'] for ent in q)
            count['D_cancel']+=len(dfront)
            count['I_cancel']+=len(ifront)
            q.clear();dfront.clear();ifront.clear()
            cache_tags={0:{},1:{}}
            architectural=dict(physical)
            read=None
            prev=e
            continue
        check(all(e[key] is not None for key in COLS),e,'undefined live external field')
        if prev is not None and prev['rstn'] and prev['dv'] and not prev['dr']:
            check(e['dv'] and all(e[k]==prev[k] for k in ['dw','ds','da','wd','ws']),e,'held D request withdrawn/changed before acceptance')
        before=list(q)
        check(bool(e['busy'])==bool(q),e,'busy does not describe whole PRE-edge queue')
        check(not e['arv'] or not q,e,'AR before whole queue empty')
        check(not e['av'] or bool(q),e,'AW with no queued head')
        for flag,data,front,owner in [('dsv','ddata',dfront,'D'),('isv','idata',ifront,'I')]:
            if e[flag]:
                count[owner+'_response']+=1
                check(bool(front),e,'response without accepted '+owner)
                if front:
                    ent=front.popleft()
                    if ent['kind']!='store':
                        check(e[data]==ent['expected'],e,owner+' read differs from independent byte memory')
                        reads.append(dict(port=owner,accepted=ent['edge'],response=c,addr=ent['addr'],actual=e[data],expected=ent['expected']))
        aw=e['init'] and e['av'] and e['ardy']
        if aw and q:
            count['AW']+=1
            check(not q[0]['aw'],e,'AW repeated for old head')
            check(e['aa']==q[0]['addr']//32*8,e,'AW not oldest address')
            q[0]['aw']=True
            awbeats.append(e['aa'])
        commit=bool(e['init'] and e['wrdy'] and q and q[0]['aw'])
        if commit:
            count['W']+=1
            head=q.popleft()
            lane=head['addr']//4%8
            check(e['wdata']==head['data']<<(lane*32),e,'W data/lane differs from oldest store')
            check(e['wstrb']==head['strb']<<(lane*4),e,'W strobe/lane differs from oldest store')
            check(e['aa']==head['addr']//32*8,e,'W address differs from oldest store')
            for b in range(4):
                if (head['strb']>>b)&1:
                    physical[head['addr']//4*4+b]=(head['data']>>(8*b))&255
            wbeats.append([e['aa'],e['wdata'],e['wstrb']])
            if aw:
                count['same_edge_AW_W']+=1
        if len(before)==2 and commit and e['dv'] and e['dr'] and e['dw']:
            witness.append(dict(kind='full_pop_push',edge=c,line=e['line']))
        if commit and e['dv'] and not e['dw']:
            same=before[0]['addr']//32==e['da']//32
            count['same_line_W_load_blocked' if same and not e['dr'] else 'other_W_load']+=1
            if len(before)==2 and before[0]['addr']//32!=e['da']//32 and before[1]['addr']//32==e['da']//32:
                count['head_other_tail_same_W']+=1
        if e['dv'] and e['dr']:
            count['D_accept']+=1
            accepts.append([c,e['dw'],e['da'],e['wd'],e['ws'],e['ds']])
            if e['dw']:
                count['store_accept']+=1
                check(len(q)<cfg['Depth'],e,'store accepted beyond capacity')
                q.append(dict(addr=e['da'],data=e['wd'],strb=e['ws'],aw=False))
                for b in range(4):
                    if (e['ws']>>b)&1:
                        architectural[e['da']//4*4+b]=(e['wd']>>(8*b))&255
                if cache_tags[0].get(e['da']//32%64)==e['da']//32:
                    del cache_tags[0][e['da']//32%64]
                ent=dict(edge=c,addr=e['da'],kind='store',expected=None)
            else:
                count['load_accept']+=1
                ent=dict(edge=c,addr=e['da'],kind='load',expected=word(architectural,e['da']))
            dfront.append(ent)
        if e['iv'] and e['ir']:
            count['I_accept']+=1
            hit=cfg['Icache'] and cache_tags[0].get(e['ia']//32%64)==e['ia']//32
            count['I_hit' if hit else 'I_miss']+=1
            ifront.append(dict(edge=c,addr=e['ia'],kind='inst',expected=word(architectural,e['ia'])))
        if e['arv'] and e['ardy2']:
            count['AR']+=1
            check(read is None,e,'second physical DDR read')
            read=e['ara']//8*32
        if e['rv']:
            count['R']+=1
            check(read is not None,e,'R without owned AR')
            if read is not None:
                want=sum(physical[read+b]<<(8*b) for b in range(32))
                check(e['rdata']==want,e,'DDR R differs from initial bytes plus committed writes')
                owner=e['rid']
                check(owner in [0,1] and e['rlast'],e,'invalid R owner/last')
                if owner in [0,1] and cfg['Icache' if owner==0 else 'Dcache']:
                    cache_tags[owner][read//32%64]=read//32
            read=None
        count['max_occupancy']=max(count['max_occupancy'],len(q))
        prev=e
    final_want={line:sum(physical[line*32+b]<<(8*b) for b in range(32)) for line in range(256)}
    assert final==final_want,tag
    assert count['store_accept']==count['W']+count['store_cancel']+len(q)
    assert count['AW']==count['W']+count['AW_cancel']
    assert count['D_accept']==count['D_response']+count['D_cancel']+len(dfront)
    assert count['I_accept']==count['I_response']+count['I_cancel']+len(ifront)
    assert count['AR']==count['R'] and read is None
    assert not q and not dfront and not ifront
    evidence={p.relative_to(ROOT).as_posix():sha(p) for p in run.iterdir() if p.is_file() and p.suffix in ['.json','.sha256','.txt','.log'] and p.name not in ['webtalk.log']}
    return dict(status='OBSERVED_TRACE_BYTE_AND_IDENTITY_REVIEW_PASS' if not issues else 'NOT_ACCEPTED',
                meta=meta,manifest=manifest,evidence_sha256=evidence,counts=dict(count),issues=issues,
                witness=witness,read_checks=reads,all_8192_final_bytes_match=True,marks=marks,
                accepts=accepts,AW=awbeats,W=wbeats,final_memory=final,summary=summary,
                raw_rows=rows,vendor_diagnostics=diagnostic)

def main():
    assert not (HERE/'review.json').exists(),'Preserve existing review'
    runs={tag:audit(tag) for tag in TAGS}
    d1,old,d2=[runs[n] for n in ['xs_short_new_d1_20261018_c','xs_short_old_20261018_c','xs_short_new_d2_20261018_c']]
    norm=lambda rows:[{k:r[k] for k in COLS} for r in rows]
    comparison=dict(legacy_all_external_edges_identical=norm(d1['raw_rows'])==norm(old['raw_rows']),
        legacy_marks_identical=d1['marks']==old['marks'],
        depth_logical_accepts_identical=[r[1:] for r in d1['accepts']]==[r[1:] for r in d2['accepts']],
        depth_AW_identical=d1['AW']==d2['AW'],depth_W_identical=d1['W']==d2['W'],
        depth_final_memory_identical=d1['final_memory']==d2['final_memory'],
        done_edges=[d1['marks']['S_done'],d2['marks']['S_done']],
        second_store_accept=[d1['accepts'][1][0],d2['accepts'][1][0]])
    e=BASE/'key_20261018_e'
    e_tb=sha(e/'src/tb/tb_wb2_bridge.sv')
    key=runs[TAGS[0]]
    e_rows=read_trace(e/'wb2.edges.log')[0]
    cross=dict(modelsim_TB_sha256=e_tb,xsim_TB_sha256=key['manifest']['tb\\tb_wb2_bridge.sv'],
               same_TB=e_tb==key['manifest']['tb\\tb_wb2_bridge.sv'],
               same_external_rows=norm(e_rows)==norm(key['raw_rows']))
    for result in runs.values():
        del result['raw_rows']; del result['final_memory']
    result=dict(status='TASK043_PARTIAL_BRIDGE_EVIDENCE_REVIEWED_FULL_ACCEPTANCE_PENDING',
        runs=runs,comparison=comparison,cross_backend=cross,
        limits=['SoC RAM/MMIO/FENCE/IRQ/Camera/PP integration absent.',
                'x16 and read-under-write disabled not executed; nonposted fails in posted-only TB model.',
                'Key has two I misses, no warm I-hit poison; no AR/R same-edge stimulus.',
                'Head-other/tail-same held-load promotion not triggered; current tail scenario has both in same line.',
                'Submitted checker only counts I responses and fills D cache on I R; short nonposted PASS has an operator-precedence escape.',
                'No standalone store/load blocking attribution or application CoreMark/board result.',
                'Vendor IPSpecCheck 04030130 display retained in old/new runs; not a clean vendor diagnostic result.',
                'No new RTL, HDL, PDS, board operation or environment change by this audit.'])
    (HERE/'review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],runs={tag:dict(status=r['status'],counts=r['counts'],issues=r['issues'][:3]) for tag,r in runs.items()},comparison=comparison,cross_backend=cross),ensure_ascii=False))

if __name__=='__main__':
    main()
