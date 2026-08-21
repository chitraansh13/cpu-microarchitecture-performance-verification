`timescale 1ns / 1ps

// ============================================================================
// Module: branch_predictor_1bit
// Description: Synchronous 1-bit dynamic branch predictor.
//              Initializes to Taken (1'b1) on reset.
//              Updates stored state to actual_taken on each rising clock edge.
// ============================================================================

module branch_predictor_1bit (
    input  logic clk,
    input  logic reset,
    input  logic actual_taken,
    output logic prediction
);

    // Internal 1-bit predictor state register
    // 1'b1 = Predict Taken (T)
    // 1'b0 = Predict Not Taken (N)
    logic state;

    always_ff @(posedge clk) begin
        if (reset) begin
            state <= 1'b1; // Default state on reset: Taken (1'b1)
        end else begin
            state <= actual_taken; // Learn previous branch outcome
        end
    end

    // Prediction output reflects current stored predictor state
    assign prediction = state;

endmodule
