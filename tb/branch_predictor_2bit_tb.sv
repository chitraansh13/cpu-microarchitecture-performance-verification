`timescale 1ns / 1ps

// ============================================================================
// Module: branch_predictor_2bit_tb
// Description: Testbench for 2-bit saturating counter branch predictor.
// Supports both default trace mode and file-driven regression mode (+WORKLOAD=<path>).
// Outputs machine-readable lines formatted as: REG_BRANCH,<branch_num>,<pred>,<actual>
// ============================================================================

module branch_predictor_2bit_tb;

    // Testbench signals
    logic clk;
    logic reset;
    logic actual_taken;
    logic prediction;

    // Instantiate Device Under Test (DUT)
    branch_predictor_2bit dut (
        .clk          (clk),
        .reset        (reset),
        .actual_taken (actual_taken),
        .prediction   (prediction)
    );

    // Clock generation: 10ns period (50MHz)
    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    // Default test workload trace: T T T T N T T T N T
    localparam int NUM_BRANCHES = 10;
    logic workload [0:NUM_BRANCHES-1];

    // Tracking counters
    int total_branches        = 0;
    int correct_predictions   = 0;
    int incorrect_predictions = 0;
    real accuracy             = 0.0;

    // Workload file I/O variables
    string workload_filename;
    int file_fd;
    int file_val;

    initial begin
        // Populate default workload trace
        workload[0] = 1'b1; // T
        workload[1] = 1'b1; // T
        workload[2] = 1'b1; // T
        workload[3] = 1'b1; // T
        workload[4] = 1'b0; // N
        workload[5] = 1'b1; // T
        workload[6] = 1'b1; // T
        workload[7] = 1'b1; // T
        workload[8] = 1'b0; // N
        workload[9] = 1'b1; // T

        // Initialize inputs
        reset        = 1'b1;
        actual_taken = 1'b0;

        // Apply reset for 2 clock cycles
        #10;
        @(posedge clk);
        #1;
        reset = 1'b0;

        // Verify initialization to Strongly Taken (2'b11) after reset
        if (dut.state !== 2'b11) begin
            $display("[ERROR] Predictor did not initialize to Strongly Taken (11) on reset!");
        end else begin
            $display("[INIT] Reset verified: Predictor state initialized to Strongly Taken (11).");
        end
        $display("-------------------------------------------------------------------------");

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
                actual_taken = (file_val != 0) ? 1'b1 : 1'b0;

                total_branches++;
                // Machine-readable regression output
                $display("REG_BRANCH,%0d,%0d,%0d", total_branches, prediction, actual_taken);

                if (prediction == actual_taken) begin
                    correct_predictions++;
                    $display("Branch %4d | State: %b | Prediction: %s | Actual: %s | Result: CORRECT",
                             total_branches, dut.state, (prediction ? "T" : "N"), (actual_taken ? "T" : "N"));
                end else begin
                    incorrect_predictions++;
                    $display("Branch %4d | State: %b | Prediction: %s | Actual: %s | Result: INCORRECT",
                             total_branches, dut.state, (prediction ? "T" : "N"), (actual_taken ? "T" : "N"));
                end

                @(posedge clk);
            end

            $fclose(file_fd);
        end else begin
            // Default 10-branch trace mode
            for (int i = 0; i < NUM_BRANCHES; i++) begin
                @(negedge clk);
                actual_taken = workload[i];

                total_branches++;
                // Machine-readable regression output
                $display("REG_BRANCH,%0d,%0d,%0d", total_branches, prediction, actual_taken);

                if (prediction == workload[i]) begin
                    correct_predictions++;
                    $display("Branch %2d | State: %b | Prediction: %s | Actual: %s | Result: CORRECT",
                             i + 1, dut.state, (prediction ? "T" : "N"), (workload[i] ? "T" : "N"));
                end else begin
                    incorrect_predictions++;
                    $display("Branch %2d | State: %b | Prediction: %s | Actual: %s | Result: INCORRECT",
                             i + 1, dut.state, (prediction ? "T" : "N"), (workload[i] ? "T" : "N"));
                end

                @(posedge clk);
            end
        end

        // Calculate summary metrics
        if (total_branches > 0) begin
            accuracy = (real'(correct_predictions) / real'(total_branches)) * 100.0;
        end

        // Summary report
        $display("-------------------------------------------------------------------------");
        $display("Total Branches        = %0d", total_branches);
        $display("Correct Predictions   = %0d", correct_predictions);
        $display("Incorrect Predictions = %0d", incorrect_predictions);
        $display("Prediction Accuracy   = %0.2f%%", accuracy);
        $display("-------------------------------------------------------------------------");

        $finish;
    end

endmodule
