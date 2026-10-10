"""Finite progress reporter for an already running stage8 simulator."""
import json,re,time
from pathlib import Path
B=Path('D:/riscv/RISCV/sim/uart_loader/build/ack_nack_stage8_repaired/full')
last=-1
for _ in range(80):
    log=(B/'full/transcript').read_text(errors='replace') if (B/'full/transcript').exists() else ''
    done=re.findall(r'CHECK: RX case=(\d+) pings=(\d+) tests=\d+ nacks=(\d+) last_seq=(\d+)',log)
    if done:
        c,p,n,s=map(int,done[-1])
        if c!=last:
            print(f'RECHECK {c+1}/114 frames checked; PING={p}; NACK={n}; last successful SEQ={s}',flush=True);last=c
    result=json.loads((B/'results.json').read_text())
    if result['status']!='RUNNING':
        print('RECHECK FINISHED:',result['status'],flush=True);break
    time.sleep(45)
else:
    print('REPORTER FINISHED: simulator still running; inspect results.json',flush=True)
