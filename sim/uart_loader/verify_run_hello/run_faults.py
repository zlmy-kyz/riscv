"""Focused verified-state UART sticky event invalidation; event model, not pins."""
import importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/verify_run_hello'))
from cases import Builder,PROGRAM,control
from protocol import response
spec=importlib.util.spec_from_file_location('combined_runner',HERE/'run.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)


def fault_cases(_):
    b=Builder();raw=PROGRAM.read_bytes();b.ping('start',new_epoch=True)
    for event in (1,2):
        b.image(raw,'event_seed_'+str(event));control(b,3,'verified_before_UART_event_'+str(event),read=len(raw))
        b.clear();b.add('UART_sticky_invalidates_VERIFIED_'+str(event),b'',0,0,0x8005,delay_cycles=event)
        b.cases[-1]['expected_hex']=response(0,0,0x8005,uart_error_flags=16 if event==1 else 32).hex()
        b.ping('UART_recovery_'+str(event))
        control(b,4,'RUN_rejected_after_UART_'+str(event),0x8008);b.ping('RUN_recovery_'+str(event))
    b.image(raw,'Hello');control(b,3,'VERIFY_full_DDR',read=len(raw));control(b,4,'RUN_Hello',read=len(raw))
    return b.cases


if __name__=='__main__':
    target=HERE/'tb/tb_faults.v'
    if not target.exists():
        text=(HERE/'tb/tb_load.v').read_text()
        text=text.replace('repeat(metadata[case_index*16+9])@(negedge clk);', '''if(metadata[case_index*16+9]==1)begin
                @(negedge clk);force dut.u_uart_mmio.frame_error=1'b1;
                @(negedge clk);release dut.u_uart_mmio.frame_error;
            end else if(metadata[case_index*16+9]==2)begin
                @(negedge clk);force dut.u_uart_mmio.overflow=1'b1;
                @(negedge clk);release dut.u_uart_mmio.overflow;
            end''')
        text=text.replace('check(!dut.u_uart_mmio.frame_error_status', 'if(case_index<0 || metadata[case_index*16+9]==0)check(!dut.u_uart_mmio.frame_error_status')
        target.write_text(text)
    runner.SOURCES[-1]=target;runner.cases=fault_cases
    sys.argv=[str(HERE/'run.py'),'--suite','negative','--tag','uart_event_v2'];runner.main()
    report=ROOT/'sim/uart_loader/build/verify_run_hello/uart_event_v2/negative/results.json'
    data=json.loads(report.read_text());data['fault_transport']='MMIO_EVENT_MODEL_NOT_PHYSICAL_UART'
    data['physical_UART_faults_claimed']=False;report.write_text(json.dumps(data,indent=2)+'\n')
