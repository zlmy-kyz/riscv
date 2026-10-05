`timescale 1ns / 1ps

// SRAM-like MMIO: each req_valid && req_ready edge causes one side effect.
// 00 TX_DATA (W), 04 RX_DATA (R), 08 STATUS (R), 0c CONTROL (commands/read zero).
// CONTROL bit8 sets RX IRQ enable, bit9 clears it (clear wins); low W1C unchanged.
// Busy TX writes return bus error. RX reads latch the head and pop only once.
module uart_mmio #(
    parameter integer CLK_HZ = 93_750_000,
    parameter integer BAUD = 115_200,
    parameter integer RSP_DELAY_CYCLES = 0
) (
    input wire clk, resetn,
    input wire req_valid, req_write,
    input wire [1:0] req_size,
    input wire [31:0] req_addr, req_wdata,
    input wire [3:0] req_wstrb,
    output wire req_ready, rsp_valid,
    output wire [31:0] rsp_rdata,
    output wire rsp_error,
    input wire uart_rx,
    output wire uart_tx,
    output wire uart_irq
);
    localparam [1:0] TX_DATA = 2'd0, RX_DATA = 2'd1,
                     STATUS = 2'd2, CONTROL = 2'd3;
    reg pending;
    reg [31:0] wait_count, response_data;
    reg response_error, frame_error_status, overflow_status;
    reg rx_irq_enable;
    wire tx_ready, tx_busy;
    wire [7:0] rx_data, fifo_data;
    wire rx_valid, frame_error, fifo_empty, fifo_full, overflow;
    wire [4:0] fifo_count;
    wire req_fire, access_valid, tx_send, fifo_pop, clear_frame, clear_overflow;
    wire irq_control_write;
    wire [31:0] status_word;

    assign req_ready = resetn && !pending;
    assign req_fire = req_valid && req_ready;
    assign rsp_valid = pending && (wait_count == 0);
    assign rsp_rdata = response_data;
    assign rsp_error = rsp_valid && response_error;
    assign access_valid = (req_addr[31:4] == 0) && (req_size != 2'd3) &&
                          ((req_size == 2'd0) ||
                           (req_size == 2'd1 && !req_addr[0]) ||
                           (req_size == 2'd2 && req_addr[1:0] == 0));
    assign tx_send = req_fire && access_valid && req_write &&
                     req_addr[3:2] == TX_DATA && req_wstrb[0] && tx_ready;
    assign fifo_pop = req_fire && access_valid && !req_write &&
                      req_addr[3:2] == RX_DATA && req_addr[1:0] == 0 && !fifo_empty;
    assign clear_frame = req_fire && access_valid && req_write &&
                         req_addr[3:2] == CONTROL && req_wstrb[0] && req_wdata[0];
    assign clear_overflow = req_fire && access_valid && req_write &&
                            req_addr[3:2] == CONTROL && req_wstrb[0] && req_wdata[1];
    assign irq_control_write = req_fire && access_valid && req_write &&
                               req_addr[3:2] == CONTROL && req_wstrb[1];
    // FIFO occupancy holds the IRQ until software drains it; never use rx_valid.
    assign uart_irq = rx_irq_enable && !fifo_empty;
    assign status_word = {24'd0, uart_irq, rx_irq_enable, overflow_status, frame_error_status,
                          fifo_full, !fifo_empty, tx_busy, tx_ready};

    uart_tx #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) u_tx (
        .clk(clk), .resetn(resetn), .tx_data(req_wdata[7:0]),
        .tx_valid(tx_send), .tx(uart_tx), .tx_busy(tx_busy), .tx_ready(tx_ready)
    );
    uart_rx #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) u_rx (
        .clk(clk), .resetn(resetn), .rx(uart_rx), .rx_data(rx_data),
        .rx_valid(rx_valid), .frame_error(frame_error), .rx_busy()
    );
    uart_rx_fifo u_fifo (
        .clk(clk), .resetn(resetn), .wr_en(rx_valid), .write_data(rx_data),
        .rd_en(fifo_pop), .read_data(fifo_data), .empty(fifo_empty),
        .full(fifo_full), .count(fifo_count), .overflow(overflow)
    );

    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            pending <= 1'b0;
            wait_count <= 32'd0;
            response_data <= 32'd0;
            response_error <= 1'b0;
            frame_error_status <= 1'b0;
            overflow_status <= 1'b0;
            rx_irq_enable <= 1'b0;
        end else begin
            // New events win over simultaneous software W1C.
            frame_error_status <= frame_error || (frame_error_status && !clear_frame);
            overflow_status <= overflow || (overflow_status && !clear_overflow);
            if (irq_control_write) begin
                if (req_wdata[9]) rx_irq_enable <= 1'b0;
                else if (req_wdata[8]) rx_irq_enable <= 1'b1;
            end
            if (pending && wait_count != 0) wait_count <= wait_count - 1'b1;
            if (rsp_valid) pending <= 1'b0;
            if (req_fire) begin
                pending <= 1'b1;
                wait_count <= (RSP_DELAY_CYCLES > 0) ? RSP_DELAY_CYCLES : 0;
                response_data <= 32'd0;
                response_error <= !access_valid;
                if (access_valid) begin
                    case (req_addr[3:2])
                        TX_DATA: response_error <= !req_write || (req_wstrb[0] && !tx_ready);
                        RX_DATA: begin
                            response_data <= {24'd0, fifo_data};
                            response_error <= req_write;
                        end
                        STATUS: begin
                            response_data <= status_word;
                            response_error <= req_write;
                        end
                        CONTROL: begin end // Commands above; read remains zero
                    endcase
                end
            end
        end
    end
endmodule
