"""Build Task027 TB from the proven user-port model plus explicit forced-stall controls."""
from pathlib import Path

HERE=Path(__file__).resolve().parent


def build_tb():
    old=(HERE/'tb_response_turnover_x32.sv').read_text(encoding='utf-8')
    text=old[:old.index('    task automatic transfer')]
    text=text.replace('module tb_response_turnover_x32;','module tb_write_buffer_x32 #(parameter integer POSTED=1);')
    # Replace old instances/mux as a single block; every new port net is declared first.
    a=text.index('    reg cpu_mode=0,cpu_allow=0;')
    b=text.index('    function automatic [31:0] word_at',a)
    text=text[:a]+(HERE/'write_buffer_connections.svh').read_text(encoding='utf-8')+'\n'+text[b:]
    text=text.replace('    reg backpressure=1, instant_read=0, instant_write=0;',
        '    reg backpressure=1, instant_read=0, instant_write=0;\n'
        '    reg block_aw=0,block_w=0,block_read=0,force_arready=0;\n    integer w_latency=4;')
    text=text.replace('assign rrdy=rv && !reading && (!backpressure || ar_wait>=3);',
        'assign rrdy=init_done && !block_read && (force_arready || (rv && !reading && (!backpressure || ar_wait>=3)));')
    text=text.replace('assign ardy=av &&','assign ardy=init_done && !block_aw && av &&')
    text=text.replace('assign wrdy=(instant_write', 'assign wrdy=init_done && !block_w && ((instant_write')
    text=text.replace('(writing && w_wait==0);','(writing && w_wait==0));')
    a=text.index('    always @(posedge clk) begin');model=text[a:]
    import re
    model=re.sub(r'\b(ir|dr|isv|dsv)\b',lambda m:{'ir':'bir','dr':'bdr','isv':'bisv','dsv':'bdsv'}[m[0]],model)
    model=model.replace('if (ar_blocked &&','if (ar_blocked && init_done &&')
    model=model.replace('if (aw_blocked &&','if (aw_blocked && init_done &&')
    model=model.replace('ar_blocked<=rv && !rrdy;aw_blocked<=av && !ardy;',
        'ar_blocked<=init_done && rv && !rrdy;aw_blocked<=init_done && av && !ardy;')
    model=model.replace('if (biv && bdv && bir)', 'if (biv && bdv && bir && bdr)')
    model=model.replace('if (reading && r_wait>0)','if (init_done && reading && r_wait>0)')
    model=model.replace('if (writing && w_wait>0)','if (init_done && writing && w_wait>0)')
    model=model.replace('w_wait<=4;', 'w_wait<=w_latency;')
    text=text[:a]+model
    return text+'\n`include "write_buffer_cases.svh"\nendmodule\n'


if __name__=='__main__':
    target=HERE/'tb_write_buffer_x32.sv';assert not target.exists()
    target.write_text(build_tb(),encoding='utf-8')
