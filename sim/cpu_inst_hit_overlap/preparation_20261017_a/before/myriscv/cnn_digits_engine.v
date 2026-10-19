`timescale 1ns/1ps
// Fixed digits10_int8_v1 sequencer. Two synchronous 2KiB activation banks.
// Parameter and gray writes are authorized by the owning MMIO controller.
module cnn_digits_engine (
    input wire clk, resetn, cancel,
    input wire param_we,
    input wire [12:0] param_index,
    input wire [31:0] param_data,
    input wire gray_we,
    input wire [9:0] gray_addr,
    input wire [7:0] gray_data,
    input wire start,
    output wire ready,
    output reg done, error,
    input wire [3:0] score_index,
    output wire [31:0] score_data,
    output reg [3:0] prediction
);
    reg [7:0] bank0 [0:2047];
    reg [7:0] bank1 [0:2047];
    reg [7:0] weights [0:6151];
    reg [31:0] biases [0:65];
    reg [4:0] shifts [0:3];
    reg signed [31:0] scores [0:9];
    localparam IDLE=0, SETUP=1, BREAD=2, BWAIT=3, CMD=4,
        READ=5, WAIT=6, SEND=7, MAC_RESULT=8, QUANT_RESULT=9,
        GREAD=10, GWAIT=11, GSEND=12, GRESULT=13;
    reg [3:0] state;
    reg [1:0] layer;
    reg read_bank;
    reg [5:0] cin, cout, width_in, width_out, ox, oy, oc, ic;
    reg [1:0] kx, ky;
    reg [7:0] term, terms;
    reg [12:0] weight_base, weight_oc;
    reg [6:0] bias_base;
    reg [10:0] output_addr;
    reg [3:0] gap_pos;
    reg [4:0] gap_channel;
    reg pad_q;
    reg [7:0] act_q, weight_q;
    reg [31:0] bias_q;
    reg signed [31:0] best;
    wire signed [7:0] sx = $signed({1'b0,ox,1'b0}) + $signed({6'b0,kx}) - 8'sd1;
    wire signed [7:0] sy = $signed({1'b0,oy,1'b0}) + $signed({6'b0,ky}) - 8'sd1;
    wire pad = layer!=3 && (sx<0 || sy<0 || sx >= $signed({2'b0,width_in}) || sy >= $signed({2'b0,width_in}));
    // Power-of-two dimensions/channels; extend BEFORE shifts.
    wire [10:0] row_pixel = layer==0 ? ({6'b0,sy[4:0]}<<5)+{6'b0,sx[4:0]} :
                           layer==1 ? ({7'b0,sy[3:0]}<<4)+{7'b0,sx[3:0]} :
                                      ({8'b0,sy[2:0]}<<3)+{8'b0,sx[2:0]};
    wire [10:0] conv_addr = layer==0 ? row_pixel :
                           layer==1 ? (row_pixel<<3)+{5'b0,ic} : (row_pixel<<4)+{5'b0,ic};
    wire gap_state = state==GREAD || state==GWAIT || state==GSEND || state==GRESULT;
    wire [10:0] act_addr = gap_state ? {2'b0,gap_pos,gap_channel} :
                                  layer==3 ? {3'b0,term} : conv_addr;
    wire [12:0] weight_addr = weight_oc+{5'b0,term};
    wire [6:0] bias_addr = bias_base+{1'b0,oc};
    wire units_resetn=resetn && !cancel;
    wire mc_ready, mi_ready, mo_valid, mo_error, qi_ready, qo_valid;
    wire signed [31:0] mo_data, qo_data;
    wire gi_ready, go_valid, go_error;
    wire [7:0] go_data;
    wire q_take = state==QUANT_RESULT && qo_valid;
    wire g_take = state==GRESULT && go_valid;
    assign ready=state==IDLE;
    assign score_data=score_index<10 ? scores[score_index] : 32'b0;
    // No reset on RAM arrays; MMIO validates a complete model and complete input.
    always @(posedge clk) begin
        if (resetn && param_we) begin
            if (param_index<6152) weights[param_index]<=param_data[7:0];
            else if (param_index<6218) biases[param_index-13'd6152]<=param_data;
            else if (param_index<6222) shifts[param_index-13'd6218]<=param_data[4:0];
        end
        act_q <= read_bank ? bank1[act_addr] : bank0[act_addr];
        weight_q <= weights[weight_addr];
        bias_q <= biases[bias_addr];
        if (resetn && !cancel) begin
            if (gray_we) bank0[{1'b0,gray_addr}]<=gray_data;
            else if (q_take && layer!=3) begin
                if (read_bank) bank0[output_addr]<=qo_data[7:0];
                else bank1[output_addr]<=qo_data[7:0];
            end else if (g_take && !go_error) begin
                // conv3 output is bank1; pooled vector is bank0.
                bank0[{6'b0,gap_channel}]<=go_data;
            end
        end
    end
    cnn_int8_mac u_mac (.clk(clk),.resetn(units_resetn),
        .cmd_valid(state==CMD),.cmd_ready(mc_ready),.bias(bias_q),.term_count({8'b0,terms}),
        .in_valid(state==SEND),.in_ready(mi_ready),.activation(pad_q ? 8'sd0 : $signed(act_q)),
        .weight($signed(weight_q)),.out_valid(mo_valid),.out_ready(state==MAC_RESULT && qi_ready),
        .out_data(mo_data),.out_error(mo_error));
    cnn_requantize u_quant (.clk(clk),.resetn(units_resetn),
        .in_valid(state==MAC_RESULT && mo_valid && !mo_error),.in_ready(qi_ready),
        .in_data(mo_data),.shift(shifts[layer]),.relu_int8(layer!=3),
        .out_valid(qo_valid),.out_ready(state==QUANT_RESULT),.out_data(qo_data),.out_clipped());
    cnn_gap16 u_gap (.clk(clk),.resetn(units_resetn),
        .in_valid(state==GSEND),.in_ready(gi_ready),.in_data(act_q),
        .out_valid(go_valid),.out_ready(state==GRESULT),.out_data(go_data),.out_error(go_error));
    integer n;
    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            state<=IDLE; layer<=0; read_bank<=0; done<=0; error<=0; prediction<=0;
            cin<=0; cout<=0; width_in<=0; width_out<=0; ox<=0; oy<=0; oc<=0; ic<=0;
            kx<=0; ky<=0; term<=0; terms<=0; weight_base<=0; weight_oc<=0; bias_base<=0;
            output_addr<=0; gap_pos<=0; gap_channel<=0; pad_q<=0; best<=0;
            for(n=0;n<10;n=n+1) scores[n]<=0;
        end else if (cancel) begin
            state<=IDLE; done<=0; error<=0;
        end else case (state)
            IDLE: if(start) begin
                layer<=0; read_bank<=0; done<=0; error<=0; prediction<=0; state<=SETUP;
            end
            SETUP: begin
                ox<=0; oy<=0; oc<=0; ic<=0; kx<=0; ky<=0; term<=0; output_addr<=0;
                case(layer)
                    0: begin cin<=1; cout<=8; width_in<=32; width_out<=16; terms<=9;
                        weight_base<=0; weight_oc<=0; bias_base<=0; end
                    1: begin cin<=8; cout<=16; width_in<=16; width_out<=8; terms<=72;
                        weight_base<=72; weight_oc<=72; bias_base<=8; end
                    2: begin cin<=16; cout<=32; width_in<=8; width_out<=4; terms<=144;
                        weight_base<=1224; weight_oc<=1224; bias_base<=24; end
                    3: begin cin<=32; cout<=10; width_in<=1; width_out<=1; terms<=32;
                        weight_base<=5832; weight_oc<=5832; bias_base<=56; end
                endcase
                state<=BREAD;
            end
            BREAD: state<=BWAIT;
            BWAIT: state<=CMD;
            CMD: if(mc_ready) begin term<=0; ic<=0; kx<=0; ky<=0; state<=READ; end
            READ: begin pad_q<=pad; state<=WAIT; end
            WAIT: state<=SEND;
            SEND: if(mi_ready) begin
                if(term==terms-1'b1) state<=MAC_RESULT;
                else begin
                    term<=term+1'b1;
                    if(ic==cin-1'b1) begin
                        ic<=0;
                        if(kx==2) begin kx<=0; ky<=ky+1'b1; end
                        else kx<=kx+1'b1;
                    end else ic<=ic+1'b1;
                    state<=READ;
                end
            end
            MAC_RESULT: if(mo_valid && qi_ready) begin
                if(mo_error) begin error<=1; state<=IDLE; end
                else state<=QUANT_RESULT;
            end
            QUANT_RESULT: if(qo_valid) begin
                if(layer==3) begin
                    scores[oc]<=qo_data;
                    if(oc==0 || qo_data>best) begin best<=qo_data; prediction<=oc[3:0]; end
                end
                output_addr<=output_addr+1'b1;
                if(oc==cout-1'b1) begin
                    oc<=0; weight_oc<=weight_base;
                    if(ox==width_out-1'b1) begin
                        ox<=0;
                        if(oy==width_out-1'b1) begin
                            if(layer==3) begin done<=1; state<=IDLE; end
                            else if(layer==2) begin
                                read_bank<=1; gap_pos<=0; gap_channel<=0; state<=GREAD;
                            end else begin layer<=layer+1'b1; read_bank<=!read_bank; state<=SETUP; end
                        end else begin oy<=oy+1'b1; state<=BREAD; end
                    end else begin ox<=ox+1'b1; state<=BREAD; end
                end else begin oc<=oc+1'b1; weight_oc<=weight_oc+{5'b0,terms}; state<=BREAD; end
            end
            GREAD: state<=GWAIT;
            GWAIT: state<=GSEND;
            GSEND: if(gi_ready) begin
                if(gap_pos==15) state<=GRESULT;
                else begin gap_pos<=gap_pos+1'b1; state<=GREAD; end
            end
            GRESULT: if(go_valid) begin
                if(go_error) begin error<=1; state<=IDLE; end
                else if(gap_channel==31) begin layer<=3; read_bank<=0; state<=SETUP; end
                else begin gap_channel<=gap_channel+1'b1; gap_pos<=0; state<=GREAD; end
            end
            default: begin error<=1; state<=IDLE; end
        endcase
    end
endmodule
