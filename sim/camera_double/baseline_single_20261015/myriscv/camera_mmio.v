`timescale 1ns/1ps
// Single-frame owner. The frame aperture is fixed and never cached by CPU.
// PCLK-domain FIFO/result state is reset between arms, never during a live DDR W.
module camera_mmio #(
    parameter integer CLK_HZ=93750000,
    parameter integer WIDTH=1280, HEIGHT=720, DROP_FRAMES=10,
    parameter [31:0] FRAME_BASE=32'h41000000,
    parameter [27:0] FRAME_NATIVE_ADDR=28'h0400000
) (
    input wire clk, resetn,
    input wire req_valid, req_write,
    input wire [1:0] req_size,
    input wire [31:0] req_addr, req_wdata,
    input wire [3:0] req_wstrb,
    output reg busy,
    output wire req_ready,
    output reg rsp_valid, rsp_error,
    output reg [31:0] rsp_rdata,
    input wire pclk, vsync, href,
    input wire [7:0] din,
    input wire scl_in, sda_in,
    output wire scl_low, sda_low, sensor_resetn,
    output wire dma_awvalid,
    output wire [27:0] dma_awaddr,
    output reg [255:0] dma_wdata,
    input wire dma_awready, dma_wready
);
    localparam integer PIXELS=WIDTH*HEIGHT, BYTES=PIXELS*2, BEATS=BYTES/32;
    localparam integer VALID_GEOMETRY=(WIDTH>0 && WIDTH<=4095 && HEIGHT>0 && HEIGHT<=2047 &&
                                     BYTES<=2097152 && (BYTES%32)==0);
    localparam D_IDLE=0, D_FETCH=1, D_LATCH=2, D_AW=3, D_W=4;
    wire config_done, config_error;
    wire [15:0] sensor_id;
    wire [7:0] config_index;
    wire [7:0] config_error_code;
    ov5640_config #(.CLK_HZ(CLK_HZ)) u_config (
        .clk(clk), .resetn(resetn), .scl_in(scl_in), .sda_in(sda_in),
        .scl_low(scl_low), .sda_low(sda_low), .sensor_resetn(sensor_resetn),
        .config_done(config_done), .config_error(config_error),
        .config_error_code(config_error_code),
        .sensor_id(sensor_id), .config_index(config_index)
    );
    reg frame_done, error_latched, overflow_latched, aborting, run;
    reg [7:0] error_code;
    reg [31:0] frame_seq, frame_bytes, pixel_count, written_beats, timer;
    reg [31:0] frame_crc32;
    reg [3:0] prepare_count;
    reg [2:0] dma_state;
    // Assertion is immediate. Each receiving clock must run for release.
    wire capture_resetn=resetn && busy;
    (* async_reg="true", syn_preserve=1 *) reg [1:0] wr_reset_pipe, rd_reset_pipe;
    always @(posedge pclk or negedge capture_resetn)
        if (!capture_resetn) wr_reset_pipe<=0;
        else wr_reset_pipe<={wr_reset_pipe[0],1'b1};
    always @(posedge clk or negedge capture_resetn)
        if (!capture_resetn) rd_reset_pipe<=0;
        else rd_reset_pipe<={rd_reset_pipe[0],1'b1};
    wire p_done, p_overflow, p_format;
    // Bundled result held in PCLK until busy is cleared by this domain, only
    // sampled after the synchronized terminal level and all DDR writes drain.
    wire [31:0] p_crc32;
    (* async_reg="true" *) reg [1:0] ready_sync, done_sync, overflow_sync, format_sync;
    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin ready_sync<=0; done_sync<=0; overflow_sync<=0; format_sync<=0; end
        else begin
            ready_sync<={ready_sync[0],wr_reset_pipe[1]};
            done_sync<={done_sync[0],p_done};
            overflow_sync<={overflow_sync[0],p_overflow};
            format_sync<={format_sync[0],p_format};
        end
    end
    wire fifo_full, fifo_empty, fifo_write;
    wire [15:0] fifo_wdata;
    wire [255:0] fifo_rdata;
    wire [12:0] fifo_wr_count;
    wire [8:0] fifo_rd_count;
    wire fifo_read=dma_state==D_FETCH && !fifo_empty && rd_reset_pipe[1];
    ov5640_capture #(.WIDTH(WIDTH), .HEIGHT(HEIGHT), .DROP_FRAMES(DROP_FRAMES)) u_capture (
        .pclk(pclk), .resetn(wr_reset_pipe[1]), .run(run),
        .vsync(vsync), .href(href), .din(din), .fifo_full(fifo_full),
        .fifo_write(fifo_write), .fifo_data(fifo_wdata),
        .done(p_done), .overflow(p_overflow), .format_error(p_format), .frame_crc32(p_crc32)
    );
    afifo_16i_64o_512 u_fifo (
        .wr_clk(pclk), .wr_rst(!wr_reset_pipe[1]), .wr_en(fifo_write), .wr_data(fifo_wdata),
        .wr_full(fifo_full), .wr_water_level(fifo_wr_count), .almost_full(),
        .rd_clk(clk), .rd_rst(!rd_reset_pipe[1]), .rd_en(fifo_read), .rd_data(fifo_rdata),
        .rd_empty(fifo_empty), .rd_water_level(fifo_rd_count), .almost_empty()
    );
    assign dma_awvalid=resetn && dma_state==D_AW;
    assign dma_awaddr=FRAME_NATIVE_ADDR + (written_beats << 3);
    wire dma_complete=dma_wready && ((dma_state==D_W) ||
                      (dma_state==D_AW && dma_awready));
    assign req_ready=resetn && !rsp_valid;
    wire accept=req_valid && req_ready;
    wire ctrl_write=accept && req_write && req_addr==4 && req_size==2 && req_wstrb==15;
    wire arm_cmd=ctrl_write && req_wdata==1 && !busy && config_done && !config_error && VALID_GEOMETRY;
    wire abort_cmd=ctrl_write && req_wdata==2;
    wire clear_cmd=ctrl_write && req_wdata==4 && !busy;
    wire capture_fault=run && (overflow_sync[1] || format_sync[1]);
    wire timed_out=busy && timer>=CLK_HZ*3;
    wire stop_now=aborting || abort_cmd || capture_fault || timed_out;
    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            rsp_valid<=0; rsp_error<=0; rsp_rdata<=0;
            busy<=0; frame_done<=0; error_latched<=0; overflow_latched<=0;
            aborting<=0; run<=0; error_code<=0; frame_seq<=0; frame_bytes<=0;
            pixel_count<=0; written_beats<=0; timer<=0; prepare_count<=0;
            dma_state<=D_IDLE; dma_wdata<=0; frame_crc32<=0;
        end else begin
            rsp_valid<=0;
            if (accept) begin
                rsp_valid<=1; rsp_error<=0; rsp_rdata<=0;
                if (req_size!=2 || req_addr[1:0]!=0 || req_addr>40) rsp_error<=1;
                else if (req_write) begin
                    if (!(arm_cmd || abort_cmd || clear_cmd)) rsp_error<=1;
                end else case (req_addr[5:2])
                    0: rsp_rdata<=32'h43414d01;
                    1: rsp_rdata<=0;
                    2: rsp_rdata<={27'b0,(error_latched|config_error|!VALID_GEOMETRY),overflow_latched,frame_done,busy,config_done};
                    3: rsp_rdata<=FRAME_BASE;
                    4: rsp_rdata<=frame_bytes;
                    5: rsp_rdata<=frame_seq;
                    6: rsp_rdata<=pixel_count;
                    7: rsp_rdata<=!VALID_GEOMETRY ? 32'd8 : config_error ?
                                  {16'b0,config_index,config_error_code} : {24'b0,error_code};
                    8: rsp_rdata<={16'b0,sensor_id};
                    9: rsp_rdata<=written_beats;
                    10: rsp_rdata<=frame_crc32;
                    default: rsp_error<=1;
                endcase
            end
            if (clear_cmd) begin
                frame_crc32<=0;
                frame_done<=0; frame_bytes<=0; pixel_count<=0;
                error_latched<=0; overflow_latched<=0; error_code<=0;
            end
            if (arm_cmd) begin
                frame_crc32<=0;
                busy<=1; frame_done<=0; frame_bytes<=0; pixel_count<=0;
                error_latched<=0; overflow_latched<=0; error_code<=0;
                aborting<=0; run<=0; prepare_count<=0; timer<=0; written_beats<=0;
            end else if (busy) begin
                if (!timed_out) timer<=timer+1;
                if (!run && !stop_now) begin
                    if (prepare_count<15) prepare_count<=prepare_count+1'b1;
                    if (prepare_count==15 && ready_sync[1] && rd_reset_pipe[1] &&
                        !done_sync[1] && !overflow_sync[1] && !format_sync[1]) run<=1;
                end
                if (stop_now) begin
                    frame_crc32<=0;
                    aborting<=1; run<=0; frame_done<=0; frame_bytes<=0; pixel_count<=0;
                    error_latched<=1;
                    if (!aborting) begin
                        overflow_latched<=overflow_sync[1];
                        error_code<=abort_cmd ? 8'd5 : overflow_sync[1] ? 8'd2 :
                                    format_sync[1] ? 8'd3 : 8'd4;
                    end
                    // D_FETCH/D_LATCH have not exposed an AW. Those can be discarded.
                    if (dma_state==D_IDLE || dma_state==D_FETCH || dma_state==D_LATCH) begin
                        busy<=0; dma_state<=D_IDLE;
                    end
                end else if (run && done_sync[1] && written_beats==BEATS && dma_state==D_IDLE) begin
                    busy<=0; run<=0; frame_done<=1;
                    frame_bytes<=BYTES; pixel_count<=PIXELS; frame_seq<=frame_seq+1;
                    frame_crc32<=p_crc32;
                end
            end
            if (abort_cmd && !busy) begin
                frame_crc32<=0;
                frame_done<=0; frame_bytes<=0; pixel_count<=0;
                error_latched<=1; error_code<=5;
            end
            // All data is present before exposing the native AW. A single-beat
            // transaction has no FIFO dependence once granted by the arbiter.
            case (dma_state)
                D_IDLE: if (busy && run && !stop_now && !fifo_empty &&
                            fifo_rd_count!=0 && written_beats<BEATS) dma_state<=D_FETCH;
                D_FETCH: if (!stop_now && fifo_read) dma_state<=D_LATCH;
                D_LATCH: if (!stop_now) begin dma_wdata<=fifo_rdata; dma_state<=D_AW; end
                D_AW: if (dma_complete) begin written_beats<=written_beats+1; dma_state<=D_IDLE; end
                      else if (dma_awready) dma_state<=D_W;
                D_W: if (dma_complete) begin written_beats<=written_beats+1; dma_state<=D_IDLE; end
                default: dma_state<=D_IDLE;
            endcase
        end
    end
endmodule
