"""One-time assertion-guarded RTL wiring; not a simulation runner."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
def edit(name,pairs):
 p=root/name; s=p.read_text(encoding='utf-8')
 for old,new in pairs:
  assert s.count(old)==1,(name,old,s.count(old))
  s=s.replace(old,new)
 p.write_text(s,encoding='utf-8')
ports='''    output wire pp_req_valid, pp_req_write,
    output wire [1:0] pp_req_size,
    output wire [31:0] pp_req_addr, pp_req_wdata,
    output wire [3:0] pp_req_wstrb,
    input wire pp_req_ready, pp_rsp_valid, pp_rsp_error,
    input wire [31:0] pp_rsp_rdata,
    input wire preprocess_busy, preprocess_done,
'''
conn='''        .pp_req_valid(pp_req_valid), .pp_req_write(pp_req_write),
        .pp_req_size(pp_req_size), .pp_req_addr(pp_req_addr),
        .pp_req_wdata(pp_req_wdata), .pp_req_wstrb(pp_req_wstrb),
        .pp_req_ready(pp_req_ready), .pp_rsp_valid(pp_rsp_valid),
        .pp_rsp_error(pp_rsp_error), .pp_rsp_rdata(pp_rsp_rdata),
        .preprocess_busy(preprocess_busy), .preprocess_done(preprocess_done),
'''
edit('myriscv/data_bus_interconnect.v',[
 ('    parameter integer ENABLE_CAMERA = 0,','    parameter integer ENABLE_PREPROCESS = 0,\n    parameter integer ENABLE_CAMERA = 0,'),
 ('    output wire cam_req_valid,',ports+'    output wire cam_req_valid,'),
 ("    localparam [2:0] TARGET_CAMERA = 3'd5;","    localparam [2:0] TARGET_PREPROCESS = 3'd6;\n    localparam [2:0] TARGET_CAMERA = 3'd5;"),
 ('    wire frame_window=', '''    wire pp_select=(ENABLE_PREPROCESS!=0) && !ram_select && !mmio_select && !uart_select && !cam_select &&
                   (m_req_addr[31:6]==(32'h10003000 >> 6));
    wire pp_blocked=(ENABLE_PREPROCESS!=0) && (m_req_addr[31:16]==16'h4200) &&
                    (m_req_write || preprocess_busy || !preprocess_done);
    wire frame_window='''),
 ('!cam_select && !frame_blocked &&','!cam_select && !pp_select && !frame_blocked && !pp_blocked &&'),
 ('                          cam_select  ? cam_req_ready  :','                          pp_select   ? pp_req_ready   :\n                          cam_select  ? cam_req_ready  :'),
 ('    assign cam_req_valid=', '''    assign pp_req_valid=issue_allowed && m_req_valid && pp_select;
    assign pp_req_write=m_req_write;
    assign pp_req_size=m_req_size;
    assign pp_req_addr=m_req_addr-32'h10003000;
    assign pp_req_wdata=m_req_wdata;
    assign pp_req_wstrb=m_req_wstrb;
    assign cam_req_valid='''),
 ('                          (response_target == TARGET_CAMERA) ? cam_rsp_valid :','                          (response_target == TARGET_PREPROCESS) ? pp_rsp_valid :\n                          (response_target == TARGET_CAMERA) ? cam_rsp_valid :'),
 ('                         (response_target == TARGET_CAMERA) ? cam_rsp_rdata :','                         (response_target == TARGET_PREPROCESS) ? pp_rsp_rdata :\n                         (response_target == TARGET_CAMERA) ? cam_rsp_rdata :'),
 ('                          (response_target == TARGET_CAMERA) ? cam_rsp_error :','                          (response_target == TARGET_PREPROCESS) ? pp_rsp_error :\n                          (response_target == TARGET_CAMERA) ? cam_rsp_error :'),
 ('                else if (cam_select)','                else if (pp_select)\n                    response_target <= TARGET_PREPROCESS;\n                else if (cam_select)')])
edit('myriscv/inst_bus_interconnect.v',[
 ('    parameter integer ENABLE_CAMERA = 0,','    parameter integer ENABLE_PREPROCESS = 0,\n    parameter integer ENABLE_CAMERA = 0,'),
 ('    assign ddr_select = (ENABLE_DDR != 0) && !rom_select &&',"    assign ddr_select = (ENABLE_DDR != 0) && !rom_select &&\n                        !((ENABLE_PREPROCESS!=0) && m_req_addr[31:16]==16'h4200) &&")])
edit('myriscv/dual_sram_to_pango_ddr_bridge.v',[
 ('    parameter integer CAMERA_UNCACHED_ENABLE = 0,','    parameter integer CAMERA_UNCACHED_ENABLE = 0,\n    parameter integer PREPROCESS_UNCACHED_ENABLE = 0,'),
 ('    wire camera_data_addr=', '''    wire preprocess_data_addr=(PREPROCESS_UNCACHED_ENABLE!=0) && data_req_addr[31:16]==16'h0200;
    wire preprocess_fill_addr=(PREPROCESS_UNCACHED_ENABLE!=0) &&
                              (request_line_tag >> (16-BEAT_ADDR_BITS))==16'h0200;
    wire camera_data_addr='''),
 ('(DATA_LINE_BUFFER_ENABLE != 0) && !camera_data_addr &&','(DATA_LINE_BUFFER_ENABLE != 0) && !camera_data_addr && !preprocess_data_addr &&'),
 ('take_data && data_req_write && !camera_data_addr &&','take_data && data_req_write && !camera_data_addr && !preprocess_data_addr &&'),
 ('(DATA_LINE_BUFFER_ENABLE != 0) && !camera_fill_addr &&','(DATA_LINE_BUFFER_ENABLE != 0) && !camera_fill_addr && !preprocess_fill_addr &&')])
edit('myriscv/soc_top.v',[
 ('    parameter integer ENABLE_CAMERA = 0,','    parameter integer ENABLE_PREPROCESS = 0,\n    parameter integer ENABLE_CAMERA = 0,'),
 ('    output wire cam_req_valid,',ports+'    output wire cam_req_valid,'),
 ('    inst_bus_interconnect #(\n','    inst_bus_interconnect #(\n        .ENABLE_PREPROCESS(ENABLE_PREPROCESS),\n'),
 ('    data_bus_interconnect #(\n','    data_bus_interconnect #(\n        .ENABLE_PREPROCESS(ENABLE_PREPROCESS),\n'),
 ('    ) u_data_bus_interconnect (\n','    ) u_data_bus_interconnect (\n'+conn),
 ('                .CAMERA_UNCACHED_ENABLE(ENABLE_CAMERA),','                .PREPROCESS_UNCACHED_ENABLE(ENABLE_PREPROCESS),\n                .CAMERA_UNCACHED_ENABLE(ENABLE_CAMERA),')])
edit('myriscv/board_top.v', [('        .ENABLE_CAMERA(1),','        .ENABLE_CAMERA(1), .ENABLE_PREPROCESS(1),')])

p=root/'myriscv/soc_ddr3_top.v'; s=p.read_text(encoding='utf-8')
s=s.replace('    parameter integer ENABLE_CAMERA = 0,','    parameter integer ENABLE_PREPROCESS = 0,\n    parameter integer ENABLE_CAMERA = 0,',1)
decl='''    localparam PREPROCESS_ACTIVE=(ENABLE_PREPROCESS!=0 && ENABLE_CAMERA!=0);
    wire pp_req_valid, pp_req_write, pp_req_ready, pp_rsp_valid, pp_rsp_error;
    wire [1:0] pp_req_size;
    wire [3:0] pp_req_wstrb;
    wire [31:0] pp_req_addr, pp_req_wdata, pp_rsp_rdata;
    wire preprocess_busy, preprocess_done, pp_read_error;
    wire [1:0] pp_source_hold;
    wire [31:0] cam_source_seq0, cam_source_seq1;
    wire cam_source_geometry_ok;
    wire [27:0] shared_awaddr, pp_awaddr, pp_araddr, cpu_araddr;
    wire [3:0] shared_awlen, shared_awuser_id, cpu_arlen, cpu_arid;
    wire shared_awuser_ap, shared_awvalid, shared_awready, shared_wready;
    wire pp_awvalid, pp_awready, pp_wready, pp_arvalid, pp_arready, pp_rvalid;
    wire cpu_arvalid, cpu_arready, cpu_rvalid, cpu_arap;
    wire [255:0] shared_wdata, pp_wdata;
    wire [31:0] shared_wstrb;
'''
s=s.replace('    wire cam_req_valid,',decl+'    wire cam_req_valid,',1)
s=s.replace('camera_mmio #(.CLK_HZ(CORE_CLK_HZ))','camera_mmio #(.CLK_HZ(CORE_CLK_HZ), .EXTERNAL_HOLD_ENABLE(PREPROCESS_ACTIVE))',1)
s=s.replace('            .dual_mode(camera_dual_mode), .cpu_owned(camera_cpu_owned),','''            .dual_mode(camera_dual_mode), .cpu_owned(camera_cpu_owned),
            .external_hold(pp_source_hold), .source_seq0(cam_source_seq0), .source_seq1(cam_source_seq1),
            .source_geometry_ok(cam_source_geometry_ok),''',1)
# Existing CPU/camera arbiter feeds an outer complete-transaction arbiter.
a=s.index('        camera_ddr_write_arbiter u_write_arbiter ('); b=s.index('    end endgenerate',a)
part=s[a:b]
for n in ['awaddr','awlen','awuser_id','awuser_ap','awvalid','awready','wdata','wstrb','wready']:
 part=part.replace('axi_'+n,'shared_'+n)
s=s[:a]+part+s[b:]
s=s.replace('        assign camera_busy=0;','        assign camera_busy=0;\n        assign cam_source_seq0=0; assign cam_source_seq1=0; assign cam_source_geometry_ok=0;',1)
block='''
    generate if (PREPROCESS_ACTIVE) begin : g_preprocess
        preprocess_mmio #(.CLK_HZ(CORE_CLK_HZ)) u_preprocess (
            .clk(core_clk), .resetn(soc_resetn),
            .req_valid(pp_req_valid), .req_write(pp_req_write), .req_size(pp_req_size),
            .req_addr(pp_req_addr), .req_wdata(pp_req_wdata), .req_wstrb(pp_req_wstrb),
            .req_ready(pp_req_ready), .rsp_valid(pp_rsp_valid), .rsp_error(pp_rsp_error), .rsp_rdata(pp_rsp_rdata),
            .camera_dual_mode(camera_dual_mode), .cpu_owned(camera_cpu_owned),
            .source_geometry_ok(cam_source_geometry_ok), .source_seq0(cam_source_seq0), .source_seq1(cam_source_seq1),
            .busy(preprocess_busy), .done(preprocess_done), .source_hold(pp_source_hold),
            .araddr(pp_araddr), .arvalid(pp_arvalid), .arready(pp_arready),
            .rvalid(pp_rvalid), .rdata(axi_rdata), .rid(axi_rid), .rlast(axi_rlast),
            .awaddr(pp_awaddr), .awvalid(pp_awvalid), .awready(pp_awready), .wdata(pp_wdata), .wready(pp_wready),
            .read_protocol_error(pp_read_error)
        );
        camera_ddr_write_arbiter #(.CAM_AW_ID(4'd3)) u_output_arbiter (
            .clk(core_clk), .resetn(soc_resetn),
            .cpu_awaddr(shared_awaddr), .cpu_awlen(shared_awlen), .cpu_awid(shared_awuser_id),
            .cpu_awap(shared_awuser_ap), .cpu_awvalid(shared_awvalid),
            .cpu_wdata(shared_wdata), .cpu_wstrb(shared_wstrb), .cpu_awready(shared_awready), .cpu_wready(shared_wready),
            .cam_awaddr(pp_awaddr), .cam_awvalid(pp_awvalid), .cam_wdata(pp_wdata),
            .cam_awready(pp_awready), .cam_wready(pp_wready),
            .awaddr(axi_awaddr), .awlen(axi_awlen), .awid(axi_awuser_id), .awap(axi_awuser_ap),
            .awvalid(axi_awvalid), .awready(axi_awready), .wdata(axi_wdata), .wstrb(axi_wstrb), .wready(axi_wready), .busy()
        );
        preprocess_ddr_read_arbiter u_read_arbiter (
            .clk(core_clk), .resetn(soc_resetn),
            .cpu_addr(cpu_araddr), .cpu_len(cpu_arlen), .cpu_id(cpu_arid), .cpu_ap(cpu_arap), .cpu_valid(cpu_arvalid),
            .cpu_ready(cpu_arready), .cpu_rvalid(cpu_rvalid),
            .pp_addr(pp_araddr), .pp_valid(pp_arvalid), .pp_ready(pp_arready), .pp_rvalid(pp_rvalid),
            .araddr(axi_araddr), .arlen(axi_arlen), .arid(axi_aruser_id), .arap(axi_aruser_ap),
            .arvalid(axi_arvalid), .arready(axi_arready), .rvalid(axi_rvalid), .rlast(axi_rlast), .rid(axi_rid),
            .protocol_error(pp_read_error)
        );
    end else begin : g_no_preprocess
        assign pp_req_ready=0; assign pp_rsp_valid=0; assign pp_rsp_error=0; assign pp_rsp_rdata=0;
        assign preprocess_busy=0; assign preprocess_done=0; assign pp_source_hold=0; assign pp_read_error=0;
        assign pp_awaddr=0; assign pp_awvalid=0; assign pp_wdata=0; assign pp_awready=0; assign pp_wready=0;
        assign pp_araddr=0; assign pp_arvalid=0; assign pp_arready=0; assign pp_rvalid=0;
        assign axi_awaddr=shared_awaddr; assign axi_awlen=shared_awlen; assign axi_awuser_id=shared_awuser_id;
        assign axi_awuser_ap=shared_awuser_ap; assign axi_awvalid=shared_awvalid;
        assign axi_wdata=shared_wdata; assign axi_wstrb=shared_wstrb;
        assign shared_awready=axi_awready; assign shared_wready=axi_wready;
        assign axi_araddr=cpu_araddr; assign axi_arlen=cpu_arlen; assign axi_aruser_id=cpu_arid;
        assign axi_aruser_ap=cpu_arap; assign axi_arvalid=cpu_arvalid;
        assign cpu_arready=axi_arready; assign cpu_rvalid=axi_rvalid;
    end endgenerate
'''
s=s.replace('    // CPU 与桥均运行于 DDR IP',block+'\n    // CPU 与桥均运行于 DDR IP',1)
s=s.replace('    soc_top #(\n','    soc_top #(\n        .ENABLE_PREPROCESS(PREPROCESS_ACTIVE),\n',1)
s=s.replace('    ) u_soc (\n','    ) u_soc (\n'+conn,1)
for old,new in [('araddr','araddr'),('arlen','arlen'),('aruser_id','arid'),('aruser_ap','arap'),('arvalid','arvalid'),('arready','arready'),('rvalid','rvalid')]:
 needle=f'.ddr_axi_{old}(axi_{old})'; assert s.count(needle)==1,needle
 s=s.replace(needle,f'.ddr_axi_{old}(cpu_{new})')
p.write_text(s,encoding='utf-8')
p=root/'RISCV.pds'; s=p.read_text(encoding='utf-8'); key='                (_file "myriscv/alu.v"'; assert s.count(key)==2
entries=''.join(f'                (_file "myriscv/{n}.v"\n                    (_format verilog)\n                )\n' for n in ['preprocess_mmio','preprocess_ddr_read_arbiter'])
p.write_text(s.replace(key,entries+key),encoding='utf-8')
print('Preprocessor wired; existing IP and constraints unchanged.')
