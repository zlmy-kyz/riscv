"""Create an isolated stage 8 candidate by byte copying, without rebuilding."""
from pathlib import Path
import hashlib, json
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'tests/uart_loader/verified/ddr_crc_stage7'
target=ROOT/'tests/uart_loader/candidates/ack_nack_stage8'
entries=[]
for p in source.rglob('*'):
    if p.is_file():
        q=target/p.relative_to(source); q.parent.mkdir(parents=True,exist_ok=True)
        if q.exists() and q.read_bytes()!=p.read_bytes(): raise RuntimeError(f'different existing candidate: {q}')
        if not q.exists(): q.write_bytes(p.read_bytes())
        entries.append(dict(source=str(p.relative_to(ROOT)),candidate=str(q.relative_to(ROOT)),sha256=sha(q)))
(ROOT/'tools/uart_loader/candidates/ack_nack_stage8/protocol.py').write_bytes((ROOT/'tools/uart_loader/verified/ddr_crc_stage7/protocol.py').read_bytes())
(HERE/'candidate_receipt.json').write_text(json.dumps(dict(rebuild_performed=False,entries=entries),indent=2)+'\n',encoding='utf8')
# Keep the production TB and its historical inputs unchanged. Extend a copy.
s=(ROOT/'sim/uart_loader/tb/tb_uart_loader.v').read_text(encoding='utf8')
s=s.replace('PING_COUNT=100);','PING_COUNT=100, CASES=114, TIME_SCALE=64);')
s=s.replace('frame_lengths[0:20], case_state[0:125], ddr_state[0:83], crc_state[0:146]', 'frame_lengths[0:511], case_state[0:3071], ddr_state[0:2047], crc_state[0:3583]')
s=s.replace('string lengths_path,state_path;', '''string lengths_path,state_path,fault_path;
    reg [31:0] faults[0:511];
    reg [31:0] virtual_cycle=0;
    integer injected_frame=0,injected_overflow=0,error_clears=0,dropped=0;
    integer pop_index=0,lbu_index=0,drop_index=-1;
    realtime case_start;
    integer timing_fd;
    string timing_path;
    // Only the MMIO cycle time source is scaled. CPU, UART, DDR remain at 93.75 MHz.
    // TIME_SCALE=1 is the independent native 100ms timeout confirmation suite.
    generate if(TIME_SCALE!=1) begin
        always @(negedge clk) begin
            if(!resetn) virtual_cycle=0;
            else virtual_cycle=virtual_cycle+TIME_SCALE;
        end
        initial force dut.u_simple_mmio.cycle_counter=virtual_cycle;
    end endgenerate''')
s=s.replace('for(byte_no=0;byte_no<frame_lengths[frame_index];byte_no=byte_no+1) begin', '''case_start=$realtime;
            if(faults[frame_index]==2) begin
                // Service-starvation injection: fill the real FIFO with real UART pin bytes.
                // Holding only its bus request preserves the waiting CPU and does not fake sticky bits.
                @(negedge clk); force dut.u_uart_mmio.req_valid=0; force dut.u_uart_mmio.req_ready=0;
                drop_index=byte_offset+16;
            end
            if(faults[frame_index]==1) begin
                rxd=0; #(TBIT*10.0); rxd=1; #(TBIT*2.0);
                check(injected_frame==1,"low stop did not generate frame error");
            end
            for(byte_no=0;byte_no<frame_lengths[frame_index];byte_no=byte_no+1) begin''')
s=s.replace('wait(decoded >= (frame_index+1)*60);', '''if(faults[frame_index]==2) begin
                repeat(10) @(negedge clk);
                check(injected_overflow==1 && dut.u_uart_mmio.fifo_count==16,"real FIFO did not overflow");
                release dut.u_uart_mmio.req_valid; release dut.u_uart_mmio.req_ready;
            end
            wait(decoded >= (frame_index+1)*60);''',1)
s=s.replace('check(dut.u_uart_mmio.fifo_empty,"FIFO not empty after fixed transaction");', '''check(dut.u_uart_mmio.fifo_empty,"FIFO not empty after fixed transaction");
            check(!dut.u_uart_mmio.frame_error_status && !dut.u_uart_mmio.overflow_status,"sticky errors not cleared after recovery");
            $fdisplay(timing_fd,"%0d,%0f",frame_index,($realtime-case_start)/1.0e9);
            $display("CHECK: timing case=%0d seconds=%0f TIME_SCALE=%0d",frame_index,($realtime-case_start)/1.0e9,TIME_SCALE);''')
s=s.replace('STAGE==4 ? 20 : STAGE==3 ? 16 : 13','STAGE==4 ? CASES-1 : STAGE==3 ? 16 : 13')
s=s.replace('STAGE==4 ? 125 : STAGE==3 ? 101 : 83','STAGE==4 ? CASES*6-1 : STAGE==3 ? 101 : 83')
s=s.replace('STAGE==4 ? 83 : 67','STAGE==4 ? CASES*4-1 : 67')
s=s.replace('$readmemh(crc_state_path,crc_state,0,146);', '''$readmemh(crc_state_path,crc_state,0,CASES*7-1);
            check($value$plusargs("FAULTS=%s",fault_path),"missing FAULTS");
            $readmemh(fault_path,faults,0,CASES-1);
            check($value$plusargs("TIMING=%s",timing_path),"missing TIMING");
            timing_fd=$fopen(timing_path,"w"); check(timing_fd!=0,"timing file");''')
s=s.replace('STAGE==4 ? 21 : STAGE==3 ? 17', 'STAGE==4 ? CASES : STAGE==3 ? 17')
s=s.replace('for(epoch=0;epoch<2;epoch=epoch+1) begin\n                boot_epoch();\n                for(case_index=', 'for(epoch=0;epoch<(STAGE==4 ? 1 : 2);epoch=epoch+1) begin\n                boot_epoch();\n                for(case_index=')
s=s.replace('STAGE==4 ? 16', 'STAGE==4 ? CASES')
s=s.replace('popped==sent && read_back==sent && cpu_lbu==sent,"fixed', 'popped==sent-dropped && read_back==sent-dropped && cpu_lbu==sent-dropped,"fixed')
s=s.replace('cpu_writes==(STAGE==4 ? 48 : 80) && cpu_reads==(STAGE==4 ? 192 : 80)', 'cpu_writes==(STAGE==4 ? 16 : 80) && cpu_reads==(STAGE==4 ? 16*(1+crc_state[(CASES-1)*7+1]) : 80)')
s=s.replace('check(!dut.u_uart_mmio.frame_error_status && !dut.u_uart_mmio.overflow_status,"UART sticky error");\n        check(!dut.u_uart_mmio.frame_error && !dut.u_uart_mmio.overflow,"UART event error");', '''if(STAGE!=4 || faults[case_index]==0) begin
            check(!dut.u_uart_mmio.frame_error_status && !dut.u_uart_mmio.overflow_status,"unexpected UART sticky error");
            check(!dut.u_uart_mmio.frame_error && !dut.u_uart_mmio.overflow,"unexpected UART event error");
        end
        if(dut.u_uart_mmio.frame_error) injected_frame=injected_frame+1;
        if(dut.u_uart_mmio.overflow) begin injected_overflow=injected_overflow+1; dropped=dropped+1; end
        if(dut.u_uart_mmio.req_valid && dut.u_uart_mmio.req_ready && dut.u_uart_mmio.req_write &&
           dut.u_uart_mmio.req_addr[3:0]==12 && dut.u_uart_mmio.req_wdata[1:0]==3 && injected_frame+injected_overflow>0)
            error_clears=error_clears+1;''')
s=s.replace('stimulus[cpu_lbu]', 'stimulus[lbu_index]')
s=s.replace('if(wb_pc==rx_pc || wb_pc==recover_rx_pc) begin', 'if(wb_pc==rx_pc || wb_pc==recover_rx_pc) begin\n                if(lbu_index==drop_index) lbu_index=lbu_index+1;')
s=s.replace('cpu_lbu=cpu_lbu+1;', 'cpu_lbu=cpu_lbu+1;lbu_index=lbu_index+1;')
s=s.replace('if(dut.u_uart_mmio.fifo_pop) begin', 'if(dut.u_uart_mmio.fifo_pop) begin\n            if(pop_index==drop_index) pop_index=pop_index+1;')
s=s.replace('stimulus[popped]', 'stimulus[pop_index]')
s=s.replace('popped=popped+1;', 'popped=popped+1;pop_index=pop_index+1;')
s=s.replace('$fclose(trace_fd);', '$fclose(trace_fd); if(STAGE==4) $fclose(timing_fd);')
s=s.replace('guards(); test_pass=1;', 'guards(); test_pass=1;\n        if(injected_frame+injected_overflow>0) check(error_clears>=2,"CPU did not clear each UART sticky error");')
s=s.replace('#2500000000.0;', '#20000000000.0;')
# A FIFO-overflow drop consumes wire input but has no LBU retirement.
s=s.replace('cpu_lbu>=frame_end', 'lbu_index>=frame_end')
# No change to production sources, timing, or successful ELF/DAT.
(HERE/'tb').mkdir(exist_ok=True)
(HERE/'tb/tb_uart_loader.v').write_text(s,encoding='utf8')
print('STAGE8_ISOLATED_COPY_PASS',len(entries),'files; unchanged ELF/DAT')

