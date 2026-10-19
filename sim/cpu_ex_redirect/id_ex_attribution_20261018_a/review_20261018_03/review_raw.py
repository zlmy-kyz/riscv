"""Offline task040 fix02d evidence review; never runs HDL or changes inputs."""
from pathlib import Path
from collections import Counter, deque
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
TASK = HERE.parent
ROOT = TASK.parents[2]
SEALED, RUN = TASK/'sealed_fix02d', TASK/'build/fix02d'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'review.json').exists(), 'Preserve review'
manifest = json.loads((SEALED/'manifest.json').read_text())['files_sha256']
assert len(manifest)==17 and all(sha(SEALED/k)==v for k,v in manifest.items())
result = json.loads((RUN/'result.json').read_text())
assert result['manifest']==manifest
assert manifest['myriscv/mycpu_sync.v']=='5c26df0229ab00365b2eca1412499f988981fdfe1d1b7292e43a8317f0d47745'
includes=[]
for rel in manifest:
    if Path(rel).suffix in ('.v','.vh','.sv','.svh'):
        for inc in re.findall(r'`include\s+"([^"]+)"',(SEALED/rel).read_text(encoding='utf-8')):
            candidates=[p for p in ((SEALED/rel).parent/inc,SEALED/'myriscv'/inc) if p.is_file()]
            assert candidates and all(p.relative_to(SEALED).as_posix() in manifest for p in candidates)
            includes.append(dict(source=rel,include=inc))
commands=json.loads((RUN/'commands.json').read_text())
assert len(commands)==25 and all(c['exit']==0 for c in commands)
assert str(SEALED) in ' '.join(commands[0]['argv'])

def events(raw):
    rows=[]
    for line in raw.splitlines():
        if not line.startswith('EV,'):
            continue
        d={};key=None
        for part in line.split(',')[1:]:
            if '=' in part:
                key,value=part.split('=',1);d[key]=[value]
            elif key is not None:
                d[key].append(part)
        if d.get('ph')==['0']:
            d['time']=int(d['t'][0]);rows.append(d)
    return rows

observations={}
for name,summary in result['runs'].items():
    sub=RUN/name;raw=(sub/'run.log').read_text()
    assert 'RESULT: FAIL' not in raw and 'RESULT: INCOMPLETE' not in raw
    assert all(line in raw for line in summary['lines'])
    rows=events(raw);table={r['time']:r for r in rows}
    assert len(table)==len(rows)
    assert all(b['time']-a['time']==10 for a,b in zip(rows,rows[1:]))
    code=[int(w,16) for w in (sub/'imem.hex').read_text().split()]
    pending=deque();ledger=[];drop_count=0;deliver_count=0
    for r in rows:
        t=r['time']
        if r['irsp'][0]=='1':
            assert len(pending)==1 and r['pend'][0]=='1',(name,t,'orphan response')
            old=pending.popleft()
            assert int(r['pend'][1],16)==old['address']
            assert int(r['irsp'][1],16)==old['data']
            dropped=r['pend'][2]=='1' or r['rdir']==['1']
            old.update(consume_ns=t,latency_edges=(t-old['accept_ns'])//10,
                       disposition='drop' if dropped else 'response_good')
            assert old['latency_edges']==(8 if name=='slowwrong' and old['address']==8 else 1)
            drop_count+=int(dropped);deliver_count+=int(not dropped)
        if r['ireq'][0]=='11':
            assert not pending,(name,t,'two outstanding')
            addr=int(r['ireq'][1],16)
            item=dict(request_id=len(ledger)+1,address=addr,data=code[addr//4],accept_ns=t)
            ledger.append(item);pending.append(item)
    assert not pending
    ia=list(map(int,re.search(r'IAUDIT acc=(\d+) rspgen=(\d+) consume=(\d+) deliver=(\d+) drop=(\d+) inflight=(\d+)',raw).groups()))
    assert ia==[len(ledger),len(ledger),len(ledger),deliver_count,drop_count,0]
    da=list(map(int,re.search(r'DAUDIT acc=(\d+) rspgen=(\d+) consume=(\d+) stores=(\d+)',raw).groups()))
    assert da[0]==da[1]==da[2] and da[3]==1
    assert 'X31CHECK x31=00000000 mscratch=00000000' in raw
    ref=json.loads((sub/'ref_ret.json').read_text())
    got=[]
    for m in re.finditer(r'^RET,\d+,([0-9a-f]+),([0-9a-f]+),(\d+),(\d+),([0-9a-f]+),([0-9a-f]+)$',raw,re.M):
        got.append(dict(pc=int(m[1],16),inst=int(m[2],16),rd=int(m[3]),we=int(m[4]),value=int(m[5],16),next_pc=int(m[6],16)))
    assert len(got)>=len(ref)
    for g,e in zip(got,ref):
        assert all(g[k]==e[k] for k in ('pc','inst','we','next_pc')),(name,g,e)
        if e['we']:
            assert g['rd']==e['rd'] and g['value']==e['value'],(name,g,e)
    evt=list(map(int,re.search(r'EVENT t0=(\d+) t1=(\d+) t2=(\d+) t3=(\d+) t4=(\d+)',raw).groups()))
    t0,t1,t2,t3,t4=evt
    obs=dict(events_ns=evt,retired_prefix_rows_checked=len(ref),
             checked_architectural_fields='pc/inst/we/next_pc and rd/value when architectural we=1',
             independent_I_ledger_entries=len(ledger),I_drop_count=drop_count,D_aggregate_audit=da,
             x31=0,mscratch=0)
    if name!='nottaken':
        target=int(table[t0]['bj'][0],16)
        assert table[t1]['rdir']==['1'] and int(table[t1]['idex'][1],16)==int(table[t0]['ifid'][1],16)
        assert table[t2]['ireq'][0]=='11' and int(table[t2]['ireq'][1],16)==target
        load=table[t3]
        assert load['front']==['0'] and load['rdir']==['0']
        from_buffer=load['buf'][0]=='1' and int(load['buf'][1],16)==target
        from_response=load['buf'][0]=='0' and load['pend'][0]=='1' and load['pend'][2]=='0' and load['irsp'][0]=='1' and int(load['pend'][1],16)==target
        assert from_buffer or from_response
        assert table[t4]['idfire']==['1'] and int(table[t4]['ifid'][1],16)==target and t3<t4
        obs.update(intervals_edges=[(t1-t0)//10,(t2-t1)//10,(t3-t2)//10,(t4-t3)//10],
                   target_loaded_from='buffer' if from_buffer else 'response',
                   actual_old_pending_pc_at_load=int(load['pend'][1],16),
                   actual_old_buffer_pc_at_load=int(load['buf'][1],16))
    roi_end=next(r['time'] for r in rows if r['time']>=t0 and r['ret'][0]=='1' and int(r['ret'][1],16)==ref[-1]['pc'])
    roi=[r for r in rows if t0<=r['time']<=roi_end]
    counts=Counter(int(r['cls'][0]) for r in roi)
    obs['ROI']=dict(start_ns=t0,end_ns_inclusive=roi_end,edges=len(roi),classifications=dict(counts),
        OTHER_retire=sum(r['cls']==['8'] and r['ret'][0]=='1' for r in roi),
        OTHER_idfire=sum(r['cls']==['8'] and r['idfire']==['1'] for r in roi))
    roi_report=list(map(int,re.search(r'ROI edges=(\d+) other=(\d+) mem=(\d+) if=(\d+) branch=(\d+) load_use=(\d+) ctrl=(\d+) hold=(\d+)',raw).groups()))
    assert roi_report==[len(roi),*[counts[k] for k in (8,3,2,4,7,5,6)]]
    (HERE/(name+'_I_ledger.json')).write_text(json.dumps(ledger,indent=2)+'\n',encoding='utf-8')
    observations[name]=obs

review=dict(status='TASK040_FIX02D_CORE_ATTRIBUTION_RAW_EVIDENCE_ACCEPTED_WITH_DOCUMENTED_REMAINING_GAPS',
    sealed_input_files_verified=17,include_closure=includes,recorded_commands_checked=25,
    observations=observations,
    accepted_scope='Six microprograms: physical five-edge timing, eight-edge wrong-address I response, per-I identity/conservation reconstructed from full phase0 trace, architectural retire prefix and x31/mscratch checks, short ROI classification.',
    remaining_gaps=['phase1 old pending/buffer/response-id fields STILL read post-NBA; report claim of frozen OLD snapshots is false. Review uses phase0 ledger instead, does not accept those fields.',
        'No per-D request/address/data/strobe trace or actual per-D latency witness. D aggregate counts/final memory and load writeback verified, not full D byte/request ownership acceptance.',
        'commands.json truncates stdout/stderr to last4000 chars, despite report saying full. Full VVP log is separate and reviewed; no tool-version transcript delivered.',
        'Runner itself omits checking g.we equality and unexpected writes when reference we=0. This offline review DOES compare actual we equality for the recorded prefix.',
        'Behavioral-model i_busy/response-id use blocking posedge writes. Recorded traces/ledger consistent, but this review does not establish scheduler-independent behavior of the TB.',
        'This is limited attribution acceptance, not all original task040 evidence requirements closed or complete CPU/SoC/IRQ/reset acceptance.'],
    next_action='Core attribution is now usable; no broad rerun justified solely for already independently reconstructed five-edge/I-identity data. Preserve listed missing D/metadata evidence for any test reuse requiring it. No new board/RTL operation authorized by this review.',
    evidence_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in [TASK/'report_fix02.md', SEALED/'manifest.json',RUN/'commands.json',RUN/'result.json',RUN/'compile.log',RUN/'tb.vvp',Path(__file__),*RUN.glob('*/run.log'),*RUN.glob('*/ref_ret.json')]},
    RTL_modified=False,HDL_started=False,PDS_started=False,serial_opened=False)
(HERE/'review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=review['status'],modes={k:dict(events=v['events_ns'],intervals=v.get('intervals_edges'),I_requests=v['independent_I_ledger_entries'],ROI=v['ROI']['edges']) for k,v in observations.items()}),ensure_ascii=False,indent=2))
