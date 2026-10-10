"""Physical BREAK and early-DATA FIFO overflow invalidate an active LOAD."""
import run
from cases import Builder,PROGRAM,materialize
from protocol import BASE,crc,response
from pathlib import Path

def selected(suite):
    b=Builder();b.ping('fault_reset',new_epoch=True);data=b'abcd';full_crc=crc(b'abcdefgh')
    b.load('LOAD_body_BREAK',data,8,full_crc,1,body=b'',body_status=0x8005)
    b.cases[-1]['wire_fault']=1
    b.cases[-1]['expected_hex']=response(b.cases[-1]['seq'],2,0x8005,BASE,uart_error_flags=0x10).hex()
    b.ping('BREAK_invalidated_recovery')
    b.load('LOAD_READY_early_flood',data,8,full_crc,1,body=b'',body_status=0x8005)
    # Deliberately violate stop-and-wait while CPU sends READY; real 16-byte FIFO.
    h=b.cases[-2];h['tx_hex'] += ('f0'*96);h['wire_fault']=2
    h.update(image_active=0,image_complete=0,image_total=0,image_received=0,image_crc=0)
    final=b.cases[-1];final['expected_hex']=response(final['seq'],2,0x8005,BASE,uart_error_flags=0x20).hex()
    b.ping('overflow_invalidated_recovery')
    raw=PROGRAM.read_bytes();b.image(raw,'recover_real');b.ping('complete_unverified');b.check_crc(raw);b.ping('no_execution')
    return b.cases

def metadata(folder,cases):
    requests,responses=materialize(folder,cases)
    values=[int(line,16) for line in (folder/'metadata.hex').read_text().split()]
    for index,case in enumerate(cases):values[index*16+15]=case.get('wire_fault',0)
    (folder/'metadata.hex').write_text(''.join(f'{v:08x}\n' for v in values))
    return requests,responses

run.cases=selected;run.materialize=metadata
run.SOURCES[-1]=Path(__file__).parent/'tb/tb_load_faults.v'
if __name__=='__main__':run.main()
