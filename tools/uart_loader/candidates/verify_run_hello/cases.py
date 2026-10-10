"""Explicit LOAD stages and expected session state; no firmware oracle."""
from pathlib import Path
import json,struct
from protocol import BASE,LIMIT,crc,header,packet,response
ROOT=Path(__file__).resolve().parents[4]
PROGRAM=ROOT/'tests/uart_loader/program_hello/build/program.bin'

class Builder:
    def __init__(self):
        self.verified=0;self.seq=1;self.active=0;self.complete=0;self.total=0;self.received=0;self.image_crc=0;self.cases=[]
    def clear(self):self.verified=0;self.active=self.complete=self.total=self.received=self.image_crc=0
    def add(self,name,tx,cmd,seq,status=0,address=BASE,accepted=0,actual_crc=0,write=0,read=0,**kw):
        self.cases.append(dict(name=name,cmd=cmd,seq=seq,status=status,tx_hex=tx.hex(),
            expected_hex=response(seq,cmd,status,address,accepted,actual_crc,self.image_crc,bool(self.complete),verified=bool(self.verified)).hex(),
            address=address,write_bytes=write,read_bytes=read,image_complete=self.complete,image_active=self.active,
            image_total=self.total,image_received=self.received,image_crc=self.image_crc,image_verified=self.verified,**kw))
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

def materialize(folder,selected):
    requests=bytearray();responses=bytearray();metadata=[]
    for c in selected:
        tx=bytes.fromhex(c['tx_hex']);requests+=tx;responses+=bytes.fromhex(c['expected_hex'])
        metadata += [len(tx),int(c.get('new_epoch',False)),c.get('inject_offset',0),c['write_bytes'],c['read_bytes'],c['address'],
                     c.get('image_received',0),int(c.get('image_end',False)),c.get('payload_offset',32),
                     c.get('delay_cycles',0),c['image_complete'],c['image_active'],c['image_total'],c['image_received'],c['image_crc'],c['image_verified']]
    for name,data in [('requests',requests),('responses',responses)]:
        (folder/(name+'.hex')).write_text(''.join(f'{x:02x}\n' for x in data))
    (folder/'metadata.hex').write_text(''.join(f'{x:08x}\n' for x in metadata))
    (folder/'cases.json').write_text(json.dumps(selected,indent=2)+'\n')
    if selected[-1].get('run'): responses+=b'Hello World\r\n'
    (folder/'responses.hex').write_text(''.join(f'{x:02x}\n' for x in responses))
    return bytes(requests),bytes(responses)

def control(b,cmd,name,status=0,read=0,actual=None,**kw):
    raw=PROGRAM.read_bytes();seq=kw.pop('seq',b.seq);b.seq=max(b.seq,seq+1)
    params=dict(address=BASE,length=len(raw),total=len(raw),image_crc=crc(raw))
    inject=kw.pop('inject_offset',0);tx_override=kw.pop('tx_override',None)
    params.update(kw)
    tx=packet(cmd,seq,**params) if tx_override is None else tx_override
    if status: b.clear()
    elif cmd==3: b.verified=1
    b.add(name,tx,cmd,seq,status,params['address'],accepted=0 if status else len(raw),
          actual_crc=0 if actual is None and not read else crc(raw) if actual is None else actual,
          read=read,inject_offset=inject,run=bool(cmd==4 and not status))

def cases(suite):
    b=Builder();raw=PROGRAM.read_bytes();b.ping('start',new_epoch=True)
    if suite=='negative':
        control(b,3,'VERIFY_empty',0x8008);b.ping('empty_recovery')
        control(b,4,'RUN_empty',0x8008);b.ping('run_empty_recovery')
        invalid=[('unaligned',BASE+1,0x8002),('ROM',0,0x8002),('MMIO',0x10001000,0x8002),
                 ('stack',BASE+LIMIT,0x8002),('nonbase',BASE+4,0x8002),('wrap',0xfffffffc,0x8002)]
        for name,address,status in invalid:
            b.image(raw,name+'_seed');control(b,3 if name=='ROM' else 4,name,status,address=address);b.ping(name+'_recovery')
        for name,params,status in [
            ('short_range',dict(length=4),0x8003),('identity_length',dict(length=4,total=4),0x8008),
            ('image_identity',dict(image_crc=1),0x8008),('flags',dict(flags=1),0x8007),
            ('version',dict(version=2),0x8006),('SEQ0',dict(seq=0),0x8009),
            ('over_window',dict(length=LIMIT+1,total=LIMIT+1),0x8003)]:
            b.image(raw,name+'_seed');control(b,3,name,status,**params);b.ping(name+'_recovery')
        b.image(raw,'unverified_seed');control(b,4,'RUN_unverified',0x8008);b.ping('unverified_recovery')
        b.image(raw,'diagnostic_seed');b.check_crc(raw);control(b,4,'diagnostic_not_VERIFY',0x8008);b.ping('diagnostic_recovery')
        b.load('incomplete',raw[:256],len(raw),crc(raw),1)
        control(b,3,'VERIFY_missing_END',0x8008);b.ping('incomplete_recovery')
        for off in range(0,len(raw),256):
            part=raw[off:off+256]
            b.load('wrong_image_crc_'+str(off),part,len(raw),crc(raw)^1,int(off==0)|(2 if off+len(part)==len(raw) else 0),BASE+off)
        control(b,3,'full_DDR_wrong_crc',0x8001,read=len(raw),image_crc=crc(raw)^1);b.ping('wrong_crc_recovery')
        b.image(raw,'damaged_VERIFY_seed');bad=bytearray(raw);bad[26]^=1
        control(b,3,'damaged_VERIFY',0x8001,read=len(raw),actual=crc(bad),inject_offset=27);b.ping('damaged_VERIFY_recovery')
        b.image(raw,'damaged_RUN_seed');control(b,3,'verified_before_damage',read=len(raw))
        control(b,4,'RUN_rechecks_DDR',0x8001,read=len(raw),actual=crc(bad),inject_offset=27);b.ping('damaged_RUN_recovery')
        b.image(raw,'duplicate_VERIFY_seed');s=b.seq;control(b,3,'first_VERIFY',read=len(raw))
        control(b,3,'same_SEQ_VERIFY_rejected',0x8009,seq=s);b.ping('duplicate_recovery')
        b.image(raw,'bad_control_tail_seed');s=b.seq
        control(b,3,'bad_control_tail',0x8001,tx_override=packet(3,s,BASE,length=len(raw),total=len(raw),image_crc=crc(raw))[:-4]+b'\1\0\0\0')
        b.ping('bad_tail_recovery')
        b.image(raw,'bad_header_seed');s=b.seq
        tx=bytearray(packet(3,s,BASE,length=len(raw),total=len(raw),image_crc=crc(raw)));tx[28]^=1
        b.clear();b.add('bad_header',bytes(tx),0,0,0x8001);b.seq+=1;b.ping('bad_header_recovery')
        b.image(raw,'new_BEGIN_seed');control(b,3,'verified_before_new_BEGIN',read=len(raw))
        b.image(raw,'replacement');control(b,4,'new_BEGIN_revokes_VERIFY',0x8008);b.ping('replacement_recovery')
    b.image(raw,'Hello')
    b.ping('loaded_unverified')
    control(b,3,'VERIFY_full_DDR',read=len(raw));b.ping('verified_status')
    if suite=='positive':control(b,3,'VERIFY_repeat_new_SEQ',read=len(raw));b.ping('still_verified')
    control(b,4,'RUN_Hello',read=len(raw))
    return b.cases
