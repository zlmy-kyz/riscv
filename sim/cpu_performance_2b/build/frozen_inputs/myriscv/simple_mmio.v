`timescale 1ns / 1ps

// 用于验证地址译码和外设访问的最小 MMIO 从机。
// 局部地址布局：
//   0x000 SCRATCH  可读写，支持字节写使能
//   0x004 ID       只读，固定为 "MMIO"
//   0x008 CYCLE    只读，自复位释放后递增
//   0x00c STATUS   只读，bit0 恒为 1
//   0x010 TEST_STATUS  0=IDLE，1=RUN，2=PASS，3=FAIL；结果锁存至复位
// 其他偏移以及对只读寄存器的写入返回总线错误。
module simple_mmio (
    input  wire        clk,
    input  wire        resetn,

    input  wire        req_valid,
    input  wire        req_write,
    input  wire [ 1:0] req_size,
    input  wire [31:0] req_addr,
    input  wire [31:0] req_wdata,
    input  wire [ 3:0] req_wstrb,
    output wire        req_ready,

    output wire        rsp_valid,
    output wire [31:0] rsp_rdata,
    output wire        rsp_error,
    output reg  [ 1:0] test_status
);

    reg        pending;
    reg [31:0] response_data;
    reg        response_error;
    reg [31:0] scratch;
    reg [31:0] cycle_counter;
    wire       req_fire;

    function [31:0] merge_wstrb;
        input [31:0] old_value;
        input [31:0] new_value;
        input [ 3:0] write_strobe;
        integer i;
        begin
            merge_wstrb = old_value;
            for (i = 0; i < 4; i = i + 1)
                if (write_strobe[i])
                    merge_wstrb[i*8 +: 8] = new_value[i*8 +: 8];
        end
    endfunction

    assign req_ready = !pending;
    assign req_fire  = req_valid && req_ready;
    assign rsp_valid = pending;
    assign rsp_rdata = response_data;
    assign rsp_error = pending && response_error;

    always @(posedge clk) begin
        if (!resetn) begin
            pending        <= 1'b0;
            response_data  <= 32'b0;
            response_error <= 1'b0;
            scratch        <= 32'b0;
            cycle_counter  <= 32'b0;
            test_status    <= 2'd0;
        end else begin
            cycle_counter <= cycle_counter + 32'd1;

            if (rsp_valid)
                pending <= 1'b0;

            if (req_fire) begin
                pending        <= 1'b1;
                response_data  <= 32'b0;
                response_error <= 1'b0;

                case (req_addr[11:2])
                    10'd0: begin
                        response_data <= scratch;
                        if (req_write)
                            scratch <= merge_wstrb(scratch, req_wdata,
                                                   req_wstrb);
                    end
                    10'd1: begin
                        response_data <= 32'h4d4d_494f;
                        if (req_write)
                            response_error <= 1'b1;
                    end
                    10'd2: begin
                        response_data <= cycle_counter;
                        if (req_write)
                            response_error <= 1'b1;
                    end
                    10'd3: begin
                        response_data <= 32'h0000_0001;
                        if (req_write)
                            response_error <= 1'b1;
                    end
                    10'd4: begin
                        response_data <= {30'b0, test_status};
                        // 仅最低字节有效；PASS/FAIL 必须在 RUN 之后上报。
                        if (req_write && req_wstrb[0]) begin
                            case (req_wdata[7:0])
                                8'd1: begin
                                    if (test_status == 2'd0)
                                        test_status <= 2'd1;
                                end
                                8'd2, 8'd3: begin
                                    if (test_status == 2'd1)
                                        test_status <= req_wdata[1:0];
                                    else if (test_status == 2'd0)
                                        response_error <= 1'b1;
                                end
                                default: response_error <= 1'b1;
                            endcase
                        end
                    end
                    default: response_error <= 1'b1;
                endcase
            end
        end
    end

    wire [1:0] _unused_req_size = req_size;

endmodule
