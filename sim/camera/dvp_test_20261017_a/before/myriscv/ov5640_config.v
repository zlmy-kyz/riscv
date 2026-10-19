`timescale 1ns/1ps
module ov5640_config #(parameter integer CLK_HZ=93750000,
    parameter integer COLORBAR_ENABLE=0) (
    input wire clk, resetn, scl_in, sda_in,
    output wire scl_low, sda_low,
    output reg sensor_resetn, config_done, config_error,
    output reg [7:0] config_error_code,
    output reg [15:0] sensor_id,
    output reg [7:0] config_index
);
    localparam HOLD_RESET=0, RELEASE_WAIT=1, ISSUE=2, WAIT_BUS=3, GAP=4, FINISH=5;
    reg [2:0] state;
    reg [31:0] count;
    reg reading, start;
    reg [3:0] read_index;
    wire [23:0] table_data;
    reg [15:0] check_addr;
    reg [7:0] check_value;
    wire busy, done, error;
    wire [7:0] read_data;
    localparam [7:0] LAST_WRITE=(COLORBAR_ENABLE!=0) ? 8'd244 : 8'd243;
    localparam [3:0] LAST_READ=(COLORBAR_ENABLE!=0) ? 4'd9 : 4'd7;
    ov5640_config_rom #(.COLORBAR_ENABLE(COLORBAR_ENABLE)) u_rom (.index(config_index), .data(table_data));
    always @* begin
        case (read_index)
            0: begin check_addr=16'h300a; check_value=8'h56; end
            1: begin check_addr=16'h300b; check_value=8'h40; end
            2: begin check_addr=16'h3808; check_value=8'h05; end
            3: begin check_addr=16'h3809; check_value=8'h00; end
            4: begin check_addr=16'h380a; check_value=8'h02; end
            5: begin check_addr=16'h380b; check_value=8'hd0; end
            6: begin check_addr=16'h4300; check_value=8'h61; end
            7: begin check_addr=16'h501f; check_value=8'h01; end
            8: begin check_addr=16'h503d; check_value=8'h80; end
            default: begin check_addr=16'h4741; check_value=8'h00; end
        endcase
    end
    ov5640_sccb #(.CLK_HZ(CLK_HZ)) u_bus (
        .clk(clk), .resetn(resetn), .start(start), .read_op(reading),
        .reg_addr(reading ? check_addr : table_data[23:8]),
        .write_data(table_data[7:0]), .scl_in(scl_in), .sda_in(sda_in),
        .scl_low(scl_low), .sda_low(sda_low), .busy(busy), .done(done),
        .error(error), .read_data(read_data)
    );
    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            state<=HOLD_RESET; count<=0; reading<=0; start<=0; read_index<=0;
            sensor_resetn<=0; config_done<=0; config_error<=0;
            sensor_id<=0; config_index<=0; config_error_code<=0;
        end else begin
            start<=0;
            case (state)
                HOLD_RESET: if (count>=CLK_HZ/100-1) begin
                    count<=0; sensor_resetn<=1; state<=RELEASE_WAIT;
                end else count<=count+1;
                RELEASE_WAIT: if (count>=CLK_HZ/25-1) begin count<=0; state<=ISSUE; end
                              else count<=count+1;
                ISSUE: if (!busy) begin start<=1; state<=WAIT_BUS; end
                WAIT_BUS: if (done) begin
                    if (reading && read_index==0) sensor_id[15:8]<=read_data;
                    if (reading && read_index==1) sensor_id[7:0]<=read_data;
                    if (error || (reading && read_data!=check_value)) begin
                        config_error<=1; state<=FINISH;
                        config_error_code<=error ? 8'd1 : (read_index<2 ? 8'd6 : 8'd7);
                    end else if (reading && read_index==LAST_READ) begin
                        config_done<=1; state<=FINISH;
                    end else begin
                        // Delay after software reset is distinct from normal gaps.
                        count<=(!reading && config_index==0) ? CLK_HZ/25 : CLK_HZ/1000;
                        state<=GAP;
                    end
                end
                GAP: if (count!=0) count<=count-1;
                     else begin
                         if (reading) read_index<=read_index+1'b1;
                         else if (config_index==LAST_WRITE) begin reading<=1; read_index<=0; end
                         else config_index<=config_index+1'b1;
                         state<=ISSUE;
                     end
                FINISH: begin end
                default: begin config_error<=1; config_error_code<=8'd8; state<=FINISH; end
            endcase
        end
    end
endmodule
