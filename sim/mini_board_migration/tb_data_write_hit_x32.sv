`timescale 1ns/1ps
// Functional Pango user-port test only; physical DDR performance is a separate run.
module tb_data_write_hit_x32;
    GTP_GRS GRS_INST (.GRS_N(1'b1));
    // Independent capacity oracle; production RTL fixes I64/D64.
    localparam integer I_LINES = 64;
    localparam integer D_LINES = 64;
    localparam integer D_ENABLED = 1;
    localparam integer ENABLE = 1;
    reg clk=0, resetn=0, init_done=0;
    always #5 clk=~clk;
    reg iv=0, dv=0, dw=0;
    reg [31:0] ia=0, da=0, wd=0;
    reg [3:0] ws=0;
    reg [1:0] ds=2;
    wire ir, dr, isv, dsv, ise, dse;
    wire [31:0] idata, ddata;
    wire [27:0] aa, ra;
    wire av, rv, ardy, rrdy, wrdy, apw, apr;
    wire [255:0] wdata, rdata;
    wire [31:0] wstrb;
    wire [3:0] wid, rid, alen, rlen;
    wire rvalid;
    reg backpressure=1, instant_read=0, instant_write=0;
    reg bad_id=0, bad_last=0, cross_id=0, stray_read=0;
    reg reading=0, writing=0;
    reg [27:0] saved_ra=0, saved_aa=0;
    reg [3:0] saved_rid=0;
    integer aw_wait=0, ar_wait=0, r_wait=0, w_wait=0;
    integer ar_count=0, aw_count=0, w_count=0;
    integer i_requests=0, d_requests=0, i_responses=0, d_responses=0;
    integer tests=0, k, lane;
    // Existing 128 backing rows cover all I64 addresses 0x000..0xfff.
    // Keep the successful DDR timing model and transfer oracle.
    reg [255:0] memory[0:127];
    reg [255:0] expected_wdata=0;
    reg [31:0] expected_wstrb=0;
    reg [27:0] expected_aa=0, expected_ra=0;
    reg [3:0] expected_rid=0;
    reg ar_blocked=0, aw_blocked=0;
    reg [27:0] held_ra=0, held_aa=0;
    reg [255:0] held_wdata=0;
    reg [31:0] held_wstrb=0;
    reg [3:0] held_rid=0;

    assign rrdy=rv && !reading && (!backpressure || ar_wait>=3);
    assign ardy=av && !writing && (!backpressure || aw_wait>=2);
    assign rvalid=stray_read || (instant_read && rv && rrdy) || (reading && r_wait==0);
    assign rdata=stray_read ? 256'hbad0bad1_bad2bad3_bad4bad5_bad6bad7_bad0bad1_bad2bad3_bad4bad5_bad6bad7 :
                             memory[(instant_read ? ra : saved_ra)>>3];
    assign wrdy=(instant_write && av && ardy) || (writing && w_wait==0);
    wire [27:0] write_addr=instant_write ? aa : saved_aa;
    wire [3:0] model_id=instant_read ? rid : saved_rid;
    wire [3:0] returned_id=bad_id ? 4'hf : (cross_id ? (model_id ^ 4'd1) : model_id);

    dual_sram_to_pango_ddr_bridge #(.MEM_DQ_WIDTH(32), .INST_LINE_BUFFER_ENABLE(ENABLE)) dut(
        .clk(clk),.resetn(resetn),.ddr_init_done(init_done),
        .inst_req_valid(iv),.inst_req_addr(ia),.inst_req_ready(ir),
        .inst_rsp_valid(isv),.inst_rsp_rdata(idata),.inst_rsp_error(ise),
        .data_req_valid(dv),.data_req_write(dw),.data_req_size(ds),
        .data_req_addr(da),.data_req_wdata(wd),.data_req_wstrb(ws),
        .data_req_ready(dr),.data_rsp_valid(dsv),.data_rsp_rdata(ddata),.data_rsp_error(dse),
        .axi_awaddr(aa),.axi_awuser_ap(apw),.axi_awuser_id(wid),.axi_awlen(alen),
        .axi_awready(ardy),.axi_awvalid(av),.axi_wdata(wdata),.axi_wstrb(wstrb),
        .axi_wready(wrdy),.axi_wusero_id(4'd1),.axi_wusero_last(wrdy),
        .axi_araddr(ra),.axi_aruser_ap(apr),.axi_aruser_id(rid),.axi_arlen(rlen),
        .axi_arready(rrdy),.axi_arvalid(rv),.axi_rdata(rdata),
        .axi_rid(returned_id),.axi_rlast(rvalid && !bad_last),.axi_rvalid(rvalid));

    function automatic [31:0] word_at(input [31:0] address);
        word_at=memory[address>>5][address[4:2]*32+:32];
    endfunction

    always @(posedge clk) begin
        if (!resetn) begin
            reading<=0; writing<=0; ar_wait<=0; aw_wait<=0; r_wait<=0; w_wait<=0;
            ar_count<=0; aw_count<=0; w_count<=0;
            i_requests<=0; d_requests<=0; i_responses<=0; d_responses<=0;
            ar_blocked<=0;aw_blocked<=0;
        end else begin
            if (ar_blocked && (!rv || ra!==held_ra || rid!==held_rid))
                $fatal(1,"RESULT: FAIL read address changed under backpressure");
            if (aw_blocked && (!av || aa!==held_aa || wdata!==held_wdata || wstrb!==held_wstrb))
                $fatal(1,"RESULT: FAIL write command changed under backpressure");
            ar_blocked<=rv && !rrdy;aw_blocked<=av && !ardy;
            held_ra<=ra;held_rid<=rid;held_aa<=aa;held_wdata<=wdata;held_wstrb<=wstrb;
            if (iv && ir) begin expected_ra<={ia[29:5],3'b0};expected_rid<=0;end
            if (dv && dr) begin
                if (dw) begin
                    expected_aa<={da[29:5],3'b0};
                    expected_wdata<={224'b0,wd} << {da[4:2],5'b0};
                    expected_wstrb<={28'b0,ws} << {da[4:2],2'b0};
                end else begin expected_ra<={da[29:5],3'b0};expected_rid<=1;end
            end
            if (iv && ir) i_requests<=i_requests+1;
            if (dv && dr) d_requests<=d_requests+1;
            if (isv) i_responses<=i_responses+1;
            if (dsv) d_responses<=d_responses+1;
            if (isv && dsv) $fatal(1,"RESULT: FAIL duplicate response owner");
            if (iv && dv && ir) $fatal(1,"RESULT: FAIL instruction bypassed data priority");
            if (rv && !rrdy) ar_wait<=ar_wait+1;
            if (av && !ardy) aw_wait<=aw_wait+1;
            if (rv && rrdy) begin
                if (rlen!=0 || ra!==expected_ra || rid!==expected_rid || apr)
                    $fatal(1,"RESULT: FAIL read command");
                ar_count<=ar_count+1; ar_wait<=0;
                saved_ra<=ra; saved_rid<=rid;
                if (!instant_read) begin reading<=1; r_wait<=4; end
            end
            if (reading && r_wait>0) r_wait<=r_wait-1;
            if (reading && rvalid) reading<=0;
            if (av && ardy) begin
                if (alen!=0 || aa!==expected_aa || wid!=1 || apw)
                    $fatal(1,"RESULT: FAIL write command");
                aw_count<=aw_count+1; aw_wait<=0; saved_aa<=aa;
                if (!instant_write) begin writing<=1; w_wait<=4; end
            end
            if (writing && w_wait>0) w_wait<=w_wait-1;
            if (wrdy) begin
                if (wdata!==expected_wdata || wstrb!==expected_wstrb)
                    $fatal(1,"RESULT: FAIL write lane/strobe expansion");
                for (integer byte_lane=0;byte_lane<32;byte_lane=byte_lane+1)
                    if (wstrb[byte_lane]) memory[write_addr>>3][byte_lane*8+:8]<=wdata[byte_lane*8+:8];
                w_count<=w_count+1; writing<=0;
            end
        end
    end

    task automatic transfer(input bit data_port, input bit write_request,
                            input [31:0] address, input [31:0] value, input [3:0] strobe,
                            input [31:0] expected, input integer cached_ar);
        integer old_ar, old_aw, waited, expected_ar;
        begin
            @(negedge clk);
            old_ar=ar_count; old_aw=aw_count;
            expected_ar=write_request ? 0 : ((data_port ? !D_ENABLED : !ENABLE) ? 1 : cached_ar);
            if (data_port) begin dv=1;dw=write_request;da=address;wd=value;ws=strobe;end
            else begin iv=1;ia=address;end
            @(posedge clk);
            while (!(data_port ? dr : ir)) @(posedge clk);
            @(negedge clk);
            if (data_port) begin dv=0;da='hfe4;wd=32'hdeadbeef;ws=0;dw=0;end
            else begin iv=0;ia='hfd0;end
            waited=0;
            while (!(data_port ? dsv : isv)) begin
                @(negedge clk); waited=waited+1;
                if (waited>100) $fatal(1,"RESULT: FAIL response timeout");
            end
            if (!write_request && (data_port ? D_ENABLED : ENABLE) && cached_ar==0 && waited!=0)
                $fatal(1,"RESULT: FAIL hit did not respond on next cycle");
            if ((data_port ? ddata : idata)!==expected || (data_port ? dse : ise))
                $fatal(1,"RESULT: FAIL wrong response data address=%h",address);
            if (ar_count-old_ar!=expected_ar || aw_count-old_aw!=integer'(write_request))
                $fatal(1,"RESULT: FAIL command count address=%h AR=%0d expected=%0d",
                       address,ar_count-old_ar,expected_ar);
            @(negedge clk);
            if (isv || dsv) $fatal(1,"RESULT: FAIL response repeated");
            tests=tests+1;
        end
    endtask


    task automatic fetch(input [31:0] address,input integer cached_ar);
        transfer(0,0,address,0,0,word_at(address),cached_ar);
    endtask
    task automatic load_word(input [31:0] address,input integer cached_ar);
        transfer(1,0,address,0,0,word_at(address),cached_ar);
    endtask
    task automatic store_word(input [31:0] address,input [31:0] value,input [3:0] strobe);
        transfer(1,1,address,value,strobe,0,0);
    endtask
    task automatic conservation;
        repeat(2) @(negedge clk);
        if (i_requests!=i_responses || d_requests!=d_responses || aw_count!=w_count)
            $fatal(1,"RESULT: FAIL request/response/beat conservation");
    endtask


    task automatic cold;
        begin
            conservation();
            @(negedge clk);init_done=0;
            repeat(2) @(negedge clk);
            if (ir || dr) $fatal(1,"RESULT: FAIL ready without DDR initialization");
            init_done=1;
        end
    endtask

    // Independent metadata oracle, driven by observed DDR fills and CPU requests.
    reg [63:0] oracle_valid=0;
    reg [26:0] oracle_tag[0:63];
    reg pending_store=0, pending_hit=0;
    reg [5:0] pending_row=0;
    integer prior_write_count=0;
    integer checked_fill_writes=0, checked_hit_writes=0;
    wire backend_write=(instant_write && av && ardy && wrdy) || (writing && wrdy);
    wire backend_data_fill=rvalid && returned_id==1 && !bad_last &&
                           ((instant_read && rv && rrdy) || reading);
    wire [27:0] fill_address=instant_read ? ra : saved_ra;
    wire expected_cache_write=resetn && init_done &&
                              (backend_data_fill || (backend_write && pending_store && pending_hit));

    always @(posedge clk) begin
        if (dut.g_data_drm.u_data_data_ram.wr_en !== expected_cache_write)
            $fatal(1,"RESULT: FAIL cache write enable outside fill/store completion");
        if (expected_cache_write) begin
            if (backend_data_fill) begin
                if (dut.g_data_drm.u_data_data_ram.wr_byte_en !== 32'hffffffff ||
                    dut.g_data_drm.u_data_data_ram.wr_data !== rdata ||
                    dut.g_data_drm.u_data_data_ram.wr_addr !== fill_address[8:3])
                    $fatal(1,"RESULT: FAIL full-line byte-enable/data/address");
                checked_fill_writes<=checked_fill_writes+1;
            end else begin
                if (dut.g_data_drm.u_data_data_ram.wr_byte_en !== expected_wstrb ||
                    dut.g_data_drm.u_data_data_ram.wr_data !== expected_wdata ||
                    dut.g_data_drm.u_data_data_ram.wr_addr !== pending_row)
                    $fatal(1,"RESULT: FAIL locked write-hit lane/data/byte-enable");
                checked_hit_writes<=checked_hit_writes+1;
            end
        end
        if (!resetn) begin
            oracle_valid<=0; pending_store<=0; pending_hit<=0;
        end else begin
            if (!init_done) oracle_valid<=0;
            else if (backend_data_fill) begin
                oracle_valid[fill_address[8:3]]<=1;
                oracle_tag[fill_address[8:3]]<=fill_address>>3;
            end
            if (init_done && dut.data_line_valid !== oracle_valid)
                $fatal(1,"RESULT: FAIL D valid changed outside reset/fill");
            if (dv && dr && dw) begin
                pending_store<=1;
                pending_hit<=oracle_valid[da[10:5]] && oracle_tag[da[10:5]]==da[31:5];
                pending_row<=da[10:5]; prior_write_count<=w_count;
            end
            if (dsv && pending_store) begin
                if (w_count!=prior_write_count+1)
                    $fatal(1,"RESULT: FAIL store responded before/excess DDR write completion");
                pending_store<=0;
            end
        end
    end

    task automatic reset_write(input integer phase);
        integer waited;
        begin
            cold(); backpressure=1;instant_read=0;instant_write=0;
            load_word('h64,1);
            @(negedge clk);dv=1;dw=1;da='h64;wd=32'h89abcdef;ws=15;
            @(posedge clk);while (!dr) @(posedge clk);
            @(negedge clk);dv=0;da='hfc0;wd=32'hdeadbeef;ws=0;
            waited=0;
            if (phase==1) begin
                while (!writing) begin @(negedge clk);waited=waited+1;
                    if (waited>100) $fatal(1,"RESULT: FAIL no AW acceptance"); end
                if (wrdy) $fatal(1,"RESULT: FAIL reset WDATA missed wait window");
            end
            if (phase==2) begin
                while (!wrdy) begin @(negedge clk);waited=waited+1;
                    if (waited>100) $fatal(1,"RESULT: FAIL no write completion"); end
                @(posedge clk);@(negedge clk);
                if (!dsv) $fatal(1,"RESULT: FAIL missing post-write response");
            end
            resetn=0;init_done=0;iv=0;dv=0;
            repeat(2) @(negedge clk);
            resetn=1;init_done=1;
            load_word('h64,1);
            tests=tests+1;
        end
    endtask

    task automatic lose_initialization;
        integer waited;
        begin
            cold();backpressure=1;instant_read=0;instant_write=0;
            load_word('h124,1);
            @(negedge clk);dv=1;dw=1;da='h124;wd=32'h12345678;ws=15;
            @(posedge clk);while (!dr) @(posedge clk);
            @(negedge clk);dv=0;da='hfe0;wd=0;ws=0;init_done=0;
            waited=0;
            while (!dsv) begin @(negedge clk);waited=waited+1;
                if (waited>100) $fatal(1,"RESULT: FAIL init-loss store timeout"); end
            if (dse || ddata!==0 || dr || ir)
                $fatal(1,"RESULT: FAIL init-loss store response/ready");
            @(negedge clk);init_done=1;tests=tests+1;
            load_word('h124,1);load_word('h128,0);
        end
    endtask

    integer mask,mode;
    initial begin : run_tests
        for (integer row=0;row<128;row=row+1)
            for (integer word=0;word<8;word=word+1)
                memory[row][word*32+:32]=32'h10203040 ^ (row<<12) ^ (word*32'h01010101);
        repeat(4) @(negedge clk);resetn=1;init_done=1;

        // New byte-enabled full fills must preserve all eight words of all rows.
        for (k=0;k<64;k=k+1)
            for (lane=0;lane<8;lane=lane+1) load_word(k*32+lane*4,lane==0 ? 1 : 0);
        conservation();$display("CHECK: full_fill_byte_enable PASS");

        // All 16 byte masks, eight 32-bit slots: SB, SH, SW, zero and mixed masks.
        for (lane=0;lane<8;lane=lane+1)
            for (mask=0;mask<16;mask=mask+1) begin
                store_word(lane*4,32'h98765432 ^ (lane<<16) ^ mask,mask[3:0]);
                load_word(lane*4,0);
                load_word(((lane+1)%8)*4,0);
            end
        conservation();$display("CHECK: masked_hit_all_lanes PASS");

        cold();load_word(0,1);store_word('h800,32'habcdef01,15);
        load_word(0,0);load_word('h800,1);store_word(0,32'h13579bdf,15);
        load_word('h800,0);load_word(0,1);load_word(4,0);
        conservation();$display("CHECK: no_allocate_tag_conflict PASS");

        for (mode=0;mode<4;mode=mode+1) begin
            cold();backpressure=(mode&2)!=0;instant_write=(mode&1)!=0;instant_read=(mode&1)!=0;
            load_word('h420+mode*4,1);
            store_word('h420+mode*4,32'hfedcba98 ^ mode,15);
            load_word('h420+mode*4,0);load_word('h43c,0);
        end
        conservation();$display("CHECK: write_completion_and_backpressure PASS");

        backpressure=1;instant_read=0;instant_write=0;cold();
        fetch(0,1);load_word(0,1);store_word(0,32'ha5a55a5a,3);
        load_word(0,0);fetch(0,1);fetch(4,0);
        store_word('hf00,32'h2468ace0,15);load_word(0,0);fetch(0,0);
        store_word(0,0,0);load_word(0,0);fetch(0,1);
        conservation();$display("CHECK: instruction_invalidation_and_zero_mask PASS");

        for (mode=0;mode<3;mode=mode+1) reset_write(mode);
        conservation();$display("CHECK: reset_before_aw_during_w_after_write PASS");

        lose_initialization();conservation();$display("CHECK: initialization_loss PASS");
        if (tests!=945 || checked_fill_writes==0 || checked_hit_writes==0)
            $fatal(1,"RESULT: FAIL test/DRM write coverage tests=%0d",tests);
        $display("RESULT: PASS data_write_hit_x32 tests=%0d fills=%0d updates=%0d",tests,checked_fill_writes,checked_hit_writes);
        $finish;
    end
    initial begin #3000000;$fatal(1,"RESULT: FAIL testbench watchdog");end
endmodule
