"""Focused malformed control bodies revoke VERIFIED and never enter DDR code."""
import importlib.util,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/verify_run_hello'))
from cases import Builder,PROGRAM,control
from protocol import packet,crc,BASE
spec=importlib.util.spec_from_file_location('combined_control_runner',HERE/'run.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)


def selected(_):
    b=Builder();raw=PROGRAM.read_bytes();b.ping('start',new_epoch=True)
    for mode in ('partial_RUN_body','bad_RUN_body_CRC','partial_VERIFY_body'):
        b.image(raw,mode+'_seed');control(b,3,mode+'_verified',read=len(raw))
        cmd=3 if mode=='partial_VERIFY_body' else 4
        tx=packet(cmd,b.seq,BASE,length=len(raw),total=len(raw),image_crc=crc(raw))
        tx=tx[:-2] if mode.startswith('partial') else tx[:-4]+b'\1\0\0\0'
        control(b,cmd,mode,0x8004 if mode.startswith('partial') else 0x8001,tx_override=tx)
        b.ping(mode+'_recovery');control(b,4,mode+'_RUN_revoked',0x8008);b.ping(mode+'_state_recovery')
    b.image(raw,'Hello');control(b,3,'VERIFY_final',read=len(raw));control(b,4,'RUN_final',read=len(raw))
    return b.cases


if __name__=='__main__':
    runner.cases=selected;sys.argv=[str(HERE/'run.py'),'--suite','negative','--tag','control_v1'];runner.main()
