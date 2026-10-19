"""Task030 simulation-only programs and independent architectural event oracles."""
from pathlib import Path
import json,sys,re,random
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'sim/cpu_zmmul'))
from prepare_tests import Program,BASE,DATA,STATUS,HANDLER,MASK,enc_b,enc_j,enc_i,s32,imm_i,imm_s,imm_b,imm_j

def oracle(p):
    regs=[0]*32;mem={DATA:9,DATA+4:17,DATA+8:0};mem.update(p.meta.get('memory',{}))
    csr={0x300:0x1800,0x301:0x40000100,0x304:0,0x305:0,0x340:0,0x341:0,0x342:0,0x343:0}
    pc=BASE;events=[];faulted=False;interrupted=False
    def trap(at,ins,cause,tval,irq=False):
        events.append([2 if irq else 1,at,0 if irq else ins,0,0,0,cause,tval])
        csr[0x341]=at;csr[0x342]=cause;csr[0x343]=tval
        csr[0x300]=0x1800|(0x80 if csr[0x300]&8 else 0)
        return csr[0x305]
    for _ in range(10000):
        ins=p.words[pc];op=ins&127;rd=(ins>>7)&31;f3=(ins>>12)&7;r1=(ins>>15)&31;r2=(ins>>20)&31
        a,b=regs[r1],regs[r2];nxt=pc+4;wr=0;val=0;addr=0
        if pc==p.meta.get('if_fault'):
            pc=trap(pc,ins,1,pc);continue
        if op==0x37:wr,val=rd,ins&0xfffff000
        elif op==0x13 and f3==0:wr,val=rd,a+imm_i(ins)
        elif op==3:
            addr=(a+imm_i(ins))&MASK
            if addr==p.meta.get('data_fault') and not faulted:
                faulted=True;pc=trap(pc,ins,5,addr);continue
            assert f3==2;wr,val=rd,mem.get(addr,0)
        elif op==0x23:
            addr=(a+imm_s(ins))&MASK;assert f3==2;mem[addr]=b
        elif op==0x63:
            take={0:a==b,1:a!=b,4:s32(a)<s32(b),5:s32(a)>=s32(b),6:a<b,7:a>=b}[f3]
            if take:nxt=pc+imm_b(ins)
        elif op==0x6f:wr,val,nxt=rd,pc+4,pc+imm_j(ins)
        elif op==0x67:wr,val,nxt=rd,pc+4,(a+imm_i(ins))&~1
        elif ins==0x30200073:
            csr[0x300]=0x1880|(8 if csr[0x300]&0x80 else 0);nxt=csr[0x341]
        elif op==0x73 and f3 in (1,2):
            n=ins>>20;wr,val=rd,csr[n]
            if f3==1 or r1:
                v=a if f3==1 else val|a
                if n==0x300:v=0x1800|(v&0x88)
                elif n==0x304:v&=0x888
                elif n in (0x305,0x341):v&=~3
                csr[n]=v
        else:raise AssertionError(hex(ins))
        if nxt&3:
            pc=trap(pc,ins,0,nxt);continue
        events.append([3 if ins==0x30200073 else 0,pc,ins,int(wr!=0),wr,val&MASK,0,0])
        if wr:regs[wr]=val&MASK
        if op==0x23 and addr==STATUS:
            assert b==1;return events
        oldpc=pc;pc=nxt&MASK
        if oldpc==p.meta.get('irq_after') and not interrupted:
            interrupted=True;pc=trap(pc,0,0x8000000b,0,True)
    raise AssertionError('Program did not finish')

def flow():
    p=Program();p.li(10,DATA);p.li(1,1);p.li(2,1);p.li(3,0xffffffff)
    for f3,rs1,rs2 in [(0,1,2),(1,1,3),(4,3,1),(5,1,3),(6,1,3),(7,3,1)]:
        p.emit(enc_b(8,rs2,rs1,f3,0x63));p.sw(0,30) # wrong path store, never committed
        p.emit(enc_b(4,rs2,rs1,f3,0x63)) # taken target equals sequential, still redirect
    p.li(4,32);loop=p.pc;p.addi(4,4,-1);p.emit(enc_b(loop-p.pc,0,4,1,0x63))
    p.emit(enc_j(8,5,0x6f));p.sw(0,30)
    target=p.pc+16;p.li(6,target|1);p.emit(enc_i(0,6,0,6,0x67));p.sw(0,30)
    assert p.pc==target
    p.finish();return p

def programs():
    jobs=[]
    for name,profile in [('flow_fast',0),('flow_delayed',1),('flow_backpressure',2),('reset_pending',1)]:
        p=flow();jobs.append((name,profile,p,name=='reset_pending'))
    p=Program();p.li(10,DATA);p.lw(1);p.emit(enc_b(8,0,1,1,0x63));p.sw(0,30)
    target=p.pc+12;p.meta['memory']={DATA+8:target|1};p.lw(6,10,8);p.emit(enc_i(0,6,0,7,0x67));p.sw(0,30)
    assert p.pc==target;p.finish();jobs.append(('load_branch_jalr',1,p,False))
    p=Program();p.setup_trap();p.emit(enc_b(6,0,0,0,0x63));p.finish();p.handler();jobs.append(('misaligned_branch',0,p,False))
    p=Program();p.setup_trap();target=BASE+0xe00;p.emit(enc_j(target-p.pc,5,0x6f));p.sw(0,30)
    end=p.pc;p.finish();p.words[target]=0x13;p.words[target+4]=enc_j(end-(target+4),0,0x6f)
    p.meta['if_fault']=target;p.handler();jobs.append(('target_access_fault',1,p,False))
    p=Program();p.setup_trap();p.li(10,DATA);p.lw(1);p.emit(enc_b(8,0,0,0,0x63));p.sw(0,30);p.finish()
    p.meta['data_fault']=DATA;p.handler();jobs.append(('older_load_fault',1,p,False))
    p=Program();p.setup_trap();p.li(20,0x800);p.csr(0x304,rs=20,op=1);p.li(20,8);p.csr(0x300,rs=20,op=1)
    p.li(10,DATA);p.meta['irq_after']=p.lw(5,10,4);p.emit(enc_b(8,0,5,1,0x63));p.sw(0,30)
    p.finish();p.handler(skip=False);jobs.append(('irq_load_drain',1,p,False))
    return jobs

def main():
    out=HERE/'fixtures';assert not out.exists();out.mkdir()
    cases=[]
    for name,profile,p,reset in programs():
        events=oracle(p)
        rom=out/(name+'.hex');trace=out/(name+'.trace')
        rom.write_text(''.join(f'{p.words.get(BASE+4*i,0x13):08x}\n' for i in range(4096)))
        trace.write_text(''.join(' '.join(f'{v&0xffffffff:08x}' for v in e)+'\n' for e in events))
        cases.append(dict(name=name,profile=profile,events=len(events),rom=rom.relative_to(ROOT).as_posix(),
            trace=trace.relative_to(ROOT).as_posix(),reset_pending=reset,if_fault=p.meta.get('if_fault',0),
            data_fault=p.meta.get('data_fault',0),irq_load=DATA+4 if 'irq_after' in p.meta else 0,
            memory_target=p.meta.get('memory',{}).get(DATA+8,0),traps=sum(e[0]==1 for e in events),IRQ=sum(e[0]==2 for e in events)))
    seed=2026101430
    population=json.loads((ROOT/'sim/cpu_zmmul/test_plan.json').read_text())['supported_population']
    assert random.Random(seed).sample(population,2)==['auipc','sb']
    samples=[]
    boot=[(0x800000e4,0x74445073,2,0x74445073,0x800000e8),(0x800000f4,0x18005073,2,0x18005073,0x800000f8),
          (0x8000010c,0x3b029073,2,0x3b029073,0x80000118),(0x80000128,0x30205073,2,0x30205073,0x80000130)]
    for name in random.Random(seed).sample(population,2):
        dump=ROOT/f'MyCpu_test/dump/rv32ui-p-{name}.dump';text=dump.read_text()
        tohost=set(re.findall(r'#\s*([0-9a-fA-F]{8})\s*<tohost>',text));assert len(tohost)==1
        tail=text.split('<pass>:')[1];end=re.search(r'^([0-9a-f]{8}):\s+00000073\s+ecall',tail,re.M);assert end
        rom=ROOT/f'MyCpu_test/dat/{name}/{name}_rom.dat';words=[int(s,16) for s in rom.read_text().split()]
        expected=boot+[(int(end[1],16),0x73,11,0,0x80000004)]
        assert all(words[(pc-BASE)//4]==ins for pc,ins,_,_,_ in expected)
        path=out/(name+'.traps');path.write_text(''.join(' '.join(f'{v:08x}' for v in e)+'\n' for e in expected))
        ram=ROOT/f'MyCpu_test/dat/{name}/{name}_ram.dat'
        samples.append(dict(name=name,rom=rom.relative_to(ROOT).as_posix(),ram=ram.relative_to(ROOT).as_posix() if ram.exists() else None,
            tohost=int(next(iter(tohost)),16),traps=path.relative_to(ROOT).as_posix(),dump=dump.relative_to(ROOT).as_posix()))
    (HERE/'plan.json').write_text(json.dumps(dict(cases=cases,ISA_seed=seed,ISA_population=population,ISA_samples=samples),indent=2)+'\n')
    print('PROGRAM_ORACLES_STATIC_PASS',sum(c['events'] for c in cases),'events; nine cases; ISA=auipc,sb seed',seed)
if __name__=='__main__':main()
