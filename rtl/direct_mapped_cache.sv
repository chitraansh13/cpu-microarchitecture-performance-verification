`timescale 1ns / 1ps

// ============================================================================
// Module: direct_mapped_cache
// Description: Simplified direct-mapped cache (Tag & Valid storage only).
// Architecture:
//   - 16-bit byte address space
//   - 4 cache lines (2 index bits)
//   - 4-byte block size (2 offset bits)
//   - 12 tag bits
// Address Breakdown:
//   [15:4] = Tag (12 bits)
//   [3:2]  = Index (2 bits)
//   [1:0]  = Offset (2 bits)
// ============================================================================

module direct_mapped_cache (
    input  logic        clk,
    input  logic        reset,
    input  logic        access_valid,
    input  logic [15:0] address,
    output logic        hit
);

    localparam int NUM_LINES = 4;
    localparam int TAG_BITS  = 12;

    // Cache storage registers
    logic [NUM_LINES-1:0] valid;
    logic [TAG_BITS-1:0]  tag [0:NUM_LINES-1];

    // Field extraction from 16-bit address
    logic [1:0]          index;
    logic [TAG_BITS-1:0] incoming_tag;

    assign index        = address[3:2];
    assign incoming_tag = address[15:4];

    // Combinational hit evaluation based on current valid and tag state
    assign hit = access_valid && valid[index] && (tag[index] == incoming_tag);

    // Sequential cache state updates
    always_ff @(posedge clk) begin
        if (reset) begin
            // Invalidate all cache lines on reset
            valid <= '0;
        end else if (access_valid) begin
            // On access, allocate/update line valid bit and tag
            valid[index] <= 1'b1;
            tag[index]   <= incoming_tag;
        end
    end

endmodule
