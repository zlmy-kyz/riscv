"""Offline Sol evidence review for Task043 supplement02. No HDL/tool execution."""
from collections import Counter, deque
from pathlib import Path
import hashlib
import importlib.util
import json
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=ROOT/'sim/write_buffer_two_entry'
spec=importlib.util.spec_from_file_location('prior_sol_audit',BASE/'review_20261018_02/review_results.py')
prior=importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
TAGS=['xs_fair_d1_20261018_d','xs_fair_d2_20261018_d','xs_edge_20261018_d',
      'xs_x16_20261018_d','xs_noposted_20261018_d','xs_ruw0_20261018_d','xs_soc_20261018_d']

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def identity(tag):
    run=BASE/tag
    meta=json.loads((run/'run_meta.json').read_text(encoding='utf-8-sig'))
    assert meta['status']=='PASS' and meta['identity_drift']==0
    assert meta['exits']==dict(xvlog=0,xelab=0,xsim=0,check=0)
    assert (run/'inputs_before.sha256').read_bytes()==(run/'inputs_after.sha256').read_bytes()
    entries={}
    for line in (run/'inputs_before.sha256').read_text().splitlines():
        digest,size,name=line.split(None,2)
        p=run/'src'/name
        assert p.stat().st_size==int(size) and sha(p)==digest,p
        entries[name]=digest
        if p.suffix in ['.v','.sv','.vh','.svh']:
            for include in re.findall(r'`include\s+"([^"]+)"',p.read_text(errors='replace')):
                candidates=[p.parent/include,run/'src/myriscv'/include]
                assert any(q.exists() for q in candidates),(p,include)
        if name.startswith('myriscv\\'):
            assert sha(ROOT/name)==digest, 'Current RTL differs from sealed '+name
    assert entries['myriscv\\dual_sram_to_pango_ddr_bridge.v']=='855318eebf7fc75a0b17d15a620b6d8d08bb54ff9348d663cbcd6aca0883262f'
    raw=(run/'log_xsim.txt').read_text(errors='replace')
    assert 'RESULT: PASS' in raw and not any(x in raw for x in ['RESULT: FAIL','Fatal:','FATAL_ERROR'])
    assert any('src\\myriscv\\dual_sram_to_pango_ddr_bridge.v' in cmd for cmd in meta['commands'])
    evidence={p.relative_to(ROOT).as_posix():sha(p) for p in run.iterdir() if p.is_file() and p.suffix in ['.json','.sha256','.txt','.log'] and not p.name.startswith('webtalk')}
    return dict(meta=meta,manifest=entries,evidence_sha256=evidence,
                vendor_diagnostics=[s for s in raw.splitlines() if 'IPSpecCheck:' in s])

def bridge(tag):
    run=BASE/tag
    out=identity(tag)
    cfg=out['meta']['params'];bs=cfg['Dq'];posted=bool(bs==32 and cfg['Posted'])
    rows,marks,initial,final,summary=prior.read_trace(run/'wb2.edges.log')
    assert set(initial)==set(final)==set(range(1024))
    physical={line*bs+b:(value>>(8*b))&255 for line,value in initial.items() for b in range(bs)}
    architectural=dict(physical)
    q,dfront,ifront=deque(),deque(),deque()
    cache={0:{},1:{}}
    read=None
    counts=Counter();issues=[];responses=[];witness=[];accepted=[];aws=[];ws=[];prev=None
    def check(ok,e,msg):
        if not ok:issues.append(dict(edge=e['cyc'],line=e['line'],message=msg))
    def word(mem,addr):
        return sum(mem[(addr//4)*4+b]<<(8*b) for b in range(4))
    def hit(owner,addr):
        return cfg['Icache' if owner==0 else 'Dcache'] and cache[owner].get(addr//bs%64)==addr//bs
    for e in rows:
        c=e['cyc']
        if not e['rstn']:
            counts['store_cancel']+=len(q)
            counts['AW_cancel']+=sum(s['aw'] for s in q)
            counts['D_cancel']+=len(dfront);counts['I_cancel']+=len(ifront)
            q.clear();dfront.clear();ifront.clear();cache={0:{},1:{}}
            architectural=dict(physical);read=None;prev=e
            continue
        check(all(e[k] is not None for k in prior.COLS),e,'undefined live pin')
        if prev and prev['rstn'] and prev['dv'] and not prev['dr']:
            check(e['dv'] and all(e[k]==prev[k] for k in ['dw','ds','da','wd','ws']),e,'D request changed before acceptance')
        before=list(q)
        check(bool(e['busy'])==bool(q and posted),e,'whole-queue busy mismatch')
        check(not e['arv'] or not q,e,'AR before all writes completed')
        for flag,data,front,owner in [('dsv','ddata',dfront,'D'),('isv','idata',ifront,'I')]:
            if e[flag]:
                counts[owner+'_response']+=1;check(bool(front),e,'unowned '+owner+' response')
                if front:
                    req=front.popleft()
                    if req['kind']=='store':
                        check(posted or req['written'],e,'nonposted ACK before W')
                    else:
                        check(e[data]==req['expected'],e,owner+' response differs from accepted architectural bytes')
                        responses.append(dict(port=owner,accepted=req['edge'],response=c,addr=req['addr'],actual=e[data],expected=req['expected']))
        aw=e['init'] and e['av'] and e['ardy']
        if aw:
            check(bool(q),e,'AW with no accepted store')
            if q:
                check(not q[0]['aw'],e,'duplicate AW')
                check(e['aa']==q[0]['addr']//bs*8,e,'AW address/order/unit mismatch')
                q[0]['aw']=True;counts['AW']+=1;aws.append([c,e['aa']])
        commit=bool(e['init'] and e['wrdy'] and q and q[0]['aw'])
        if commit:
            s=q.popleft();counts['W']+=1;s['written']=True
            lane=s['addr']//4%(bs//4)
            check(e['aa']==s['addr']//bs*8,e,'W address mismatch')
            check(e['wdata']==s['data']<<(lane*32),e,'W data/lane mismatch')
            check(e['wstrb']==s['strb']<<(lane*4),e,'W byte mask mismatch')
            for b in range(4):
                if (s['strb']>>b)&1:physical[s['addr']//4*4+b]=(s['data']>>(8*b))&255
            ws.append([c,e['aa'],e['wdata'],e['wstrb']])
        if commit and e['dv'] and not e['dw'] and before:
            if len(before)==2 and before[0]['addr']//bs!=e['da']//bs and before[1]['addr']//bs==e['da']//bs:
                counts['tail_only_W_load_blocked']+=int(not e['dr'])
        if e['dv'] and e['dr']:
            counts['D_accept']+=1;accepted.append([c,e['dw'],e['da'],e['wd'],e['ws'],e['ds']])
            if e['dw']:
                counts['store_accept']+=1
                check(len(q)<(cfg['Depth'] if posted else 1),e,'write capacity exceeded')
                req=dict(edge=c,addr=e['da'],kind='store',expected=None,data=e['wd'],strb=e['ws'],aw=False,written=False)
                q.append(req)
                for b in range(4):
                    if (e['ws']>>b)&1:architectural[e['da']//4*4+b]=(e['wd']>>(8*b))&255
                if hit(0,e['da']):del cache[0][e['da']//bs%64]
            else:
                counts['load_accept']+=1
                req=dict(edge=c,addr=e['da'],kind='load',expected=word(architectural,e['da']),needs_R=not hit(1,e['da']))
            dfront.append(req)
        if e['iv'] and e['ir']:
            counts['I_accept']+=1
            ih=bool(hit(0,e['ia']))
            counts['I_hit' if ih else 'I_miss']+=1
            ifront.append(dict(edge=c,addr=e['ia'],kind='inst',expected=word(architectural,e['ia']),needs_R=not ih))
        if e['arv'] and e['ardy2']:
            counts['AR']+=1;check(read is None,e,'second outstanding read')
            base=e['ara']//8*bs
            candidates=[(owner,req) for owner,front in [(1,dfront),(0,ifront)] for req in front if req.get('needs_R') and req['addr']//bs*bs==base]
            check(len(candidates)==1,e,'AR has no unique independently predicted miss')
            read=dict(base=base,owner=candidates[0][0] if len(candidates)==1 else None,req=candidates[0][1] if len(candidates)==1 else None)
        if e['rv']:
            counts['R']+=1;check(read is not None,e,'unowned R')
            if read:
                check(e['rid']==read['owner'] and e['rlast']==1,e,'R ID/last mismatch')
                want=sum(physical[read['base']+b]<<(8*b) for b in range(bs))
                check(e['rdata']==want,e,'R differs from independent committed memory')
                if read['req']:read['req']['needs_R']=False
                if read['owner'] in [0,1] and cfg['Icache' if read['owner']==0 else 'Dcache']:
                    cache[read['owner']][read['base']//bs%64]=read['base']//bs
            read=None
        if e['dsv'] and e['dv'] and e['dr']:counts['response_turnover']+=1
        if aw and commit:counts['AW_W_same_edge']+=1
        if e['arv'] and e['ardy2'] and e['rv']:counts['AR_R_same_edge']+=1
        counts['max_occupancy']=max(counts['max_occupancy'],len(q));prev=e
    check(not q and not dfront and not ifront and read is None,rows[-1],'unfinished request')
    assert final=={line:sum(physical[line*bs+b]<<(8*b) for b in range(bs)) for line in initial}
    assert counts['store_accept']==counts['W']+counts['store_cancel']+len(q)
    assert counts['D_accept']==counts['D_response']+counts['D_cancel']+len(dfront)
    assert counts['I_accept']==counts['I_response']+counts['I_cancel']+len(ifront)
    assert counts['AW']==counts['W']+counts['AW_cancel']
    assert counts['AR']==counts['R']
    out.update(counts=dict(counts),issues=issues,responses=responses,marks=marks,
               accepted=accepted,AW=aws,W=ws,final_memory_sha256=hashlib.sha256(b''.join(final[n].to_bytes(bs,'little') for n in sorted(final))).hexdigest(),
               initial_memory_sha256=hashlib.sha256(b''.join(initial[n].to_bytes(bs,'little') for n in sorted(initial))).hexdigest(),
               final_bytes_checked=bs*len(initial),summary=summary)
    return out

def soc():
    tag=TAGS[-1];run=BASE/tag;out=identity(tag)
    records=[]
    decimal={'n','ep','fst'}
    for line_no,line in enumerate((run/'soc.edges.log').read_text().splitlines(),1):
        fields=line.split();r=dict(kind=fields[0],line=line_no)
        for token in fields[1:]:
            k,v=token.split('=')
            r[k]=None if any(c in v.lower() for c in 'xz') else int(v,10 if k in decimal else 16)
        records.append(r)
    images={ep:[int(v,16) for v in (run/f'src/tb/soc_wb2_{name}.hex').read_text().splitlines()] for ep,name in [(1,'a'),(2,'b')]}
    mem={line*32+b:(line*29+b*7+3)&255 for line in range(4096) for b in range(32)}
    for base,value in [(0x800*32,0xc0de0001),(0x840*32,0xb0b00001)]:
        for b in range(4):mem[base+b]=(value>>(8*b))&255
    q=deque();aw_pending=None;rd=None;epoch=0;counts=Counter();issues=[]
    actual_access={1:[],2:[]};w_events={1:[],2:[]};nonddr=[];blocked=[];irqs=[];fences=[];ar_aperture=[]
    def check(ok,r,msg):
        if not ok:issues.append(dict(edge=r['n'],line=r['line'],message=msg))
    def alias(ctrl):
        byte=ctrl*4
        if byte>>22==4:return 0x800*32+(byte&0x3ff)//32*32
        if byte>>22==8:return 0x840*32+(byte&0x3ff)//32*32
        return byte//32*32
    for r in records:
        if r['kind']=='I':
            irqs.append(r);continue
        if r['kind']!='E':continue
        ep=r['ep'];n=r['n']
        if not r['rst']:
            check(not q and aw_pending is None and rd is None,r,'reset cancels unexpected SoC transaction')
            continue
        if ep!=epoch:
            epoch=ep
            for w in range(512):
                value=images[ep][w] if w<len(images[ep]) else 0
                for b in range(4):mem[w*4+b]=(value>>(8*b))&255
        check(all(v is not None for k,v in r.items() if k not in ['kind']),r,'undefined live SoC observation')
        check(bool(r['busy'])==bool(q),r,'SoC busy differs from independently accepted DDR stores')
        if r['fret']:fences.append(r)
        if r['dv'] and r['dr']:
            actual_access[ep].append([bool(r['dw']),r['da'],r['dwd'] if r['dw'] else None,n])
            if r['dw'] and r['ds']==8:q.append(dict(addr=r['da']-0x40000000,data=r['dwd'],strb=15))
            if r['ds']&7:
                nonddr.append(r);check(not q,r,'nonDDR side effect before whole queue empty')
        elif r['dv'] and r['ds']&7 and q:blocked.append(r)
        if r['awv'] and r['awr']:
            counts['AW']+=1
            check(aw_pending is None and bool(q),r,'unowned/duplicate SoC AW')
            if q:
                check(r['awa']==q[0]['addr']//32*8,r,'SoC AW not oldest store')
                aw_pending=[r['awa'],r['wdv'],r['wsv']]
        commit=bool(r['wr'] and aw_pending)
        check(bool(r['wf'])==commit,r,'model WF does not equal independently owned WREADY')
        if commit and q:
            counts['W']+=1;head=q.popleft();lane=head['addr']//4%8
            check([r['awa'],r['wdv'],r['wsv']]==aw_pending,r,'AW-captured W fields changed')
            check(r['wdv']==head['data']<<(lane*32) and r['wsv']==15<<(lane*4),r,'SoC W byte data differs from accepted store')
            base=alias(aw_pending[0])
            for b in range(32):
                if (r['wsv']>>b)&1:mem[base+b]=(r['wdv']>>(8*b))&255
            w_events[ep].append(n);aw_pending=None
        if r['arv'] and r['arr']:
            counts['AR']+=1;check(rd is None and not q,r,'SoC read before drain/second outstanding read')
            rd=[r['ara'],r['ari']]
            if r['ara'] in [0x400000,0x800000]:ar_aperture.append([ep,n,r['ara']])
        if r['rv']:
            counts['R']+=1;check(rd is not None,r,'SoC R without AR')
            if rd:
                base=alias(rd[0]);want=sum(mem[base+b]<<(8*b) for b in range(32))
                check(r['rdv']==want and r['rid']==rd[1],r,'SoC R data/ID mismatch against independent model')
                if base in [0x800*32,0x840*32]:
                    value=0xc0de0002 if base==0x800*32 else 0xb0b00002
                    for b in range(4):mem[base+b]=(value>>(8*b))&255
            rd=None
    # Independent decoding of all observed retired instructions and GPR writes.
    regs={1:[0]*32,2:[0]*32};expected_access={1:[],2:[]};camera_reads={0x41000000:0,0x42000000:0}
    retires=[r for r in records if r['kind']=='T']
    for r in retires:
        ep=r['ep'];pc=r['pc'];ins=r['inst'];reg=regs[ep]
        idx=(pc-0x40000000)//4
        check(0<=idx<len(images[ep]) and images[ep][idx]==ins,r,'retired PC/instruction differs from frozen program')
        op=ins&127;rdn=ins>>7&31;rs1=ins>>15&31;rs2=ins>>20&31;value=None
        imm=ins>>20;imm=imm-4096 if imm&2048 else imm
        if op==0x37:value=ins&0xfffff000
        elif op==0x13:value=(reg[rs1]+imm)&0xffffffff
        elif op==0x03:
            addr=(reg[rs1]+imm)&0xffffffff
            check(addr in camera_reads,r,'unexpected CPU load address')
            if addr in camera_reads:
                camera_reads[addr]+=1;value=(0xc0de0000 if addr==0x41000000 else 0xb0b00000)+camera_reads[addr]
            expected_access[ep].append([False,addr,None])
        elif op==0x23:
            off=(ins>>25<<5)|(ins>>7&31);off=off-4096 if off&2048 else off
            expected_access[ep].append([True,(reg[rs1]+off)&0xffffffff,reg[rs2]])
        else:check(op in [0x0f,0x6f,0x73],r,'unexpected program opcode')
        if r['we'] and r['rd']:
            check(value is not None and r['rd']==rdn and r['wd']==value,r,'GPR write differs from independent instruction calculation')
            reg[r['rd']]=value
        elif value is not None and rdn:check(False,r,'missing GPR write')
    for ep in [1,2]:check([v[:3] for v in actual_access[ep]]==expected_access[ep],dict(n=0,line=0),'CPU accepted accesses differ from independently decoded program')
    dump={}
    for line in (run/'soc.mem.log').read_text().splitlines():
        _,addr,value=line.split();dump[int(addr)]=int(value,16)
    assert set(dump)==set(range(512))
    for line,value in dump.items():check(value==sum(mem[line*32+b]<<(8*b) for b in range(32)),dict(n=0,line=0),'SoC final byte image mismatch at beat '+str(line))
    check(not q and aw_pending is None and rd is None,dict(n=0,line=0),'SoC pending transaction at end')
    live=[r for r in records if r['kind']=='E' and r['rst']]
    for f in fences:check(not f['busy'] and f['n']>max(n for n in w_events[f['ep']] if n<f['n']),f,'FENCE retired before last W')
    for r in irqs:check(not r['busy'] and r['cause']==11 and r['epc']==0x40000100 and r['n']>max(n for n in w_events[r['ep']] if n<r['n']),r,'IRQ taken before drain/wrong cause/target')
    out.update(issues=issues,edges=len(live),retires=len(retires),counts=dict(counts),
               decoded_data_accesses=expected_access,W_edges=w_events,
               nonDDR_accepts=[dict(edge=r['n'],addr=hex(r['da']),data=r['dwd']) for r in nonddr],
               nonDDR_blocked=len(blocked),tail_only_nonDDR_blocked=sum(w_events[1][0]<r['n']<=w_events[1][1] for r in blocked),
               FENCE_retire=[r['n'] for r in fences],IRQs=irqs,aperture_ARs=ar_aperture,
               final_bytes_checked=512*32,
               FENCE_active_busy_wait='NOT_STIMULATED: UART and RAM before FENCE already drained the queue; only ordered retirement observed')
    return out

def main():
    assert not (HERE/'review.json').exists(),'Preserve original review'
    runs={tag:bridge(tag) for tag in TAGS[:-1]};runs[TAGS[-1]]=soc()
    d1,d2=runs[TAGS[0]],runs[TAGS[1]]
    assert d1['manifest']==d2['manifest']
    fair=dict(same_sealed_inputs=True,same_initial_bytes=d1['initial_memory_sha256']==d2['initial_memory_sha256'],
              logical_requests_equal=[r[1:] for r in d1['accepted']]==[r[1:] for r in d2['accepted']],
              AW_equal=d1['AW']==d2['AW'],W_equal=d1['W']==d2['W'],
              final_memory_equal=d1['final_memory_sha256']==d2['final_memory_sha256'],
              cycles=[r['marks']['S2_done']-r['marks']['S2'] for r in [d1,d2]],
              second_store_accept=[r['accepted'][1][0] for r in [d1,d2]],net_cycles=0)
    neg=json.loads((BASE/'negatives_summary.json').read_text())
    negatives=[]
    for tag,entry in neg['runs'].items():
        for row in entry['rows']:
            if not row['applied']:
                continue
            assert row['exit']!=0 and row['status']=='FAIL'
            folder=BASE/tag/'negatives'/row['name']
            checks=list(folder.glob('check_*.json'))
            assert len(checks)==1 and json.loads(checks[0].read_text())['status']=='FAIL'
            negatives.append(dict(tag=tag,name=row['name'],reported_exit=row['exit'],checker_json_sha256=sha(checks[0])))
    result=dict(status='TASK043_SUPPLEMENT02_PARTIAL_ACCEPTED_FENCE_BUSY_TRIGGER_PENDING',runs=runs,fair=fair,
                negatives=negatives,negative_limit='48 FAIL artefacts verified; per-mutation stdout and native invocation records not separately preserved.',
                limits=['FENCE after UART/RAM cannot test independent busy-queue wait; only positive ordered retirement observed.',
                        'No fixed-BIN hardware/application performance result; no net gain in this fair fragment.',
                        'No new HDL/PDS/board/environment action; no submitted checker or negative runner executed by Sol.'])
    (HERE/'review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],fair=fair,runs={tag:dict(issues=r['issues'][:4],counts=r['counts']) for tag,r in runs.items()},negatives=len(negatives)),ensure_ascii=False))

if __name__=='__main__':main()
