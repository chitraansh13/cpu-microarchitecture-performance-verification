#!/usr/bin/env python3
"""
Workload Generator for CPU Microarchitecture Performance Verification.

Generates synthetic, reproducible branch-outcome and memory-address workloads
for evaluating branch predictor accuracy and cache hit/miss rates.

Standard Library Only.
"""

import argparse
import random
from pathlib import Path
from typing import List, Optional

DEFAULT_SEED = 42
DEFAULT_BRANCH_COUNT = 1000
DEFAULT_MEMORY_COUNT = 1000


# ============================================================================
# Validation Utilities
# ============================================================================

def validate_branch_workload(workload: List[int], expected_count: int) -> None:
    """Validates that a branch workload contains only 0s and 1s and has correct count."""
    if len(workload) != expected_count:
        raise ValueError(f"Workload length {len(workload)} does not match expected count {expected_count}")
    for item in workload:
        if item not in (0, 1):
            raise ValueError(f"Invalid branch outcome {item}; must be 0 or 1.")


def validate_memory_workload(workload: List[int], expected_count: int) -> None:
    """Validates that a memory workload contains 4-byte aligned 16-bit addresses."""
    if len(workload) != expected_count:
        raise ValueError(f"Workload length {len(workload)} does not match expected count {expected_count}")
    for addr in workload:
        if not isinstance(addr, int):
            raise ValueError(f"Address {addr} must be an integer.")
        if addr < 0 or addr > 65535:
            raise ValueError(f"Address {addr} outside 16-bit address space [0, 65535].")
        if addr % 4 != 0:
            raise ValueError(f"Address {addr} is not 4-byte aligned.")


# ============================================================================
# Branch Workload Generators
# ============================================================================

def generate_mostly_taken(
    count: int = DEFAULT_BRANCH_COUNT,
    taken_ratio: float = 0.9,
    rng: Optional[random.Random] = None
) -> List[int]:
    """Generates a branch workload with high probability of Taken outcomes (~90% Taken)."""
    if count <= 0:
        raise ValueError("Count must be positive.")
    if not (0.0 <= taken_ratio <= 1.0):
        raise ValueError("taken_ratio must be between 0.0 and 1.0.")
    if rng is None:
        rng = random.Random(DEFAULT_SEED)

    workload = [1 if rng.random() < taken_ratio else 0 for _ in range(count)]
    validate_branch_workload(workload, count)
    return workload


def generate_mostly_not_taken(
    count: int = DEFAULT_BRANCH_COUNT,
    not_taken_ratio: float = 0.9,
    rng: Optional[random.Random] = None
) -> List[int]:
    """Generates a branch workload with high probability of Not Taken outcomes (~90% Not Taken)."""
    if count <= 0:
        raise ValueError("Count must be positive.")
    if not (0.0 <= not_taken_ratio <= 1.0):
        raise ValueError("not_taken_ratio must be between 0.0 and 1.0.")
    if rng is None:
        rng = random.Random(DEFAULT_SEED)

    workload = [0 if rng.random() < not_taken_ratio else 1 for _ in range(count)]
    validate_branch_workload(workload, count)
    return workload


def generate_alternating(count: int = DEFAULT_BRANCH_COUNT) -> List[int]:
    """Generates a deterministic alternating pattern: 1, 0, 1, 0, 1, 0..."""
    if count <= 0:
        raise ValueError("Count must be positive.")

    workload = [1 if i % 2 == 0 else 0 for i in range(count)]
    validate_branch_workload(workload, count)
    return workload


def generate_loop_pattern(
    count: int = DEFAULT_BRANCH_COUNT,
    taken_per_loop: int = 5
) -> List[int]:
    """Generates a repeating loop pattern: N Taken branches followed by 1 Not Taken branch."""
    if count <= 0:
        raise ValueError("Count must be positive.")
    if taken_per_loop < 1:
        raise ValueError("taken_per_loop must be at least 1.")

    pattern_len = taken_per_loop + 1
    workload = []
    for i in range(count):
        pos_in_loop = i % pattern_len
        workload.append(1 if pos_in_loop < taken_per_loop else 0)

    validate_branch_workload(workload, count)
    return workload


def generate_random_branches(
    count: int = DEFAULT_BRANCH_COUNT,
    rng: Optional[random.Random] = None
) -> List[int]:
    """Generates a random 50/50 branch outcome sequence using seeded randomness."""
    if count <= 0:
        raise ValueError("Count must be positive.")
    if rng is None:
        rng = random.Random(DEFAULT_SEED)

    workload = [rng.randint(0, 1) for _ in range(count)]
    validate_branch_workload(workload, count)
    return workload


# ============================================================================
# Memory Workload Generators
# ============================================================================

def generate_high_locality(
    count: int = DEFAULT_MEMORY_COUNT,
    working_set: Optional[List[int]] = None,
    rng: Optional[random.Random] = None
) -> List[int]:
    """Generates repeated accesses to a small working set of addresses exhibiting high spatial/temporal locality."""
    if count <= 0:
        raise ValueError("Count must be positive.")
    if working_set is None:
        working_set = [0, 4, 8, 12]
    if rng is None:
        rng = random.Random(DEFAULT_SEED)

    for addr in working_set:
        if addr % 4 != 0 or addr < 0 or addr > 65535:
            raise ValueError(f"Working set address {addr} is invalid.")

    workload = [rng.choice(working_set) for _ in range(count)]
    validate_memory_workload(workload, count)
    return workload


def generate_sequential(
    count: int = DEFAULT_MEMORY_COUNT,
    start: int = 0,
    stride: int = 4
) -> List[int]:
    """Generates a sequential stream of 4-byte aligned memory addresses."""
    if count <= 0:
        raise ValueError("Count must be positive.")
    if start % 4 != 0 or start < 0 or start > 65535:
        raise ValueError("Start address must be 4-byte aligned within [0, 65535].")
    if stride % 4 != 0 or stride <= 0:
        raise ValueError("Stride must be a positive multiple of 4.")

    workload = []
    curr = start
    for _ in range(count):
        workload.append(curr)
        curr = (curr + stride) % 65536
        curr = (curr // 4) * 4

    validate_memory_workload(workload, count)
    return workload


def generate_random_memory(
    count: int = DEFAULT_MEMORY_COUNT,
    min_addr: int = 0,
    max_addr: int = 65532,
    rng: Optional[random.Random] = None
) -> List[int]:
    """Generates random 4-byte-aligned addresses within 16-bit address bounds."""
    if count <= 0:
        raise ValueError("Count must be positive.")
    if min_addr < 0 or max_addr > 65532 or min_addr > max_addr:
        raise ValueError("Invalid address bounds.")
    if rng is None:
        rng = random.Random(DEFAULT_SEED)

    min_word = min_addr // 4
    max_word = max_addr // 4

    workload = [rng.randint(min_word, max_word) * 4 for _ in range(count)]
    validate_memory_workload(workload, count)
    return workload


def generate_conflict_workload(
    count: int = DEFAULT_MEMORY_COUNT,
    base_addr: int = 0,
    stride: int = 16,
    num_tags: int = 4
) -> List[int]:
    """
    Generates addresses that map to the same direct-mapped cache index.
    
    Since index = address[3:2], addresses separated by multiples of 16 (2^4) bytes
    share index bits while carrying different tag bits [15:4], inducing conflict misses.
    """
    if count <= 0:
        raise ValueError("Count must be positive.")
    if base_addr % 4 != 0 or base_addr < 0 or base_addr > 65535:
        raise ValueError("base_addr must be 4-byte aligned within 16-bit space.")
    if stride % 16 != 0 or stride <= 0:
        raise ValueError("stride must be a positive multiple of 16 to guarantee index aliasing.")

    conflicting_addresses = [
        (base_addr + i * stride) % 65536 for i in range(num_tags)
    ]

    workload = [conflicting_addresses[i % num_tags] for i in range(count)]
    validate_memory_workload(workload, count)
    return workload


# ============================================================================
# File Output Utilities
# ============================================================================

def save_workload(file_path: Path, workload: List[int]) -> None:
    """Saves a workload list to a file, one integer per line."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        for item in workload:
            f.write(f"{item}\n")


# ============================================================================
# Main Execution / CLI
# ============================================================================

def generate_all_workloads(
    branch_count: int,
    memory_count: int,
    seed: int,
    output_dir: Path
) -> None:
    """Generates all default branch and memory workload files."""
    rng = random.Random(seed)

    branch_dir = output_dir / "branches"
    memory_dir = output_dir / "memory"

    # Branch Workloads
    branch_files = {
        "mostly_taken.txt": generate_mostly_taken(count=branch_count, rng=rng),
        "mostly_not_taken.txt": generate_mostly_not_taken(count=branch_count, rng=rng),
        "alternating.txt": generate_alternating(count=branch_count),
        "loop.txt": generate_loop_pattern(count=branch_count, taken_per_loop=5),
        "random.txt": generate_random_branches(count=branch_count, rng=rng),
    }

    for filename, workload in branch_files.items():
        save_workload(branch_dir / filename, workload)

    # Memory Workloads
    memory_files = {
        "high_locality.txt": generate_high_locality(count=memory_count, rng=rng),
        "sequential.txt": generate_sequential(count=memory_count, start=0, stride=4),
        "random.txt": generate_random_memory(count=memory_count, rng=rng),
        "conflict.txt": generate_conflict_workload(count=memory_count, base_addr=0, stride=16, num_tags=4),
    }

    for filename, workload in memory_files.items():
        save_workload(memory_dir / filename, workload)

    # Console Summary
    print("Generated branch workloads:")
    for filename, workload in branch_files.items():
        print(f"  {filename:<22} {len(workload)} entries")

    print("\nGenerated memory workloads:")
    for filename, workload in memory_files.items():
        print(f"  {filename:<22} {len(workload)} entries")

    print(f"\nSeed: {seed}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synthetic workload generator for CPU microarchitecture performance verification."
    )
    parser.add_argument(
        "--branch-count",
        type=int,
        default=DEFAULT_BRANCH_COUNT,
        help=f"Number of branch outcomes per workload (default: {DEFAULT_BRANCH_COUNT})"
    )
    parser.add_argument(
        "--memory-count",
        type=int,
        default=DEFAULT_MEMORY_COUNT,
        help=f"Number of memory accesses per workload (default: {DEFAULT_MEMORY_COUNT})"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed for deterministic generation (default: {DEFAULT_SEED})"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("workloads"),
        help="Root output directory for workload files (default: workloads/)"
    )

    args = parser.parse_args()

    generate_all_workloads(
        branch_count=args.branch_count,
        memory_count=args.memory_count,
        seed=args.seed,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()
