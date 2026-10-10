"""Parse frozen UART counters and verify CoreMark through the existing strict CRC parser."""
from pathlib import Path
import sys,re
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/bsp_workflow'))
from application import parse_output
NAMES='cycles instret if_stall_cycles mem_stall_cycles branch_flush_cycles control_redirect_cycles control_hold_cycles load_use_cycles other_cycles ddr_transactions branch_redirects ddr_ar_commands ddr_aw_commands'.split()
def check(info,raw,board=False,elapsed=None):
    prefix,sep,suffix=raw.partition(b'PERF2B version=')
    assert sep and b'PERF2B ' not in prefix
    crc=parse_output(info,prefix,board=board,elapsed=elapsed)
    lines=(sep+suffix).decode('ascii').replace('\r\n','\n').splitlines()
    m=re.fullmatch(r'PERF2B version=1 state=3 start=(\d+) stop=(\d+)',lines[0]);assert m
    assert len(lines)==15 and lines[-1]=='PERF2B_DONE'
    counts={}
    for name,line in zip(NAMES,lines[1:-1]):
        m=re.fullmatch(r'PERF2B '+name+r'=([0-9a-fA-F]{16})',line);assert m,(name,line)
        counts[name]=int(m[1],16)
    start,stop=map(int,re.fullmatch(r'PERF2B version=1 state=3 start=(\d+) stop=(\d+)',lines[0]).groups())
    assert ((stop-start)&0xffffffff)==crc['ticks']==counts['cycles']
    assert sum(counts[n] for n in NAMES[2:9])==counts['cycles']
    assert counts['ddr_transactions']==counts['ddr_ar_commands']+counts['ddr_aw_commands']
    assert 0<counts['instret']<=counts['cycles']
    return dict(status='PERF2B_UART_COUNTERS_AND_COREMARK_PASS',crc=crc,counters=counts,
        cpi=counts['cycles']/counts['instret'],timer_start=start,timer_stop=stop,
        origin='ACTUAL_BOARD' if board else 'FUNCTIONAL_SIMULATION_NOT_DDR_PERFORMANCE')
