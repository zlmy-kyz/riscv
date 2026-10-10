"""Offline independent board-verifier checks; fixture logs are not board evidence."""
from pathlib import Path
import copy,hashlib,json,sys,tempfile
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from check_pc_tool import Fixture,response
from check_board import verify,TOOLS
from acceptance import exercise,image_identity
from cases import board_cases
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def fixture_report(mode):
    selected=board_cases(mode);port=Fixture(selected)
    report=dict(mode=mode,port='COM11',baud=115200,image_sha256=image_identity(),input_sha256={p.name:sha(p) for p in sorted(TOOLS.glob('*.py'))},
                no_automatic_retry=True,load_verify_run_implemented=False,records=[],evidence_origin='OFFLINE_FIXTURE_NOT_BOARD')
    def hypothetical_break(p):
        result=port.break_fn(p);result['api']='Windows SetCommBreak/ClearCommBreak';return result
    exercise(port,selected,report,lambda:None,clock=port.clock,break_fn=hypothetical_break,emit=lambda *a,**k:None)
    return report

def main():
    results=[]
    with tempfile.TemporaryDirectory(prefix='stage8_diag_verifier_') as directory:
        folder=Path(directory)
        def test(name,report,reject=False):
            path=folder/(str(len(results))+'.json');path.write_text(json.dumps(report),encoding='utf8')
            error=None
            try:checked=verify(path,check_gate=False)
            except Exception as e:error=type(e).__name__+': '+str(e)
            assert (error is not None)==reject,(name,error)
            results.append(dict(name=name,result='PASS',expected_rejection=reject,error=error))
        full=fixture_report('all');test('117 raw responses checked independently',full)
        short=fixture_report('faults');test('9 raw responses checked independently',short)
        for name,flags in [('common 8005 without frame flags',0),('mixed frame and overflow flags',48),('frame instead of overflow',16)]:
            data=copy.deepcopy(full);i=114 if flags==16 else 110;c=board_cases('all')[i]
            data['records'][i]['rx_hex']=response(c,flags=flags).hex();test(name,data,True)
        data=copy.deepcopy(full);data['records'][110]['break_control']['set_success']=False;test('BREAK API failure metadata',data,True)
        data=copy.deepcopy(full);data['records'][114]['seconds_since_injection']=.01;test('early overflow response',data,True)
        data=copy.deepcopy(full);data['records'][115]['extra_rx_hex']='55';test('extra RX after recovery',data,True)
        data=copy.deepcopy(full);data['records']=data['records'][:-1];test('incomplete run',data,True)
        data=copy.deepcopy(full);data['image_sha256']['loader_rom.dat']='0'*64;test('wrong candidate identity',data,True)
        data=copy.deepcopy(full);data['records'][110]['rx_hex']=data['records'][114]['rx_hex'];test('replayed other UART error',data,True)
    path=ROOT/'sim/uart_loader/build/uart_fault_stage8_diag/pc/board_verifier_results.json'
    with path.open('x',encoding='utf8') as stream:stream.write(json.dumps(dict(status='DIAGNOSTIC_BOARD_VERIFIER_OFFLINE_PASS',board_result='NOT_TESTED',serial_opened=False,checks=results),indent=2)+'\n')
    print('RESULT: PASS',len(results),'independent board verifier offline checks; board NOT_TESTED')

if __name__=='__main__':main()
