#!/usr/bin/env python3
"""
Python Reference Models for CPU Microarchitecture Performance Verification.

Provides golden software reference models for:
1. 1-Bit Dynamic Branch Predictor
2. 2-Bit Saturating Counter Branch Predictor
3. Simplified Direct-Mapped Cache

These software models serve as independent functional specification targets
for verifying SystemVerilog hardware RTL outputs in regression testing.

Standard Library Only.
"""

from typing import Dict, List, Any


# ============================================================================
# 1. 1-Bit Dynamic Branch Predictor Reference Model
# ============================================================================

class OneBitBranchPredictor:
    """
    Golden software reference model for a 1-bit dynamic branch predictor.
    
    Behavior:
    - Internal state is 1 bit: 1 = Taken (T), 0 = Not Taken (N).
    - Default reset state: 1 (Taken).
    - Prediction is the current state before applying the branch outcome update.
    - Update sets state = actual_taken.
    """

    def __init__(self) -> None:
        self.state: int = 1  # Default state: Taken

    def reset(self) -> None:
        """Resets predictor state to Taken (1)."""
        self.state = 1

    def predict(self) -> int:
        """Returns the current branch prediction (1 for Taken, 0 for Not Taken)."""
        return self.state

    def update(self, actual_taken: int) -> None:
        """Updates predictor state to actual_taken."""
        if actual_taken not in (0, 1):
            raise ValueError(f"actual_taken must be 0 or 1, got {actual_taken}")
        self.state = actual_taken

    def process(self, actual_taken: int) -> int:
        """
        Processes a branch: returns the prediction BEFORE updating state.
        
        Order of Operations:
        1. Read current prediction from state
        2. Update state = actual_taken
        3. Return prediction
        """
        prediction = self.predict()
        self.update(actual_taken)
        return prediction


# ============================================================================
# 2. 2-Bit Saturating Branch Predictor Reference Model
# ============================================================================

class TwoBitBranchPredictor:
    """
    Golden software reference model for a 2-bit saturating counter branch predictor.
    
    States:
    - 0 (00): Strongly Not Taken (SN) -> Predict 0
    - 1 (01): Weakly Not Taken   (WN) -> Predict 0
    - 2 (10): Weakly Taken       (WT) -> Predict 1
    - 3 (11): Strongly Taken     (ST) -> Predict 1
    
    Default reset state: 3 (Strongly Taken).
    """

    STRONGLY_NOT_TAKEN = 0
    WEAKLY_NOT_TAKEN   = 1
    WEAKLY_TAKEN       = 2
    STRONGLY_TAKEN     = 3

    def __init__(self) -> None:
        self.state: int = self.STRONGLY_TAKEN

    def reset(self) -> None:
        """Resets predictor state to Strongly Taken (3 / 2'b11)."""
        self.state = self.STRONGLY_TAKEN

    def predict(self) -> int:
        """Returns prediction: 1 (Taken) if state >= 2 else 0 (Not Taken)."""
        return 1 if self.state >= 2 else 0

    def update(self, actual_taken: int) -> None:
        """Updates 2-bit state using saturating increment/decrement."""
        if actual_taken not in (0, 1):
            raise ValueError(f"actual_taken must be 0 or 1, got {actual_taken}")
        
        if actual_taken == 1:
            self.state = min(self.state + 1, self.STRONGLY_TAKEN)
        else:
            self.state = max(self.state - 1, self.STRONGLY_NOT_TAKEN)

    def process(self, actual_taken: int) -> int:
        """
        Processes a branch: returns prediction BEFORE updating 2-bit state.
        """
        prediction = self.predict()
        self.update(actual_taken)
        return prediction


# ============================================================================
# 3. Direct-Mapped Cache Reference Model
# ============================================================================

class DirectMappedCache:
    """
    Golden software reference model for a simplified direct-mapped cache.
    
    Configuration:
    - Address space: 16 bits (0 to 65535)
    - Cache lines:   4 lines (2 index bits)
    - Block size:    4 bytes (2 offset bits)
    - Tag width:     12 bits
    
    Address Breakdown:
    - Offset: address[1:0] (bits 0..1)
    - Index:  address[3:2] (bits 2..3)
    - Tag:    address[15:4] (bits 4..15)
    """

    NUM_LINES = 4

    def __init__(self) -> None:
        self.valid: List[bool] = [False] * self.NUM_LINES
        self.tag: List[int] = [0] * self.NUM_LINES

    def reset(self) -> None:
        """Invalidates all cache lines."""
        self.valid = [False] * self.NUM_LINES
        self.tag = [0] * self.NUM_LINES

    def access(self, address: int) -> bool:
        """
        Simulates a cache access for the given 16-bit address.
        
        Returns:
            bool: True if hit, False if miss.
        """
        if not isinstance(address, int):
            raise ValueError(f"Address {address} must be an integer.")
        if not (0 <= address <= 65535):
            raise ValueError(f"Address {address} outside 16-bit space [0, 65535].")

        # Decompose address fields
        index = (address >> 2) & 0b11
        incoming_tag = address >> 4

        # Check hit condition BEFORE updating line state
        is_hit = self.valid[index] and (self.tag[index] == incoming_tag)

        # Update cache line state (allocate/update on miss or hit)
        self.valid[index] = True
        self.tag[index] = incoming_tag

        return is_hit


# ============================================================================
# 4. Trace Execution Helper Functions
# ============================================================================

def run_branch_trace(model: Any, outcomes: List[int]) -> Dict[str, Any]:
    """
    Runs a list of branch outcomes through a branch predictor reference model.
    
    Returns a dictionary with per-branch event records and summary statistics.
    """
    events = []
    correct_count = 0

    for i, actual in enumerate(outcomes):
        prediction = model.process(actual)
        is_correct = (prediction == actual)
        if is_correct:
            correct_count += 1

        events.append({
            "branch_num": i + 1,
            "actual": actual,
            "prediction": prediction,
            "correct": is_correct
        })

    total = len(outcomes)
    incorrect_count = total - correct_count
    accuracy = (correct_count / total * 100.0) if total > 0 else 0.0

    return {
        "total": total,
        "correct": correct_count,
        "incorrect": incorrect_count,
        "accuracy": accuracy,
        "events": events
    }


def run_cache_trace(cache: DirectMappedCache, addresses: List[int]) -> Dict[str, Any]:
    """
    Runs a list of memory addresses through a cache reference model.
    
    Returns a dictionary with per-access event records and summary statistics.
    """
    events = []
    hit_count = 0

    for i, addr in enumerate(addresses):
        is_hit = cache.access(addr)
        if is_hit:
            hit_count += 1

        index = (addr >> 2) & 0b11
        tag = addr >> 4

        events.append({
            "access_num": i + 1,
            "address": addr,
            "index": index,
            "tag": tag,
            "hit": is_hit
        })

    total = len(addresses)
    miss_count = total - hit_count
    hit_rate = (hit_count / total * 100.0) if total > 0 else 0.0
    miss_rate = (miss_count / total * 100.0) if total > 0 else 0.0

    return {
        "total": total,
        "hits": hit_count,
        "misses": miss_count,
        "hit_rate": hit_rate,
        "miss_rate": miss_rate,
        "events": events
    }


# ============================================================================
# Sanity Demo / Self-Test
# ============================================================================

if __name__ == "__main__":
    print("=== Reference Models Sanity Demonstration ===")

    # 1-Bit & 2-Bit Branch Predictor Baseline Trace
    branch_trace = [1, 1, 1, 1, 0, 1, 1, 1, 0, 1]  # T T T T N T T T N T

    model_1bit = OneBitBranchPredictor()
    res_1bit = run_branch_trace(model_1bit, branch_trace)

    model_2bit = TwoBitBranchPredictor()
    res_2bit = run_branch_trace(model_2bit, branch_trace)

    print(f"\n1-Bit Predictor Results (Trace: T T T T N T T T N T):")
    print(f"  Accuracy: {res_1bit['accuracy']:.2f}% ({res_1bit['correct']}/{res_1bit['total']} correct)")

    print(f"\n2-Bit Predictor Results (Trace: T T T T N T T T N T):")
    print(f"  Accuracy: {res_2bit['accuracy']:.2f}% ({res_2bit['correct']}/{res_2bit['total']} correct)")

    # Direct-Mapped Cache Baseline Trace
    cache_trace = [0, 0, 4, 4, 16, 0, 0]

    cache_model = DirectMappedCache()
    res_cache = run_cache_trace(cache_model, cache_trace)

    hit_seq = ["HIT" if e["hit"] else "MISS" for e in res_cache["events"]]
    print(f"\nDirect-Mapped Cache Results (Trace: 0, 0, 4, 4, 16, 0, 0):")
    print(f"  Hit Sequence: {' '.join(hit_seq)}")
    print(f"  Hit Rate:     {res_cache['hit_rate']:.2f}% ({res_cache['hits']}/{res_cache['total']} hits)")
