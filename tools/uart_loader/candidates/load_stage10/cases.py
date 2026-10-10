"""Explicit LOAD stages and expected session state; no firmware oracle."""
from pathlib import Path
import json,struct
from protocol import BASE,LIMIT,crc,header,packet,response
ROOT=Path(__file__).resolve().parents[4]
PROGRAM=ROOT/'tests/uart_loader/program_stage10/build/program.bin'

class Builder:
    def __init__(self):
        self.seq=1;self.active=0;self.complete=0;self.total=0;self.received=0;self.image_crc=0;self.cases=[]
    def clear(self):self.active=self.complete=self.total=self.received=self.image_crc=0
    def add(self,name,tx,cmd,seq,status=0,address=BASE,accepted=0,actual_crc=0,write=0,read=0,**kw):
        self.cases.append(dict(name=name,cmd=cmd,seq=seq,status=status,tx_hex=tx.hex(),
            expected_hex=response(seq,cmd,status,address,accepted,actual_crc,self.image_crc,bool(self.complete)).hex(),
            address=address,write_bytes=write,read_bytes=read,image_complete=self.complete,image_active=self.active,
            image_total=self.total,image_received=self.received,image_crc=self.image_crc,**kw))
    def ping(self,name='ping',new_epoch=False):
        if new_epoch:self.clear();self.seq=1
        s=self.seq;self.seq+=1
        self.add(name,packet(1,s),1,s,accepted=self.received,new_epoch=new_epoch)
    def load(self,name,data,total=None,image_crc=None,flags=3,address=BASE,seq=None,status=0,body_status=0,duplicate=False,body=None,header_mutate=None):
        total=len(data) if total is None else total;image_crc=crc(data) if image_crc is None else image_crc
        s=self.seq if seq is None else seq
        h=header(2,s,address,len(data),total,image_crc,flags)
        if header_mutate:h=header_mutate(h)
        if status:
            self.clear();self.add(name+'_header_nack',h,2,s,status,address);return
        if not duplicate and flags&1:
            self.clear();self.active=1;self.total=total;self.image_crc=image_crc
        self.add(name+'_ready',h,2,s,1,address)
        tx=data+struct.pack('<I',crc(data)) if body is None else body
        if body_status:self.clear()
        elif not duplicate:
            self.received+=len(data);self.complete=int(bool(flags&2))
        self.add(name+'_final',tx,2,s,body_status,address,0 if body_status else len(data),
                 write=0 if body_status or duplicate else len(data),payload_offset=0,
                 image_end=bool(not body_status and flags&2))
        if not body_status:self.seq=max(self.seq,s+1)
    def image(self,data,name='program'):
        c=crc(data);total=len(data)
        for off in range(0,total,256):
            part=data[off:off+256];flags=int(off==0)| (2 if off+len(part)==total else 0)
            self.load(f'{name}_{off}',part,total,c,flags,BASE+off)
    def check_crc(self,data,name='diagnostic_read_crc'):
        s=self.seq;self.seq+=1
        self.add(name,packet(0x14,s,BASE,length=len(data),image_crc=crc(data)),0x14,s,
                 accepted=len(data),actual_crc=crc(data),read=len(data),image_end=True)

def cases(suite):
    b=Builder();raw=PROGRAM.read_bytes()
    b.ping('start',new_epoch=True)
    if suite=='positive' or suite=='native':
        b.image(raw);b.ping('loaded_unverified_ping');b.check_crc(raw);b.ping('still_rom_ping')
        if suite=='positive':
            # Exact retransmit of final block has its own READY, and zero DDR writes.
            b.image(raw,'restart')
            last=b.seq-1;off=256
            b.load('duplicate_final',raw[off:],len(raw),crc(raw),2,BASE+off,seq=last,duplicate=True)
            b.ping('duplicate_did_not_increment')
            b.ping('reset_retains_DDR_clears_session',new_epoch=True);b.check_crc(raw,'after_reset_physical_crc')
            for n in (1,2,3,4,255,256,257,1023):
                data=bytes((i*37+11)&255 for i in range(n));b.image(data,'boundary_'+str(n));b.check_crc(data)
    else:
        for name,addr,length,flags,total,expected in [
            ('zero',BASE,0,3,1,0x8003),('over_chunk',BASE,257,1,513,0x8003),
            ('stack',BASE+LIMIT,4,3,4,0x8002),('wrap',0xfffffffc,4,3,4,0x8002),
            ('unaligned',BASE+1,4,3,4,0x8002),('begin_offset',BASE+4,4,3,4,0x8002),
            ('total_zero',BASE,4,1,0,0x8003),('total_big',BASE,4,1,LIMIT+1,0x8003),
            ('nonfinal_tail',BASE,3,1,7,0x8003),('missing_END',BASE,4,1,4,0x8003),
            ('early_END',BASE,4,3,8,0x8003),('reserved_flags',BASE,4,7,4,0x8007),
            ('without_BEGIN',BASE,4,2,4,0x8008)]:
            b.load(name,b'x'*length,total,flags=flags,address=addr,status=expected);b.ping(name+'_recover')
        b.load('bad_header_crc',b'abcd',status=0x8001,header_mutate=lambda h:h[:-1]+bytes([h[-1]^1]))
        # Bad Header cannot trust SEQ/CMD; generic parser returns both zero, base address.
        b.cases[-1].update(seq=0,cmd=0,expected_hex=response(0,0,0x8001).hex())
        b.ping('bad_header_recover')
        for name,tail,status in [('bad_data_crc',b'abcd\0\0\0\0',0x8001),('truncated_body',b'ab',0x8004)]:
            b.load(name,b'abcd',body=tail,body_status=status);b.ping(name+'_recover')
        for name,params,status in [
            ('gap',{'address':BASE+8},0x8002),('changed_total',{'total':9},0x8008),
            ('changed_image_crc',{'image_crc':1},0x8008),('early_tail_END',{'flags':0},0x8003)]:
            c=crc(b'abcdefgh');b.load(name+'_begin',b'abcd',8,c,1)
            kw=dict(total=8,image_crc=c,flags=2,address=BASE+4);kw.update(params)
            b.load(name,b'efgh',status=status,**kw);b.ping(name+'_invalidated')
        c=crc(b'abcdefgh');b.load('duplicate_begin_seed',b'abcd',8,c,1);seq=b.seq-1
        b.load('duplicate_begin_exact',b'abcd',8,c,1,seq=seq,duplicate=True)
        b.load('duplicate_begin_changed',b'ABCD',8,c,1,seq=seq,duplicate=True,body_status=0x8009)
        b.ping('duplicate_changed_invalidated')
        b.load('session_timeout_begin',b'abcd',8,c,1)
        b.clear();b.add('wait_5s_session_timeout',b'',0,0,0x8004,delay_cycles=940000)
        b.ping('session_timeout_recover')
        b.image(raw,'real_program');b.check_crc(raw)
        for cmd in (3,4):
            s=b.seq;b.seq+=1;b.clear()
            b.add('reject_formal_'+str(cmd),packet(cmd,s,BASE,total=len(raw),image_crc=crc(raw)),cmd,s,0x8007)
            b.ping('reject_formal_recover_'+str(cmd))
    return b.cases

def materialize(folder,selected):
    requests=bytearray();responses=bytearray();metadata=[]
    for c in selected:
        tx=bytes.fromhex(c['tx_hex']);requests+=tx;responses+=bytes.fromhex(c['expected_hex'])
        metadata += [len(tx),int(c.get('new_epoch',False)),0,c['write_bytes'],c['read_bytes'],c['address'],
                     c.get('image_received',0),int(c.get('image_end',False)),c.get('payload_offset',32),
                     c.get('delay_cycles',0),c['image_complete'],c['image_active'],c['image_total'],c['image_received'],c['image_crc'],0]
    for name,data in [('requests',requests),('responses',responses)]:
        (folder/(name+'.hex')).write_text(''.join(f'{x:02x}\n' for x in data))
    (folder/'metadata.hex').write_text(''.join(f'{x:08x}\n' for x in metadata))
    (folder/'cases.json').write_text(json.dumps(selected,indent=2)+'\n')
    return bytes(requests),bytes(responses)
