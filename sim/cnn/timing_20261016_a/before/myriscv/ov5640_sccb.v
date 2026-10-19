`timescale 1ns/1ps
// One 16-bit-register SCCB transaction. 100 kHz, open drain, ACK checked.
// Read uses STOP between address write and read, as in OV5640 SCCB read cycle.
// SCL release is observed (clock stretching/stuck bus bounded by watchdog).
module ov5640_sccb #(
    parameter integer CLK_HZ=93750000,
    parameter integer BUS_HZ=100000
) (
    input wire clk, resetn, start, read_op,
    input wire [15:0] reg_addr,
    input wire [7:0] write_data,
    input wire scl_in, sda_in,
    output reg scl_low, sda_low,
    output reg busy, done, error,
    output reg [7:0] read_data
);
    localparam integer DIV=(CLK_HZ/(BUS_HZ*4)>0)?CLK_HZ/(BUS_HZ*4):1;
    localparam IDLE=0, START=1, SEND=2, ACK=3, STOP=4, RESTART=5, RECV=6, NACK=7;
    reg [3:0] state;
    reg [1:0] phase;
    reg [31:0] div_count, watchdog;
    reg [7:0] tx, rx;
    reg [2:0] bit_index, byte_index;
    reg [15:0] addr;
    reg [7:0] data;
    reg reading, read_address_phase, stop_then_read;
    (* async_reg="true" *) reg [1:0] scl_sync, sda_sync;
    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin scl_sync<=3; sda_sync<=3; end
        else begin scl_sync<={scl_sync[0],scl_in}; sda_sync<={sda_sync[0],sda_in}; end
    end
    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            state<=IDLE; phase<=0; div_count<=0; watchdog<=0;
            scl_low<=0; sda_low<=0; busy<=0; done<=0; error<=0;
            read_data<=0; tx<=0; rx<=0; bit_index<=7; byte_index<=0;
            addr<=0; data<=0; reading<=0; read_address_phase<=0; stop_then_read<=0;
        end else begin
            done<=0;
            if (!busy) begin
                div_count<=0; watchdog<=0;
                if (start) begin
                    addr<=reg_addr; data<=write_data; reading<=read_op;
                    busy<=1; error<=0; state<=START; phase<=0;
                    tx<=8'h78; byte_index<=0; read_address_phase<=0;
                    stop_then_read<=0; bit_index<=7; rx<=0;
                end
            end else if (watchdog >= CLK_HZ/50) begin
                // A stuck line cannot be recovered by pretending STOP succeeded.
                busy<=0; done<=1; error<=1; state<=IDLE; scl_low<=0; sda_low<=0;
            end else begin
                watchdog<=watchdog+1;
                if (div_count != DIV-1) div_count<=div_count+1;
                else begin
                    div_count<=0;
                    case (state)
                        START, RESTART: case (phase)
                            0: begin scl_low<=0; sda_low<=0; phase<=1; end
                            1: if (scl_sync[1] && sda_sync[1]) begin sda_low<=1; phase<=2; end
                            2: begin scl_low<=1; phase<=3; end
                            3: begin phase<=0; state<=SEND; end
                        endcase
                        SEND: case (phase)
                            0: begin scl_low<=1; sda_low<=!tx[bit_index]; phase<=1; end
                            1: begin scl_low<=0; phase<=2; end
                            2: if (scl_sync[1]) phase<=3;
                            3: begin
                                scl_low<=1; phase<=0;
                                if (bit_index==0) state<=ACK;
                                else bit_index<=bit_index-1'b1;
                            end
                        endcase
                        ACK: case (phase)
                            0: begin sda_low<=0; phase<=1; end
                            1: begin scl_low<=0; phase<=2; end
                            2: if (scl_sync[1]) begin
                                if (sda_sync[1]) error<=1;
                                phase<=3;
                            end
                            3: begin
                                scl_low<=1; phase<=0; bit_index<=7;
                                if (error) begin stop_then_read<=0; state<=STOP; end
                                else if (read_address_phase) state<=RECV;
                                else case (byte_index)
                                    0: begin tx<=addr[15:8]; byte_index<=1; state<=SEND; end
                                    1: begin tx<=addr[7:0]; byte_index<=2; state<=SEND; end
                                    2: if (reading) begin stop_then_read<=1; state<=STOP; end
                                       else begin tx<=data; byte_index<=3; state<=SEND; end
                                    default: begin stop_then_read<=0; state<=STOP; end
                                endcase
                            end
                        endcase
                        RECV: case (phase)
                            0: begin scl_low<=1; sda_low<=0; phase<=1; end
                            1: begin scl_low<=0; phase<=2; end
                            2: if (scl_sync[1]) begin rx[bit_index]<=sda_sync[1]; phase<=3; end
                            3: begin
                                scl_low<=1; phase<=0;
                                if (bit_index==0) begin read_data<=rx; state<=NACK; end
                                else bit_index<=bit_index-1'b1;
                            end
                        endcase
                        NACK: case (phase)
                            0: begin sda_low<=0; phase<=1; end
                            1: begin scl_low<=0; phase<=2; end
                            2: if (scl_sync[1]) phase<=3;
                            3: begin scl_low<=1; phase<=0; stop_then_read<=0; state<=STOP; end
                        endcase
                        STOP: case (phase)
                            0: begin scl_low<=1; sda_low<=1; phase<=1; end
                            1: begin scl_low<=0; phase<=2; end
                            2: if (scl_sync[1]) begin sda_low<=0; phase<=3; end
                            3: begin
                                phase<=0;
                                if (stop_then_read) begin
                                    state<=RESTART; tx<=8'h79; bit_index<=7;
                                    read_address_phase<=1; stop_then_read<=0;
                                end else begin busy<=0; done<=1; state<=IDLE; end
                            end
                        endcase
                        default: begin busy<=0; done<=1; error<=1; state<=IDLE; end
                    endcase
                end
            end
        end
    end
endmodule
