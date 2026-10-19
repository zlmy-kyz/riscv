`timescale 1ns/1ps
// ABI 2: legacy single-frame plus two explicit-ownership stream buffers.
// A=FRAME_BASE, B=FRAME_BASE+2MiB. READY/CPU buffers are never overwritten.
// PCLK-domain FIFO/result state is reset between arms, never during a live DDR W.
module camera_mmio #(
    parameter integer CLK_HZ=93750000,
    parameter integer COLORBAR_ENABLE=0,
    parameter integer DVP_TEST_ENABLE=0,
    parameter integer WIDTH=1280, HEIGHT=720, DROP_FRAMES=10,
    parameter integer EXTERNAL_HOLD_ENABLE=0,
    parameter [31:0] FRAME_BASE=32'h41000000,
    parameter [27:0] FRAME_NATIVE_ADDR=28'h0400000
) (
    input wire clk, resetn,
    input wire req_valid, req_write,
    input wire [1:0] req_size,
    input wire [31:0] req_addr, req_wdata,
    input wire [3:0] req_wstrb,
    output reg busy,
    output reg dual_mode,
    output wire [1:0] cpu_owned,
    input wire [1:0] external_hold,
    output wire [31:0] source_seq0, source_seq1,
    output wire source_geometry_ok,
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
    // Bus protection/cache aperture is fixed at 0x41000000..0x413fffff.
    localparam integer VALID_GEOMETRY=(WIDTH>0 && WIDTH<=4095 && HEIGHT>0 && HEIGHT<=2047 &&
                                     BYTES<=2097152 && (BYTES%32)==0 &&
                                     FRAME_BASE==32'h41000000 && FRAME_NATIVE_ADDR==28'h0400000);
    localparam D_IDLE=0, D_FETCH=1, D_LATCH=2, D_AW=3, D_W=4;
    localparam [1:0] BUF_FREE=0, BUF_WRITING=1, BUF_READY=2, BUF_CPU=3;
    wire config_done, config_error;
    wire [15:0] sensor_id;
    wire [7:0] config_index;
    wire [7:0] config_error_code;
    ov5640_config #(.CLK_HZ(CLK_HZ), .COLORBAR_ENABLE(COLORBAR_ENABLE),
        .DVP_TEST_ENABLE(DVP_TEST_ENABLE)) u_config (
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
    reg stream_enabled, stream_warmed, active_buf, selected_buf, next_buf;
    reg [1:0] buffer_state [0:1];
    reg [31:0] buffer_seq [0:1];
    (* syn_preserve=1 *) reg [31:0] buffer_crc [0:1];
    reg [31:0] expected_seq, wait_cycles;
    reg [3:0] idle_count;
    wire free_available=(buffer_state[0]==BUF_FREE) || (buffer_state[1]==BUF_FREE);
    wire allocate_buf=(buffer_state[next_buf]==BUF_FREE) ? next_buf : !next_buf;
    wire ready_any=(buffer_state[0]==BUF_READY) || (buffer_state[1]==BUF_READY);
    wire all_free=(buffer_state[0]==BUF_FREE) && (buffer_state[1]==BUF_FREE);
    wire wait_free=dual_mode && stream_enabled && !busy && !free_available;
    wire selected_valid=(buffer_state[selected_buf]==BUF_READY) ||
                        (buffer_state[selected_buf]==BUF_CPU);
    assign cpu_owned={buffer_state[1]==BUF_CPU,buffer_state[0]==BUF_CPU};
    assign source_seq0=buffer_seq[0];
    assign source_seq1=buffer_seq[1];
    assign source_geometry_ok=(WIDTH==1280 && HEIGHT==720 && VALID_GEOMETRY);
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
    ov5640_capture #(.WIDTH(WIDTH), .HEIGHT(HEIGHT), .DROP_FRAMES(DROP_FRAMES),
                    .WARMUP_SKIP_ENABLE(1)) u_capture (
        .pclk(pclk), .resetn(wr_reset_pipe[1]), .run(run),
        .skip_warmup(dual_mode && stream_warmed),
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
    assign dma_awaddr=FRAME_NATIVE_ADDR + (active_buf ? 28'h0080000 : 28'd0) + (written_beats << 3);
    wire dma_complete=dma_wready && ((dma_state==D_W) ||
                      (dma_state==D_AW && dma_awready));
    assign req_ready=resetn && !rsp_valid;
    wire accept=req_valid && req_ready;
    wire ctrl_write=accept && req_write && req_addr==4 && req_size==2 && req_wstrb==15;
    wire can_start=config_done && !config_error && VALID_GEOMETRY;
    wire arm_cmd=ctrl_write && req_wdata==1 && !dual_mode && !busy && can_start;
    wire abort_cmd=ctrl_write && req_wdata==2;
    wire clear_cmd=ctrl_write && req_wdata==4 && !busy && !stream_enabled && all_free;
    wire stream_start_cmd=ctrl_write && req_wdata==8 && !busy && !stream_enabled &&
                          all_free && can_start && !error_latched;
    // STOP drains the current valid frame. ABORT instead invalidates the active frame.
    wire stream_stop_cmd=ctrl_write && req_wdata==16 && dual_mode;
    wire claim_cmd=ctrl_write && req_wdata==32 && dual_mode &&
                   buffer_state[selected_buf]==BUF_READY && expected_seq==buffer_seq[selected_buf];
    wire release_cmd=ctrl_write && req_wdata==64 && dual_mode &&
                     buffer_state[selected_buf]==BUF_CPU && expected_seq==buffer_seq[selected_buf] &&
                     ((EXTERNAL_HOLD_ENABLE==0) || !external_hold[selected_buf]);
    wire select_cmd=accept && req_write && req_addr==44 && req_size==2 &&
                    req_wstrb==15 && req_wdata<=1 && dual_mode;
    wire token_cmd=accept && req_write && req_addr==56 && req_size==2 &&
                   req_wstrb==15 && dual_mode;
    wire auto_arm=dual_mode && stream_enabled && !busy && free_available &&
                  idle_count==15 && can_start && !error_latched &&
                  !stream_stop_cmd && !abort_cmd;
    wire begin_capture=arm_cmd || auto_arm;
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
            dual_mode<=0; stream_enabled<=0; stream_warmed<=0;
            active_buf<=0; selected_buf<=0; next_buf<=0; expected_seq<=0; wait_cycles<=0; idle_count<=0;
            buffer_state[0]<=BUF_FREE; buffer_state[1]<=BUF_FREE;
            buffer_seq[0]<=0; buffer_seq[1]<=0; buffer_crc[0]<=0; buffer_crc[1]<=0;
        end else begin
            rsp_valid<=0;
            if (accept) begin
                rsp_valid<=1; rsp_error<=0; rsp_rdata<=0;
                if (req_size!=2 || req_addr[1:0]!=0 || req_addr>60) rsp_error<=1;
                else if (req_write) begin
                    if (!(arm_cmd || abort_cmd || clear_cmd || stream_start_cmd || stream_stop_cmd ||
                          claim_cmd || release_cmd || select_cmd || token_cmd)) rsp_error<=1;
                end else case (req_addr[5:2])
                    0: rsp_rdata<=32'h43414d02;
                    1: rsp_rdata<=0;
                    2: rsp_rdata<={24'b0,wait_free,stream_enabled,dual_mode,
                                  (error_latched|config_error|!VALID_GEOMETRY),overflow_latched,
                                  (dual_mode ? ready_any : frame_done),busy,config_done};
                    3: rsp_rdata<=FRAME_BASE + ((dual_mode && selected_buf) ? 32'h00200000 : 32'd0);
                    4: rsp_rdata<=dual_mode ? (selected_valid ? BYTES : 0) : frame_bytes;
                    5: rsp_rdata<=dual_mode ? (selected_valid ? buffer_seq[selected_buf] : 0) : frame_seq;
                    6: rsp_rdata<=dual_mode ? (selected_valid ? PIXELS : 0) : pixel_count;
                    7: rsp_rdata<=!VALID_GEOMETRY ? 32'd8 : config_error ?
                                  {16'b0,config_index,config_error_code} : {24'b0,error_code};
                    8: rsp_rdata<={16'b0,sensor_id};
                    9: rsp_rdata<=!dual_mode ? written_beats : selected_valid ? BEATS :
                                   (busy && selected_buf==active_buf) ? written_beats : 0;
                    10: rsp_rdata<=dual_mode ? (selected_valid ? buffer_crc[selected_buf] : 0) : frame_crc32;
                    11: rsp_rdata<={31'b0,selected_buf};
                    12: rsp_rdata<={22'b0,wait_free,dual_mode,stream_enabled,busy,active_buf,selected_buf,
                                    buffer_state[1],buffer_state[0]};
                    13: rsp_rdata<=frame_seq;
                    14: rsp_rdata<=expected_seq;
                    15: rsp_rdata<=wait_cycles;
                    default: rsp_error<=1;
                endcase
            end
            if (busy || begin_capture || stream_start_cmd) idle_count<=0;
            else if (idle_count!=15) idle_count<=idle_count+1'b1;
            if (wait_free && wait_cycles!=32'hffffffff) wait_cycles<=wait_cycles+1'b1;
            if (select_cmd) selected_buf<=req_wdata[0];
            if (token_cmd) expected_seq<=req_wdata;
            if (claim_cmd) buffer_state[selected_buf]<=BUF_CPU;
            if (release_cmd) buffer_state[selected_buf]<=BUF_FREE;
            if (stream_stop_cmd || (abort_cmd && dual_mode)) stream_enabled<=0;
            if (stream_start_cmd) begin
                dual_mode<=1; stream_enabled<=1; stream_warmed<=0;
                selected_buf<=0; next_buf<=0; expected_seq<=0; wait_cycles<=0;
                frame_done<=0; frame_bytes<=0; pixel_count<=0; frame_crc32<=0;
            end
            if (clear_cmd) begin
                dual_mode<=0; stream_warmed<=0; selected_buf<=0;
                frame_crc32<=0;
                frame_done<=0; frame_bytes<=0; pixel_count<=0;
                error_latched<=0; overflow_latched<=0; error_code<=0;
            end
            if (begin_capture) begin
                active_buf<=auto_arm ? allocate_buf : 1'b0;
                if (auto_arm) begin
                    buffer_state[allocate_buf]<=BUF_WRITING;
                    buffer_seq[allocate_buf]<=0; buffer_crc[allocate_buf]<=0;
                    next_buf<=!allocate_buf;
                end
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
                    if (dual_mode) stream_enabled<=0;
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
                        if (dual_mode) buffer_state[active_buf]<=BUF_FREE;
                    end
                end else if (run && done_sync[1] && written_beats==BEATS && dma_state==D_IDLE) begin
                    busy<=0; run<=0; frame_done<=1;
                    frame_bytes<=BYTES; pixel_count<=PIXELS; frame_seq<=frame_seq+1;
                    frame_crc32<=p_crc32;
                    if (dual_mode) begin
                        buffer_state[active_buf]<=BUF_READY;
                        buffer_seq[active_buf]<=frame_seq+1;
                        buffer_crc[active_buf]<=p_crc32;
                        stream_warmed<=1;
                    end
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
