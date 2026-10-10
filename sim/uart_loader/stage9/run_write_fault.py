"""Separate post-write physical damage/retry suite; doesn't alter approved main suites."""
from pathlib import Path
import sys
import run as runner
from cases import Builder,binary
from protocol import WRITE,RANGE_CRC,DDR_BASE,crc32
HERE=Path(__file__).resolve().parent

def cases():
    b=Builder();raw=binary(987,17)
    c=b.add('write_then_physical_damage',WRITE,DDR_BASE+3,raw,status=0x800b,write=True,read=True,new_epoch=True)
    b.memory[9]^=1;c['actual_crc']=crc32(b.memory[3:20])
    b.add('same_seq_ping_after_failed_write')
    b.add('rewrite_good',WRITE,DDR_BASE+3,raw,write=True,read=True)
    c=b.add('duplicate_write_physical_damage_no_rewrite',WRITE,DDR_BASE+3,raw,seq=2,status=0x800b,read=True)
    b.memory[9]^=1;c['actual_crc']=crc32(b.memory[3:20])
    c=b.add('duplicate_again_still_bad',WRITE,DDR_BASE+3,raw,seq=2,status=0x800b,read=True)
    b.add('new_seq_rewrite_good',WRITE,DDR_BASE+3,raw,write=True,read=True)
    b.add('whole_range_good',RANGE_CRC,DDR_BASE+3,length=17,image_crc=crc32(raw),read=True)
    return b.cases

def main():
    runner.SOURCES=runner.SOURCES[:-1]+[HERE/'tb/tb_write_fault.v']
    runner.negative_cases=cases
    sys.argv=[sys.argv[0],'--suite','negative','--tag','write_fault_v1']
    runner.main()

if __name__=='__main__':main()
