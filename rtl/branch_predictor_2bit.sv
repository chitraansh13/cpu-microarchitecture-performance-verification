`timescale 1ns / 1ps

// ============================================================================
// Module: branch_predictor_2bit
// Description: Synchronous 2-bit saturating counter dynamic branch predictor.
//
// States:
//   2'b00: Strongly Not Taken (SN) -> Predict 0 (Not Taken)
//   2'b01: Weakly Not Taken   (WN) -> Predict 0 (Not Taken)
//   2'b10: Weakly Taken       (WT) -> Predict 1 (Taken)
//   2'b11: Strongly Taken     (ST) -> Predict 1 (Taken)
//
// Reset State: 2'b11 (Strongly Taken)
// ============================================================================

module branch_predictor_2bit (
    input  logic clk,
    input  logic reset,
    input  logic actual_taken,
    output logic prediction
);

    // 2-bit predictor state register
    logic [1:0] state;

    // State encoding constants
    localparam logic [1:0] STRONGLY_NOT_TAKEN = 2'b00;
    localparam logic [1:0] WEAKLY_NOT_TAKEN   = 2'b01;
    localparam logic [1:0] WEAKLY_TAKEN       = 2'b10;
    localparam logic [1:0] STRONGLY_TAKEN     = 2'b11;

    always_ff @(posedge clk) begin
        if (reset) begin
            state <= STRONGLY_TAKEN; // Initialize to 2'b11 (Strongly Taken) on reset
        end else begin
            if (actual_taken) begin
                // Saturating increment: 00->01, 01->10, 10->11, 11->11
                if (state != STRONGLY_TAKEN) begin
                    state <= state + 1'b1;
                end
            end else begin
                // Saturating decrement: 11->10, 10->01, 01->00, 00->00
                if (state != STRONGLY_NOT_TAKEN) begin
                    state <= state - 1'b1;
                end
            end
        end
    end

    // Prediction output: MSB of 2-bit state (10/11 -> 1 (T), 00/01 -> 0 (N))
    assign prediction = state[1];

endmodule
