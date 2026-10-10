"""Additional formal LOAD boundary/session negatives; preserve passing v1 suites."""
import run
from cases import Builder,PROGRAM
from protocol import BASE,crc,header,packet

def selected(suite):
    b=Builder();b.ping('extended_reset',new_epoch=True)
    full=b'abcdefgh';c=crc(full)
    for name,changes in [('changed_header_address',dict(address=BASE+4)),
                         ('changed_header_total',dict(total=9)),
                         ('changed_header_image_crc',dict(image_crc=1)),
                         ('changed_header_flags',dict(flags=3)),
                         ('changed_header_length',dict(data=b'abcdefgh'))]:
        b.load(name+'_seed',b'abcd',8,c,1);s=b.seq-1
        kw=dict(data=b'abcd',total=8,image_crc=c,flags=1,seq=s);kw.update(changes)
        b.load(name,status=0x8009,**kw);b.ping(name+'_recover')
    b.load('wrong_version',b'abcd',status=0x8006,header_mutate=lambda h:header(2,b.seq,BASE,4,4,crc(b'abcd'),3,2));b.ping('version_recover')
    b.load('zero_seq',b'abcd',seq=0,status=0x8009);b.ping('zero_seq_recover')
    b.load('cross_stack',b'abcd',8,c,1,address=BASE+61436,status=0x8002);b.ping('cross_stack_recover')
    b.load('begin_then_ping',b'abcd',8,c,1);old=b.seq-1;b.ping('ping_partial_reports_four')
    b.load('stale_previous_load',b'abcd',8,c,1,seq=old,status=0x8009);b.ping('stale_invalidated')
    b.load('partial_header_seed',b'abcd',8,c,1)
    tx=header(2,b.seq,BASE+4,4,8,c,2)[:19];b.clear();b.add('partial_header_timeout',tx,0,0,0x8004)
    b.ping('partial_header_invalidated')
    b.load('new_BEGIN_seed',b'abcd',8,c,1)
    replacement=b'HELLO\0\xff';b.image(replacement,'new_BEGIN_replaces_incomplete');b.check_crc(replacement)
    b.load('RUN_while_receiving_seed',b'abcd',8,c,1)
    s=b.seq;b.seq+=1;b.clear();b.add('RUN_while_receiving_rejected',packet(4,s,BASE,total=8,image_crc=c),4,s,0x8007)
    b.ping('RUN_rejection_invalidates')
    b.image(PROGRAM.read_bytes(),'recover_real_program');b.check_crc(PROGRAM.read_bytes())
    return b.cases

run.cases=selected
if __name__=='__main__':run.main()
