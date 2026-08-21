`timescale 1ns / 1ps

// ============================================================================
// Module: cache_tb
// Description: Testbench for direct_mapped_cache.
// Supports both default trace mode and file-driven regression mode (+WORKLOAD=<path>).
// Outputs machine-readable lines formatted as: REG_CACHE,<access_num>,<address>,<hit>
// ============================================================================

module cache_tb;

    // Testbench signals
    logic        clk;
    logic        reset;
    logic        access_valid;
    logic [15:0] address;
    logic        hit;

    // Instantiate Device Under Test (DUT)
    direct_mapped_cache dut (
        .clk          (clk),
        .reset        (reset),
        .access_valid (access_valid),
        .address      (address),
        .hit          (hit)
    );

    // Clock generation: 10ns period (50MHz)
    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    // Default test workload trace (decimal byte addresses)
    localparam int NUM_ACCESSES = 7;
    logic [15:0] workload [0:NUM_ACCESSES-1];

    // Tracking counters
    int total_accesses = 0;
    int hits           = 0;
    int misses         = 0;
    real hit_rate      = 0.0;
    real miss_rate     = 0.0;

    // Workload file I/O variables
    string workload_filename;
    int file_fd;
    int file_val;

    initial begin
        // Populate default workload array
        workload[0] = 16'd0;
        workload[1] = 16'd0;
        workload[2] = 16'd4;
        workload[3] = 16'd4;
        workload[4] = 16'd16;
        workload[5] = 16'd0;
        workload[6] = 16'd0;

        // Initialize inputs
        reset        = 1'b1;
        access_valid = 1'b0;
        address      = 16'd0;

        // Apply reset across clock edge
        #10;
        @(posedge clk);
        #1;
        reset = 1'b0;

        // Verify initial reset invalidates all 4 cache lines
        if (dut.valid !== 4'b0000) begin
            $display("[ERROR] Initial reset failed: valid bits not cleared! valid = %b", dut.valid);
        end else begin
            $display("[INIT] Reset verified: All 4 cache line valid bits cleared (valid = %b).", dut.valid);
        end
        $display("--------------------------------------------------------------------------------");

        // Check for +WORKLOAD=<path> plusarg
        if ($value$plusargs("WORKLOAD=%s", workload_filename)) begin
            $display("[WORKLOAD] Executing file-driven regression mode: %s", workload_filename);
            file_fd = $fopen(workload_filename, "r");
            if (file_fd == 0) begin
                $display("[ERROR] Failed to open workload file: %s", workload_filename);
                $finish;
            end

            while ($fscanf(file_fd, "%d\n", file_val) == 1) begin
                @(negedge clk);
                address      = file_val[15:0];
                access_valid = 1'b1;

                // Settling delay for combinational logic propagation
                #1;

                total_accesses++;
                // Machine-readable regression output (1 = HIT, 0 = MISS)
                $display("REG_CACHE,%0d,%0d,%0d", total_accesses, address, (hit ? 1 : 0));

                if (hit) begin
                    hits++;
                    $display("Access %4d | Address: %5d | Index: %0d | Tag: %0d | Result: HIT  | Line State [Valid: %b, Tag: %0d]",
                             total_accesses, address, address[3:2], address[15:4],
                             dut.valid[address[3:2]], dut.tag[address[3:2]]);
                end else begin
                    misses++;
                    $display("Access %4d | Address: %5d | Index: %0d | Tag: %0d | Result: MISS | Line State [Valid: %b, Tag: %0d]",
                             total_accesses, address, address[3:2], address[15:4],
                             dut.valid[address[3:2]], dut.tag[address[3:2]]);
                end

                @(posedge clk);
                #1;
            end

            @(negedge clk);
            access_valid = 1'b0;

            $fclose(file_fd);
        end else begin
            // Default 7-access workload trace
            for (int i = 0; i < NUM_ACCESSES; i++) begin
                @(negedge clk);
                address      = workload[i];
                access_valid = 1'b1;

                #1;

                total_accesses++;
                // Machine-readable regression output (1 = HIT, 0 = MISS)
                $display("REG_CACHE,%0d,%0d,%0d", total_accesses, address, (hit ? 1 : 0));

                if (hit) begin
                    hits++;
                    $display("Access %0d | Address: %5d | Index: %0d | Tag: %0d | Result: HIT  | Line State [Valid: %b, Tag: %0d]",
                             i + 1, workload[i], workload[i][3:2], workload[i][15:4],
                             dut.valid[workload[i][3:2]], dut.tag[workload[i][3:2]]);
                end else begin
                    misses++;
                    $display("Access %0d | Address: %5d | Index: %0d | Tag: %0d | Result: MISS | Line State [Valid: %b, Tag: %0d]",
                             i + 1, workload[i], workload[i][3:2], workload[i][15:4],
                             dut.valid[workload[i][3:2]], dut.tag[workload[i][3:2]]);
                end

                @(posedge clk);
                #1;
            end

            @(negedge clk);
            access_valid = 1'b0;
        end

        // Calculate summary metrics
        if (total_accesses > 0) begin
            hit_rate  = (real'(hits) / real'(total_accesses)) * 100.0;
            miss_rate = (real'(misses) / real'(total_accesses)) * 100.0;
        end

        // Summary metric report
        $display("--------------------------------------------------------------------------------");
        $display("Total Accesses = %0d", total_accesses);
        $display("Hits           = %0d", hits);
        $display("Misses         = %0d", misses);
        $display("Hit Rate       = %0.2f%%", hit_rate);
        $display("Miss Rate      = %0.2f%%", miss_rate);
        $display("--------------------------------------------------------------------------------");

        // Post-workload Reset Invalidation Verification (separate from metrics)
        if (!$value$plusargs("WORKLOAD=%s", workload_filename)) begin
            $display("[POST-RESET] Testing re-invalidation via reset...");
            @(negedge clk);
            reset = 1'b1;
            @(posedge clk);
            #1;
            reset = 1'b0;

            if (dut.valid !== 4'b0000) begin
                $display("[ERROR] Post-test reset failed: valid bits not cleared! valid = %b", dut.valid);
            end else begin
                $display("[POST-RESET] Verified: All valid bits cleared after post-test reset (valid = %b).", dut.valid);
            end

            @(negedge clk);
            address      = 16'd0;
            access_valid = 1'b1;
            #1;

            if (!hit) begin
                $display("[POST-RESET] Verified: Address 0 correctly MISSES after reset invalidation.");
            end else begin
                $display("[ERROR] Post-reset failure: Address 0 hit unexpectedly after reset!");
            end

            @(posedge clk);
            #1;
            @(negedge clk);
            access_valid = 1'b0;
        end

        $finish;
    end

endmodule
