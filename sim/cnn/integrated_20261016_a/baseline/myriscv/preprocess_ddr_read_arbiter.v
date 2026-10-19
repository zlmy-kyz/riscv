`timescale 1ns/1ps
// Serial native Pango reads, no RREADY. Lock before presenting AR, retain until
// the counted final R beat. Unknown/incorrect responses quarantine until reset.
module preprocess_ddr_read_arbiter (
    input wire clk, resetn,
    input wire [27:0] cpu_addr, pp_addr,
    input wire [3:0] cpu_len, cpu_id,
    input wire cpu_ap, cpu_valid, pp_valid,
    output wire cpu_ready, pp_ready, cpu_rvalid, pp_rvalid,
    output wire [27:0] araddr,
    output wire [3:0] arlen, arid,
    output wire arap, arvalid,
    input wire arready, rvalid, rlast,
    input wire [3:0] rid,
    output reg protocol_error
);
    localparam IDLE=0, ADDR=1, DATA=2;
    reg [1:0] state;
    reg owner, last_owner;
    reg [4:0] remaining;
    reg [3:0] accepted_id;
    wire ar_fire=arvalid && arready;
    wire response_window=(state==DATA) || ar_fire;
    wire r_fire=resetn && !protocol_error && rvalid && response_window;
    wire [4:0] beats_left=(state==DATA) ? remaining : {1'b0,arlen}+5'd1;
    wire [3:0] expected_id=(state==DATA) ? accepted_id : arid;
    assign arvalid=resetn && !protocol_error && state==ADDR && (owner ? pp_valid : cpu_valid);
    assign araddr=owner ? pp_addr : cpu_addr;
    assign arlen=owner ? 4'd0 : cpu_len;
    assign arid=owner ? 4'd3 : cpu_id;
    assign arap=owner ? 1'b0 : cpu_ap;
    assign cpu_ready=resetn && !protocol_error && !owner && state==ADDR && arready;
    assign pp_ready=resetn && !protocol_error && owner && state==ADDR && arready;
    assign cpu_rvalid=r_fire && !owner;
    assign pp_rvalid=r_fire && owner;
    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            state<=IDLE; owner<=0; last_owner<=1; remaining<=0; accepted_id<=0; protocol_error<=0;
        end else if (!protocol_error) begin
            case (state)
                IDLE: if (cpu_valid || pp_valid) begin
                    owner<=cpu_valid && pp_valid ? !last_owner : pp_valid;
                    state<=ADDR;
                end
                ADDR: if (ar_fire) begin
                    remaining<={1'b0,arlen}+5'd1; accepted_id<=arid; state<=DATA;
                end
                default: begin end
            endcase
            // Later assignments handle an AR/R on the same edge, including len=0.
            if (rvalid) begin
                if (!response_window || rid!=expected_id || rlast!=(beats_left==1)) protocol_error<=1;
                else begin
                    remaining<=beats_left-1'b1;
                    if (beats_left==1) begin state<=IDLE; last_owner<=owner; end
                end
            end
        end
    end
endmodule
