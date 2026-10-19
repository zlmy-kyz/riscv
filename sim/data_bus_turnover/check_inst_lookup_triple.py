"""Independent reference for the single missing old-hit/dual-request boundary."""
import json
from pathlib import Path
from check_inst_lookup_protocol_completion import parse_edges, read_plan_log

PLAN = [dict(id=t,scen=1,target=int(t==3),addr=0x40 if t==0 else 0x44,
             write=int(t==3),size=2,wdata=0x01020304 if t==3 else 0,
             wstrb=10 if t==3 else 0,cancel=0) for t in range(4)]


def review(edge_path, plan_path):
    assert read_plan_log(plan_path)==PLAN, 'Full stimulus identity mismatch'
    edges, scen, toks, sums, bus = parse_edges(edge_path)
    assert not scen and not toks and not bus
    assert [e['edge'] for e in edges]==list(range(1,len(edges)+1))
    memory=[(i*43+90)&255 for i in range(4096)]
    cache=None
    pending=None
    physical_write=False
    order=iter([0,1,3,2])
    accepted,responded={},{}
    read=None
    ar_at={}
    r_at={}
    expected={}
    counts=dict(accepts=0,responses=0,ar=0,r=0,aw=0,w=0)
    triple=[]
    previous=None
    for e in edges:
        assert e['scen']==1
        if not e['resetn']:
            assert pending is None and not e['i_v'] and not e['d_v']
            cache=None
            continue
        assert e['init']==1
        ai=e['i_v'] and e['i_r']; ad=e['d_v'] and e['d_r']
        assert not (ai and ad)
        if previous and previous['i_v'] and not previous['i_r']:
            assert e['i_v'] and e['i_addr']==previous['i_addr'], 'Younger I was not held'
        if e['i_rsp'] or e['d_rsp']:
            assert pending is not None and not (e['i_rsp'] and e['d_rsp'])
            p=PLAN[pending]
            assert int(bool(e['d_rsp']))==p['target']
            if pending==3:
                assert e['edge']==accepted[3]+1
            else:
                assert e['i_rdata']==expected[pending], ('CPU data',pending,e['edge'])
                assert e['edge']==(accepted[pending]+1 if pending==1 else r_at[pending]+1)
            if pending==1:
                assert e['i_v'] and e['d_v'] and e['d_r'] and not e['i_r'], 'Missing required triple boundary'
                assert e['i_addr']==e['d_addr']==0x44 and ad and not ai
                triple.append(e['edge'])
            responded[pending]=e['edge']; pending=None; counts['responses']+=1
        if e['ar_v'] and e['ar_r']:
            assert read in (0,2) and read not in ar_at and not e['busy']
            assert e['ar_addr']==16 and e['ar_id']==0
            ar_at[read]=e['edge']; counts['ar']+=1
        if e['r_v']:
            assert read in ar_at and read not in r_at and e['r_id']==0 and e['r_last']==1
            bs=memory[0x40:0x60]
            assert e['r_data']==sum(b<<(j*8) for j,b in enumerate(bs)), 'DDR byte data'
            lane=0 if read==0 else 1
            expected[read]=sum(bs[lane*4+j]<<(8*j) for j in range(4))
            r_at[read]=e['edge']; cache=list(bs); read=None; counts['r']+=1
        if e['aw_v'] and e['aw_r']:
            assert physical_write and e['w_r'] and e['aw_addr']==16
            assert e['w_strb']==0xa0 and e['w_data']==0x01020304<<32
            # Expected write comes from the fixed CPU stimulus, never from DUT output.
            memory[0x45]=3; memory[0x47]=1
            physical_write=False; counts['aw']+=1; counts['w']+=1
        if ai or ad:
            assert pending is None
            tid=next(order)
            p=PLAN[tid]
            assert p['target']==int(bool(ad))
            assert (e['d_addr'] if ad else e['i_addr'])==p['addr']
            accepted[tid]=e['edge']; pending=tid; counts['accepts']+=1
            if ad:
                assert e['d_wr']==1 and e['d_size']==2 and e['d_wdata']==p['wdata'] and e['d_wstrb']==p['wstrb']
                assert not physical_write
                cache=None; physical_write=True
            elif tid==1:
                assert cache is not None
                expected[tid]=sum(cache[4+j]<<(8*j) for j in range(4))
            else:
                assert cache is None and read is None
                read=tid
        previous=e
    assert next(order,None) is None and pending is None and read is None and not physical_write
    assert set(accepted)==set(responded)==set(range(4)) and len(triple)==1
    assert counts==dict(accepts=4,responses=4,ar=2,r=2,aw=1,w=1)
    assert expected[1]!=expected[2] and responded[1]==accepted[3] and accepted[2]>accepted[3]
    assert sums=={k:str(v) for k,v in dict(accepts=4,responses=4,aw=1,w=1,edges=len(edges)).items()}
    return dict(status='INST_LOOKUP_TRIPLE_REFERENCE_PASS',counts=counts,triple_edges=triple,
                accepted=accepted,responded=responded,old_word=expected[1],new_word=expected[2],edges=len(edges))


if __name__=='__main__':
    import sys
    print(json.dumps(review(Path(sys.argv[1]),Path(sys.argv[2])),indent=2))
