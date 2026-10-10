"""Deterministic boundary corpus and independent physical-byte oracle."""
from pathlib import Path
import hashlib,json,random
from protocol import *
BOUNDARIES=[1,2,3,4,15,16,17,255,256,257,1023,16368,16369,61440]
SEED=0x20261009
sha=lambda data:hashlib.sha256(data).hexdigest()

def binary(index,length,seed=SEED):
    rng=random.Random((seed<<32)|index)
    raw=bytearray(rng.getrandbits(8) for _ in range(length))
    marker=b'\x00\xffRVLD\r\n\x80\x7f'
    raw[:min(len(marker),length)]=marker[:length]
    return bytes(raw)

def corpus(directory,kind='board'):
    directory=Path(directory)
    rng=random.Random(SEED)
    lengths=BOUNDARIES+[rng.randint(1,LIMIT if kind=='board' else 1024) for _ in range(100)]
    if kind=='board':lengths += [rng.randint(1,1024) for _ in range(1000-len(lengths))]
    if directory.exists():
        saved=json.loads((directory/'manifest.json').read_text())
        assert saved['kind']==kind and saved['seed']==SEED and [e['bytes'] for e in saved['images']]==lengths
        for entry in saved['images']:
            raw=(directory/entry['file']).read_bytes();assert sha(raw)==entry['sha256'] and crc32(raw)==entry['crc32']
        return saved
    directory.mkdir(parents=True)
    images=[]
    for index,length in enumerate(lengths):
        raw=binary(index,length);name=f'image_{index:04d}_{length}.bin';(directory/name).write_bytes(raw)
        images.append(dict(index=index,file=name,bytes=length,crc32=crc32(raw),sha256=sha(raw)))
    saved=dict(kind=kind,seed=SEED,images=images,image_count=len(images),payload_bytes=sum(lengths),
               boundary_lengths=BOUNDARIES,full_range_random_images=100 if kind=='board' else 0,
               random_small_images=886 if kind=='board' else 100,execute_random_data=False)
    (directory/'manifest.json').write_text(json.dumps(saved,indent=2)+'\n');return saved

class Builder:
    def __init__(self):self.memory=bytearray([0xa5])*65536;self.seq=1;self.cases=[]
    def add(self,name,cmd=1,address=0,data=b'',length=None,status=0,seq=None,write=False,read=False,**kw):
        sequence=self.seq if seq is None else seq;length=len(data) if length is None else length
        raw=packet(cmd,sequence,address,data,length=length,image_crc=kw.pop('image_crc',0),**kw.pop('packet_args',{}))
        if write:self.memory[address-DDR_BASE:address-DDR_BASE+length]=data
        actual=crc32(self.memory[address-DDR_BASE:address-DDR_BASE+length]) if read else 0
        case=dict(name=name,cmd=cmd,seq=sequence,status=status,tx_hex=raw.hex(),address=address,length=length,
                  accepted=length if cmd in (WRITE,RANGE_CRC) and not status else 0 if cmd==1 else None,
                  response_address=address if cmd in (WRITE,RANGE_CRC) else None,actual_crc=actual,
                  write_bytes=length if write else 0,read_bytes=length if read else 0,**kw)
        if not status and (seq is None or sequence>=self.seq):self.seq=sequence+1
        self.cases.append(case);return case
    def image(self,raw,name):
        n=len(raw);guard=b'\x5a\xc3\x7e'
        if n+3<=LIMIT:self.add(name+'_guard_set',WRITE,DDR_BASE+n,guard,write=True,read=True)
        for offset in range(0,n,CHUNK):self.add(f'{name}_chunk_{offset}',WRITE,DDR_BASE+offset,raw[offset:offset+CHUNK],write=True,read=True)
        self.add(name+'_crc',RANGE_CRC,DDR_BASE,length=n,image_crc=crc32(raw),read=True,image_end=True)
        if n+3<=LIMIT:self.add(name+'_tail_guard',RANGE_CRC,DDR_BASE+n,length=3,image_crc=crc32(guard),read=True)

def positive_cases(corpus_dir,native=False):
    plan=corpus(corpus_dir,'sim');b=Builder()
    images=plan['images'][:10] if native else plan['images']
    for entry in images:b.image((Path(corpus_dir)/entry['file']).read_bytes(),f"image_{entry['index']:04d}_{entry['bytes']}")
    b.cases[0]['new_epoch']=True
    return b

def negative_cases():
    b=Builder();raw=binary(123,17)
    b.add('seed',WRITE,DDR_BASE+3,raw,write=True,read=True)
    b.add('exact_duplicate',WRITE,DDR_BASE+3,raw,seq=1,read=True)
    b.add('same_seq_changed_data',WRITE,DDR_BASE+3,raw[:-1]+bytes([raw[-1]^1]),seq=1,status=0x8009)
    b.add('same_seq_changed_address',WRITE,DDR_BASE+4,raw,seq=1,status=0x8009)
    b.add('same_seq_changed_length',WRITE,DDR_BASE+3,raw[:-1],seq=1,status=0x8009)
    b.add('same_seq_other_command',RANGE_CRC,DDR_BASE+3,length=17,image_crc=crc32(raw),seq=1,status=0x8009)
    b.add('stale_seq',WRITE,DDR_BASE,raw,seq=0,status=0x8009)
    negatives=[('before_window',WRITE,DDR_BASE-1,1,0x8002),('stack_start',WRITE,DDR_BASE+LIMIT,1,0x8002),
               ('wrap',WRITE,0xffffffff,1,0x8002),('write_cross_stack',WRITE,DDR_BASE+LIMIT-1,2,0x8002),
               ('write_empty',WRITE,DDR_BASE,0,0x8003),('write257',WRITE,DDR_BASE,257,0x8003),
               ('write_huge',WRITE,DDR_BASE,0xffffffff,0x8003),('crc_empty',RANGE_CRC,DDR_BASE,0,0x8003),
               ('crc_over_limit',RANGE_CRC,DDR_BASE,LIMIT+1,0x8003),('crc_cross_stack',RANGE_CRC,DDR_BASE+1,LIMIT,0x8002),
               ('crc_stack',RANGE_CRC,DDR_BASE+LIMIT,1,0x8002)]
    for name,cmd,address,length,status in negatives:
        b.add(name,cmd,address,b'x' if cmd==WRITE else b'',length,status,recover=True)
        b.add(name+'_recover')
        b.add(name+'_seed_crc',RANGE_CRC,DDR_BASE+3,length=17,image_crc=crc32(raw),read=True)
    for name,params,status in [('total',{'total':1},0x8003),('version',{'version':2},0x8006),('flags',{'flags':1},0x8007)]:
        b.add(name,WRITE,DDR_BASE,raw,status=status,packet_args=params,recover=True);b.add(name+'_recover')
    b.add('unexpected_write_image_crc',WRITE,DDR_BASE,raw,image_crc=1,status=0x8008,recover=True);b.add('state_recover')
    bad=b.add('bad_chunk_data_crc',WRITE,DDR_BASE,raw,status=0x8001,recover=True)
    wire=bytes.fromhex(bad['tx_hex']);bad['tx_hex']=(wire[:-1]+bytes([wire[-1]^1])).hex();b.add('bad_data_recover')
    bad=b.add('truncated_256_body',WRITE,DDR_BASE,raw,length=256,status=0x8004,recover=True)
    bad['tx_hex']=bad['tx_hex'][:(32+17)*2];b.add('timeout_recover')
    b.add('wrong_expected_crc',RANGE_CRC,DDR_BASE+3,length=17,image_crc=crc32(raw)^1,status=0x8001,read=True)
    b.add('correct_same_seq',RANGE_CRC,DDR_BASE+3,length=17,image_crc=crc32(raw),read=True)
    # Change physical memory, not UART payload or expected CRC, then reread twice.
    b.memory[9]^=1
    changed=b.add('physical_corruption',RANGE_CRC,DDR_BASE+3,length=17,image_crc=crc32(raw),status=0x8001,read=True,inject_offset=9)
    b.add('physical_corruption_repeat',RANGE_CRC,DDR_BASE+3,length=17,image_crc=crc32(raw),status=0x8001,read=True)
    b.add('rewrite_after_corruption',WRITE,DDR_BASE+3,raw,write=True,read=True)
    b.add('physical_recover_crc',RANGE_CRC,DDR_BASE+3,length=17,image_crc=crc32(raw),read=True)
    b.add('last_valid_byte',WRITE,DDR_BASE+LIMIT-1,b'\xff',write=True,read=True)
    b.add('last_byte_crc',RANGE_CRC,DDR_BASE+LIMIT-1,length=1,image_crc=crc32(b'\xff'),read=True)
    b.add('after_reset_old_seq',WRITE,DDR_BASE+3,raw,seq=1,write=True,read=True,new_epoch=True)
    b.seq=2;b.add('after_reset_retained_crc',RANGE_CRC,DDR_BASE+3,length=17,image_crc=crc32(raw),read=True)
    b.cases[0]['new_epoch']=True
    return b.cases

def materialize(folder,cases):
    folder=Path(folder);rx=b''.join(bytes.fromhex(c['tx_hex']) for c in cases);tx=b''.join(response(c) for c in cases)
    for name,data in [('requests',rx),('responses',tx)]:
        (folder/(name+'.bin')).write_bytes(data);(folder/(name+'.hex')).write_text(''.join(f'{v:02x}\n' for v in data))
    # reset, inject byte offset+1 (0=no injection), expected DDR write/read byte totals.
    meta=[]
    for c in cases:meta += [len(bytes.fromhex(c['tx_hex'])),int(c.get('new_epoch',False)),c.get('inject_offset',-1)+1,c['write_bytes'],c['read_bytes'],c.get('address',DDR_BASE),c.get('length',0),int(c.get('image_end',False))]
    (folder/'metadata.hex').write_text(''.join(f'{v:08x}\n' for v in meta))
    (folder/'cases.json').write_text(json.dumps(cases,indent=2)+'\n');return rx,tx
