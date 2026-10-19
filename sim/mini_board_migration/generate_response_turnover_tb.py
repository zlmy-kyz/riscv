"""Reuse the successful DDR model/transfer unchanged behind a manual/CPU mux."""
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent


def build_tb():
    old=(HERE/'tb_data_write_hit_x32.sv').read_text(encoding='utf-8')
    text=old[:old.index('    // Independent metadata oracle')]
    text=text.replace('module tb_data_write_hit_x32;', 'module tb_response_turnover_x32;')
    # Only the model observes physical muxed requests. Manual tasks still drive iv/dv.
    aliases={'iv':'biv','ia':'bia','dv':'bdv','dw':'bdw','da':'bda','wd':'bwd','ws':'bws','ds':'bds'}
    start=text.index('    always @(posedge clk) begin')
    end=text.index('    task automatic transfer',start)
    model=text[start:end]
    model=re.sub(r'\b(iv|ia|dv|dw|da|wd|ws|ds)\b',lambda m:aliases[m[0]],model)
    text=text[:start]+model+text[end:]
    for port,old_signal in [('inst_req_valid','iv'),('inst_req_addr','ia'),('data_req_valid','dv'),
        ('data_req_write','dw'),('data_req_size','ds'),('data_req_addr','da'),
        ('data_req_wdata','wd'),('data_req_wstrb','ws')]:
        needle=f'.{port}({old_signal})';assert text.count(needle)==1
        text=text.replace(needle,f'.{port}({aliases[old_signal]})')
    declarations=(HERE/'response_turnover_cpu_mux.svh').read_text(encoding='utf-8')
    # Declare mux nets before DUT port connections; otherwise vlog creates implicit nets.
    anchor='    dual_sram_to_pango_ddr_bridge #'
    assert text.count(anchor)==1
    text=text.replace(anchor,declarations+'\n'+anchor,1)
    for name in aliases.values():
        decl=re.search(r'\bwire\s+(?:\[[^\]]+\]\s+)?'+name+r'\s*=',text)
        assert decl and decl.start()<text.index('('+name+')'),name
    return text+'\n`include "response_turnover_cases.svh"\nendmodule\n'


if __name__=='__main__':
    out=HERE/'tb_response_turnover_x32.sv'
    assert not out.exists(),'Preserve generated TB'
    out.write_text(build_tb(),encoding='utf-8')
