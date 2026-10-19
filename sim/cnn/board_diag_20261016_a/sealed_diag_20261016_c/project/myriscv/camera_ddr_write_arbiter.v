`timescale 1ns/1ps
// Pango native write port: no WVALID and no B channel. Lock selection BEFORE
// presenting AW, retain it under AW backpressure and through all W consumptions.
module camera_ddr_write_arbiter #(parameter [3:0] CAM_AW_ID=4'd2) (
    input wire clk, resetn,
    input wire [27:0] cpu_awaddr, cam_awaddr,
    input wire [3:0] cpu_awlen, cpu_awid,
    input wire cpu_awap, cpu_awvalid, cam_awvalid,
    input wire [255:0] cpu_wdata, cam_wdata,
    input wire [31:0] cpu_wstrb,
    output wire cpu_awready, cpu_wready, cam_awready, cam_wready,
    output wire [27:0] awaddr,
    output wire [3:0] awlen, awid,
    output wire awap, awvalid,
    output wire [255:0] wdata,
    output wire [31:0] wstrb,
    input wire awready, wready,
    output wire busy
);
    localparam IDLE=0, ADDR=1, DATA=2;
    reg [1:0] state;
    reg owner, last_owner;
    reg [4:0] remaining;
    wire selected_valid = owner ? cam_awvalid : cpu_awvalid;
    wire address_fire = awvalid && awready;
    wire data_fire = wready && ((state == DATA) || address_fire);
    assign busy = state != IDLE;
    assign awvalid = resetn && state == ADDR && selected_valid;
    assign awaddr = owner ? cam_awaddr : cpu_awaddr;
    assign awlen = owner ? 4'd0 : cpu_awlen;
    assign awid = owner ? CAM_AW_ID : cpu_awid;
    assign awap = owner ? 1'b0 : cpu_awap;
    assign wdata = owner ? cam_wdata : cpu_wdata;
    assign wstrb = owner ? 32'hffffffff : cpu_wstrb;
    assign cpu_awready = !owner && state == ADDR && awready && resetn;
    assign cam_awready = owner && state == ADDR && awready && resetn;
    assign cpu_wready = !owner && data_fire && resetn;
    assign cam_wready = owner && data_fire && resetn;
    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin state<=IDLE; owner<=0; last_owner<=1; remaining<=0; end
        else case (state)
            IDLE: if (cpu_awvalid || cam_awvalid) begin
                owner <= cpu_awvalid && cam_awvalid ? !last_owner : cam_awvalid;
                state <= ADDR;
            end
            ADDR: if (address_fire) begin
                remaining <= {1'b0,awlen} + 5'd1 - (data_fire ? 5'd1 : 5'd0);
                if (data_fire && awlen == 0) begin
                    state<=IDLE; last_owner<=owner;
                end else state<=DATA;
            end
            DATA: if (data_fire) begin
                remaining<=remaining-1'b1;
                if (remaining==1) begin state<=IDLE; last_owner<=owner; end
            end
            default: state<=IDLE;
        endcase
    end
endmodule
