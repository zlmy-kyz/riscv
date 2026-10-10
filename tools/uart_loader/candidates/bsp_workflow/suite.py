"""User-operated ten KEY0 epochs, same bitstream and unified build/download workflow."""
from pathlib import Path
import argparse,datetime,json,subprocess,sys
from application import ROOT
from upload import require_gate,sha
SEQUENCE=('hello','crc32','performance_1','validation_1','hello','crc32','performance_1','validation_1','performance_60','validation_60')
def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,default=ROOT/'sim/bsp_workflow/board/first');a=p.parse_args()
    folder=a.directory.resolve();assert not folder.exists(),'Preserve all logs; choose a new --directory'
    for name in set(SEQUENCE):require_gate(ROOT/f'tests/bsp_workflow/build/{name}/manifest.json')
    folder.mkdir(parents=True);journal=folder/'suite.json'
    result=dict(status='RUNNING',evidence_origin='USER_OPERATED_ACTUAL_SERIAL_SUITE',sequence=list(SEQUENCE),records=[],
                FPGA_programming_independently_observed=False,KEY0_independently_observed=False,bitstream_rebuilt=False)
    save=lambda:journal.write_text(json.dumps(result,indent=2)+'\n')
    save();short={}
    print('Keep the successful VERIFY/RUN/Hello Loader bitstream; close the serial terminal. Ten rounds, no FPGA rebuild.')
    try:
        for i,name in enumerate(SEQUENCE,1):
            input(f'[{i}/10 {name}] Press KEY0, release, wait for DDR initialization, then Enter: ')
            row=dict(round=i,application=name,user_KEY0_confirmation=True,start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),result='RUNNING')
            result['records'].append(row);save()
            log=folder/f'round_{i:02}_{name}.json'
            command=[sys.executable,str(ROOT/'tests/bsp_workflow/run.py'),'--application',name,'--port','COM11','--log',str(log)]
            if name.endswith('_60'):command+=['--crc-log',str(short[name.rsplit('_',1)[0]])]
            completed=subprocess.run(command)
            row.update(log_path=log.as_posix(),log_sha256=sha(log) if log.exists() else None,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
            if completed.returncode:row['result']='FAIL';raise RuntimeError(f'Round {i} failed; preserve log; no automatic retry')
            row['result']='PASS';save()
            if name.endswith('_1'):short[name.rsplit('_',1)[0]]=log
        result['status']='AWAITING_AUDIT';save()
        audit=folder/'board_result.json'
        completed=subprocess.run([sys.executable,str(ROOT/'sim/bsp_workflow/check_ten.py'),'--directory',str(folder),'--output',str(audit)])
        if completed.returncode:raise RuntimeError('Independent ten-round audit failed')
        result.update(status='UNIFIED_BSP_TEN_ROUND_BOARD_PASS',independent_result_sha256=sha(audit));save()
        print('RESULT: PASS all ten reset/download/VERIFY/RUN rounds. Logs:',folder)
    except BaseException as error:
        result.update(status='FAIL',error=str(error));save();raise
if __name__=='__main__':main()
