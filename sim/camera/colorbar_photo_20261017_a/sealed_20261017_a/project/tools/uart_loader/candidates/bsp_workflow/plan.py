"""Generate one stop-and-wait application download, VERIFY and exactly one RUN."""
from pathlib import Path
import importlib.util,struct
ROOT=Path(__file__).resolve().parents[4]
spec=importlib.util.spec_from_file_location('rvld',ROOT/'tools/uart_loader/candidates/verify_run_hello/protocol.py')
rvld=importlib.util.module_from_spec(spec);spec.loader.exec_module(rvld)

def make_plan(info):
    raw=(ROOT/info['bin_path']).read_bytes();assert len(raw)==info['bytes'] and rvld.crc(raw)==info['crc32']
    seq=1;received=0;rows=[]
    def add(name,tx,cmd,status=0,address=rvld.BASE,accepted=0,actual_crc=0,complete=False,verified=False,write=0,read=0,**kw):
        rows.append(dict(name=name,tx_hex=tx.hex(),cmd=cmd,seq=seq,status=status,address=address,
            expected_hex=rvld.response(seq,cmd,status,address,accepted,actual_crc,info['crc32'] if cmd!=1 else 0,complete,verified=verified).hex(),
            received=received,complete=int(complete),verified=int(verified),write_bytes=write,read_bytes=read,**kw))
    # Initial PING has no loaded image and therefore image CRC 0.
    add('PING_fresh_loader',rvld.packet(1,seq),1);seq+=1
    for offset in range(0,len(raw),256):
        part=raw[offset:offset+256];address=rvld.BASE+offset;last=offset+len(part)==len(raw)
        flags=int(offset==0)|(2 if last else 0)
        add(f'LOAD_{offset}_READY',rvld.header(2,seq,address,len(part),len(raw),info['crc32'],flags),2,1,address)
        received+=len(part)
        add(f'LOAD_{offset}_ACK',part+struct.pack('<I',rvld.crc(part)),2,0,address,len(part),complete=last,write=len(part),image_end=last)
        seq+=1
    for cmd,name in ((3,'VERIFY_whole_DDR'),(4,'RUN_once')):
        add(name,rvld.packet(cmd,seq,rvld.BASE,length=len(raw),total=len(raw),image_crc=info['crc32']),cmd,
            accepted=len(raw),actual_crc=info['crc32'],complete=True,verified=True,read=len(raw),run=cmd==4)
        seq+=1
    return rows

def materialize(folder,info):
    rows=make_plan(info);requests=bytearray();responses=bytearray();metadata=[]
    for i,row in enumerate(rows):
        tx=bytes.fromhex(row['tx_hex']);requests+=tx;responses+=bytes.fromhex(row['expected_hex'])
        is_ping=i==0;length=info['bytes'] if not is_ping else 0
        metadata += [len(tx),0,0,row['write_bytes'],row['read_bytes'],row['address'],row['received'],
                     int(row.get('image_end',False)),0,0,row['complete'],0 if is_ping else 1,length,
                     row['received'],0 if is_ping else info['crc32'],row['verified']]
    for name,data in [('requests',requests),('responses',responses)]:
        (folder/(name+'.hex')).write_text(''.join(f'{b:02x}\n' for b in data))
    (folder/'metadata.hex').write_text(''.join(f'{n:08x}\n' for n in metadata))
    return rows,bytes(requests),bytes(responses)
