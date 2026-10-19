"""One-time guarded wiring edit; do not rerun on an integrated tree."""
from pathlib import Path
from datetime import datetime

def replace(s,a,b,count=1):
    assert s.count(a)==count,(a,s.count(a))
    return s.replace(a,b)

ports='''    output wire cnn_req_valid, cnn_req_write,
    output wire [1:0] cnn_req_size,
    output wire [31:0] cnn_req_addr, cnn_req_wdata,
    output wire [3:0] cnn_req_wstrb,
    input wire cnn_req_ready, cnn_rsp_valid, cnn_rsp_error,
    input wire [31:0] cnn_rsp_rdata,
'''
connections='''        .cnn_req_valid(cnn_req_valid), .cnn_req_write(cnn_req_write),
        .cnn_req_size(cnn_req_size), .cnn_req_addr(cnn_req_addr),
        .cnn_req_wdata(cnn_req_wdata), .cnn_req_wstrb(cnn_req_wstrb),
        .cnn_req_ready(cnn_req_ready), .cnn_rsp_valid(cnn_rsp_valid),
        .cnn_rsp_error(cnn_rsp_error), .cnn_rsp_rdata(cnn_rsp_rdata),
'''
p=Path('myriscv/data_bus_interconnect.v');s=p.read_text(encoding='utf-8')
s=replace(s,'    parameter integer ENABLE_PREPROCESS = 0,','    parameter integer ENABLE_CNN = 0,\n    parameter integer ENABLE_PREPROCESS = 0,')
s=replace(s,'    output wire pp_req_valid, pp_req_write,',ports+'    output wire pp_req_valid, pp_req_write,')
s=replace(s,'    localparam [2:0] TARGET_PREPROCESS',"    localparam [2:0] TARGET_CNN = 3'd7;\n    localparam [2:0] TARGET_PREPROCESS")
s=replace(s,'    wire pp_blocked=', '''    wire cnn_select=(ENABLE_CNN!=0) && !ram_select && !mmio_select && !uart_select && !cam_select && !pp_select &&
                    (m_req_addr[31:8]==24'h100040);
    wire pp_blocked=''')
s=replace(s,'!pp_select && !frame_blocked','!pp_select && !cnn_select && !frame_blocked')
s=replace(s,'                          pp_select   ? pp_req_ready', '                          cnn_select  ? cnn_req_ready  :\n                          pp_select   ? pp_req_ready')
s=replace(s,'    assign pp_req_valid=', '''    assign cnn_req_valid=issue_allowed && m_req_valid && cnn_select;
    assign cnn_req_write=m_req_write;
    assign cnn_req_size=m_req_size;
    assign cnn_req_addr=m_req_addr-32'h10004000;
    assign cnn_req_wdata=m_req_wdata;
    assign cnn_req_wstrb=m_req_wstrb;
    assign pp_req_valid=''')
for f in ['valid','rdata','error']:
    anchor=f'                          (response_target == TARGET_PREPROCESS) ? pp_rsp_{f} :' if f!='rdata' else '                         (response_target == TARGET_PREPROCESS) ? pp_rsp_rdata :'
    s=replace(s,anchor,anchor.replace('TARGET_PREPROCESS','TARGET_CNN').replace('pp_rsp_','cnn_rsp_')+'\n'+anchor)
s=replace(s,'                else if (pp_select)','                else if (cnn_select)\n                    response_target <= TARGET_CNN;\n                else if (pp_select)')
p.write_text(s,encoding='utf-8')
p=Path('myriscv/soc_top.v');s=p.read_text(encoding='utf-8')
s=replace(s,'    parameter integer ENABLE_PREPROCESS = 0,','    parameter integer ENABLE_CNN = 0,\n    parameter integer ENABLE_PREPROCESS = 0,')
s=replace(s,'    output wire pp_req_valid, pp_req_write,',ports+'    output wire pp_req_valid, pp_req_write,')
s=replace(s,'    data_bus_interconnect #(\n','    data_bus_interconnect #(\n        .ENABLE_CNN(ENABLE_CNN),\n')
s=replace(s,'    ) u_data_bus_interconnect (\n','    ) u_data_bus_interconnect (\n'+connections)
p.write_text(s,encoding='utf-8')
p=Path('myriscv/soc_ddr3_top.v');s=p.read_text(encoding='utf-8')
s=replace(s,'    parameter integer ENABLE_PREPROCESS = 0,','    parameter integer ENABLE_CNN = 0,\n    parameter integer ENABLE_PREPROCESS = 0,')
s=replace(s,'    wire pp_req_valid,', '''    localparam CNN_ACTIVE=(ENABLE_CNN!=0 && PREPROCESS_ACTIVE);
    wire cnn_req_valid, cnn_req_write, cnn_req_ready, cnn_rsp_valid, cnn_rsp_error;
    wire [1:0] cnn_req_size;
    wire [31:0] cnn_req_addr, cnn_req_wdata, cnn_rsp_rdata;
    wire [3:0] cnn_req_wstrb;
    wire cnn_hold, cnn_arvalid, cnn_arready, cnn_rvalid, inner_read_error, outer_read_error;
    wire [27:0] cnn_araddr, group_araddr;
    wire [3:0] group_arlen, group_arid;
    wire group_arap, group_arvalid, group_arready, group_rvalid;
    wire [31:0] pp_result_seq;
    wire pp_result_buf;
    wire pp_req_valid,''')
s=replace(s,'preprocess_mmio #(.CLK_HZ(CORE_CLK_HZ))','preprocess_mmio #(.CLK_HZ(CORE_CLK_HZ), .OUTPUT_HOLD_ENABLE(CNN_ACTIVE))')
s=replace(s,'u_preprocess (\n','u_preprocess (\n            .output_hold(cnn_hold), .result_seq(pp_result_seq), .result_buf(pp_result_buf),\n')
old='''.araddr(axi_araddr), .arlen(axi_arlen), .arid(axi_aruser_id), .arap(axi_aruser_ap),
            .arvalid(axi_arvalid), .arready(axi_arready), .rvalid(axi_rvalid), .rlast(axi_rlast), .rid(axi_rid),
            .protocol_error(pp_read_error)'''
new='''.araddr(group_araddr), .arlen(group_arlen), .arid(group_arid), .arap(group_arap),
            .arvalid(group_arvalid), .arready(group_arready), .rvalid(group_rvalid), .rlast(axi_rlast), .rid(axi_rid),
            .protocol_error(inner_read_error)'''
s=replace(s,old,new)
s=replace(s,'assign pp_source_hold=0; assign pp_read_error=0;', 'assign pp_source_hold=0; assign inner_read_error=0;\n        assign pp_result_seq=0; assign pp_result_buf=0;')
s=replace(s,'''        assign axi_araddr=cpu_araddr; assign axi_arlen=cpu_arlen; assign axi_aruser_id=cpu_arid;
        assign axi_aruser_ap=cpu_arap; assign axi_arvalid=cpu_arvalid;
        assign cpu_arready=axi_arready; assign cpu_rvalid=axi_rvalid;''','''        assign group_araddr=cpu_araddr; assign group_arlen=cpu_arlen; assign group_arid=cpu_arid;
        assign group_arap=cpu_arap; assign group_arvalid=cpu_arvalid;
        assign cpu_arready=group_arready; assign cpu_rvalid=group_rvalid;''')
s=replace(s,'    // CPU 与桥均运行于', '''    assign pp_read_error=inner_read_error | outer_read_error;
    generate if(CNN_ACTIVE) begin : g_cnn
        cnn_mmio #(.CLK_HZ(CORE_CLK_HZ)) u_cnn (
            .clk(core_clk), .resetn(soc_resetn),
            .req_valid(cnn_req_valid), .req_write(cnn_req_write), .req_size(cnn_req_size),
            .req_addr(cnn_req_addr), .req_wdata(cnn_req_wdata), .req_wstrb(cnn_req_wstrb),
            .req_ready(cnn_req_ready), .rsp_valid(cnn_rsp_valid), .rsp_error(cnn_rsp_error), .rsp_rdata(cnn_rsp_rdata),
            .pp_done(preprocess_done), .pp_busy(preprocess_busy), .pp_result_buf(pp_result_buf),
            .pp_result_seq(pp_result_seq), .pp_hold(cnn_hold),
            .araddr(cnn_araddr), .arvalid(cnn_arvalid), .arready(cnn_arready), .rvalid(cnn_rvalid),
            .rdata(axi_rdata), .rid(axi_rid), .rlast(axi_rlast), .protocol_error(pp_read_error)
        );
        preprocess_ddr_read_arbiter #(.PP_ID(4'd4)) u_cnn_read_arbiter (
            .clk(core_clk), .resetn(soc_resetn),
            .cpu_addr(group_araddr), .cpu_len(group_arlen), .cpu_id(group_arid), .cpu_ap(group_arap),
            .cpu_valid(group_arvalid), .cpu_ready(group_arready), .cpu_rvalid(group_rvalid),
            .pp_addr(cnn_araddr), .pp_valid(cnn_arvalid), .pp_ready(cnn_arready), .pp_rvalid(cnn_rvalid),
            .araddr(axi_araddr), .arlen(axi_arlen), .arid(axi_aruser_id), .arap(axi_aruser_ap),
            .arvalid(axi_arvalid), .arready(axi_arready), .rvalid(axi_rvalid), .rlast(axi_rlast), .rid(axi_rid),
            .protocol_error(outer_read_error)
        );
    end else begin : g_no_cnn
        assign cnn_req_ready=0; assign cnn_rsp_valid=0; assign cnn_rsp_error=0; assign cnn_rsp_rdata=0;
        assign cnn_hold=0; assign cnn_araddr=0; assign cnn_arvalid=0; assign cnn_arready=0; assign cnn_rvalid=0;
        assign outer_read_error=0;
        assign axi_araddr=group_araddr; assign axi_arlen=group_arlen; assign axi_aruser_id=group_arid;
        assign axi_aruser_ap=group_arap; assign axi_arvalid=group_arvalid;
        assign group_arready=axi_arready; assign group_rvalid=axi_rvalid;
    end endgenerate

    // CPU 与桥均运行于''')
s=replace(s,'    soc_top #(\n','    soc_top #(\n        .ENABLE_CNN(CNN_ACTIVE),\n')
s=replace(s,'    ) u_soc (\n','    ) u_soc (\n'+connections)
p.write_text(s,encoding='utf-8')
p=Path('myriscv/board_top.v');s=p.read_text(encoding='utf-8')
s=replace(s,'.ENABLE_CAMERA(1), .ENABLE_PREPROCESS(1),','.ENABLE_CAMERA(1), .ENABLE_PREPROCESS(1), .ENABLE_CNN(1),')
p.write_text(s,encoding='utf-8')
p=Path('RISCV.pds');s=p.read_text(encoding='utf-8')
anchor='                (_file "myriscv/preprocess_mmio.v"'
items=''
for name in ['cnn_rgb96_gray32','cnn_int8_mac','cnn_requantize','cnn_gap16','cnn_digits_engine','cnn_mmio']:
    assert f'myriscv/{name}.v' not in s
    stamp=datetime.fromtimestamp(Path(f'myriscv/{name}.v').stat().st_mtime).strftime('%Y-%m-%dT%H:%M:%S')
    items+=f'                (_file "myriscv/{name}.v"\n                    (_format verilog)\n                    (_timespec "{stamp}")\n                )\n'
s=replace(s,anchor,items+anchor)
p.write_text(s,encoding='utf-8')
print('Integrated CNN bus, source hold, nested read arbitration and PDS sources.')
