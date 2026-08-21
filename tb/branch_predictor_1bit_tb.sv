`timescale 1ns / 1ps

// ============================================================================
// Module: branch_predictor_1bit_tb
// Description: Self-contained testbench for 1-bit dynamic branch predictor.
// Workload trace: T T T T N T T T N T (T=1, N=0)
// ============================================================================

module branch_predictor_1bit_tb;

    // Testbench signals
    logic clk;
    logic reset;
    logic actual_taken;
    logic prediction;

    // Instantiate Device Under Test (DUT)
    branch_predictor_1bit dut (
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

    // Test sequence parameter and storage
    localparam int NUM_BRANCHES = 10;
    logic workload [0:NUM_BRANCHES-1];

    // Tracking counters
    int total_branches        = 0;
    int correct_predictions   = 0;
    int incorrect_predictions = 0;
    real accuracy             = 0.0;

    initial begin
        // Populate workload array: T T T T N T T T N T
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

        // Verify initialization to Taken (1'b1 / 'T') after reset
        if (prediction !== 1'b1) begin
            $display("[ERROR] Predictor did not initialize to Taken (T) on reset!");
        end else begin
            $display("[INIT] Reset verified: Predictor state initialized to Taken (T).");
        end
        $display("----------------------------------------------------------------");

        // Iterate through workload trace
        for (int i = 0; i < NUM_BRANCHES; i++) begin
            // Setup actual_taken on falling clock edge to guarantee stable setup time before rising edge
            @(negedge clk);
            actual_taken = workload[i];

            // Sample and evaluate prediction BEFORE the DUT learns current outcome on posedge clk
            total_branches++;
            if (prediction == workload[i]) begin
                correct_predictions++;
                $display("Branch %2d | Prediction: %s | Actual: %s | Result: CORRECT",
                         i + 1, (prediction ? "T" : "N"), (workload[i] ? "T" : "N"));
            end else begin
                incorrect_predictions++;
                $display("Branch %2d | Prediction: %s | Actual: %s | Result: INCORRECT",
                         i + 1, (prediction ? "T" : "N"), (workload[i] ? "T" : "N"));
            end

            // Wait for posedge clk: DUT updates stored state to actual_taken
            @(posedge clk);
        end

        // Calculate accuracy metric dynamically from testbench counter variables
        if (total_branches > 0) begin
            accuracy = (real'(correct_predictions) / real'(total_branches)) * 100.0;
        end

        // Summary report
        $display("----------------------------------------------------------------");
        $display("Total Branches        = %0d", total_branches);
        $display("Correct Predictions   = %0d", correct_predictions);
        $display("Incorrect Predictions = %0d", incorrect_predictions);
        $display("Prediction Accuracy   = %0.2f%%", accuracy);
        $display("----------------------------------------------------------------");

        $finish;
    end

endmodule
