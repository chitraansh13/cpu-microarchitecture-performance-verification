from typing import Dict, Any


def calculate_performance(
    instructions: int,
    base_cpi: float,
    branch_penalty: int,
    cache_miss_penalty: int,
    branch_mispredictions: int,
    cache_misses: int
) -> Dict[str, Any]:
    """
    Calculates analytical Estimated CPI using stall penalties from verified component metrics.
    Formula:
      Base Cycles = instructions * base_cpi
      Extra Branch Cycles = branch_mispredictions * branch_penalty
      Extra Cache Cycles = cache_misses * cache_miss_penalty
      Total Cycles = Base Cycles + Extra Branch Cycles + Extra Cache Cycles
      Estimated CPI = Total Cycles / instructions
    """
    base_cycles = float(instructions) * float(base_cpi)
    extra_branch_cycles = float(branch_mispredictions) * float(branch_penalty)
    extra_cache_cycles = float(cache_misses) * float(cache_miss_penalty)
    total_cycles = base_cycles + extra_branch_cycles + extra_cache_cycles
    estimated_cpi = total_cycles / float(instructions) if instructions > 0 else 0.0

    return {
        "instructions": instructions,
        "base_cpi": base_cpi,
        "branch_penalty": branch_penalty,
        "cache_miss_penalty": cache_miss_penalty,
        "base_cycles": round(base_cycles, 2),
        "branch_penalty_cycles": round(extra_branch_cycles, 2),
        "cache_penalty_cycles": round(extra_cache_cycles, 2),
        "estimated_total_cycles": round(total_cycles, 2),
        "estimated_cpi": round(estimated_cpi, 4)
    }
