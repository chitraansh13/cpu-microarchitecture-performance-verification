#!/usr/bin/env python3
"""
Performance Analyzer for CPU Microarchitecture Verification.

Consumes results/regression_results.csv produced by regression testing and generates
results/performance_report.txt containing comparison tables, analytical Estimated CPI,
and data-driven microarchitectural observations.

Standard Library Only.
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_CSV_PATH = REPO_ROOT / "results" / "regression_results.csv"
DEFAULT_REPORT_PATH = REPO_ROOT / "results" / "performance_report.txt"

BRANCH_WORKLOADS = [
    "mostly_taken",
    "mostly_not_taken",
    "alternating",
    "loop",
    "random",
]

MEMORY_WORKLOADS = [
    "high_locality",
    "sequential",
    "random",
    "conflict",
]

PREDICTOR_ID_MAP = {
    "1bit": "branch_predictor_1bit",
    "2bit": "branch_predictor_2bit",
}

WORKLOAD_DISPLAY_NAMES = {
    "mostly_taken": "Mostly Taken",
    "mostly_not_taken": "Mostly Not Taken",
    "alternating": "Alternating",
    "loop": "Loop",
    "random": "Random",
    "high_locality": "High Locality",
    "sequential": "Sequential",
    "conflict": "Conflict",
}


# ============================================================================
# CSV Parsing & Validation
# ============================================================================

def parse_regression_csv(csv_path: Path) -> List[Dict[str, Any]]:
    """Reads and validates regression results CSV."""
    if not csv_path.exists():
        sys.stderr.write(f"[ERROR] Regression results CSV not found: {csv_path}\n")
        sys.stderr.write("Please run 'python scripts/regression.py' first.\n")
        sys.exit(1)

    rows = []
    required_cols = {
        "component", "workload", "status", "total_events",
        "correct_or_hits", "incorrect_or_misses", "metric_name", "metric_value"
    }

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not required_cols.issubset(set(reader.fieldnames or [])):
                sys.stderr.write(f"[ERROR] CSV is missing required columns. Expected: {required_cols}\n")
                sys.exit(1)

            for row in reader:
                raw_metric = row["metric_value"].rstrip("%")
                rows.append({
                    "component": row["component"],
                    "workload": row["workload"],
                    "status": row["status"],
                    "total_events": int(row["total_events"]),
                    "correct_or_hits": int(row["correct_or_hits"]),
                    "incorrect_or_misses": int(row["incorrect_or_misses"]),
                    "metric_name": row["metric_name"],
                    "metric_val_float": float(raw_metric),
                    "metric_val_str": row["metric_value"],
                })
    except Exception as e:
        sys.stderr.write(f"[ERROR] Failed to parse CSV file {csv_path}: {e}\n")
        sys.exit(1)

    if not rows:
        sys.stderr.write(f"[ERROR] CSV file {csv_path} contains no data rows.\n")
        sys.exit(1)

    failing_rows = [r for r in rows if r["status"] != "PASS"]
    if failing_rows:
        sys.stderr.write(f"[ERROR] Regression CSV contains {len(failing_rows)} non-PASS test case(s).\n")
        sys.stderr.write("Performance analysis cannot be performed on failing regressions.\n")
        sys.exit(1)

    return rows


# ============================================================================
# Performance Calculation & Report Synthesis
# ============================================================================

def build_lookup_table(rows: List[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """Creates (component, workload) -> row lookup dict."""
    return {(r["component"], r["workload"]): r for r in rows}


def generate_performance_report(
    rows: List[Dict[str, Any]],
    instructions: int,
    base_cpi: float,
    branch_penalty: int,
    cache_miss_penalty: int,
    predictor_choice: str,
    branch_workload_choice: str,
    cache_workload_choice: str,
) -> str:
    """Synthesizes the complete performance report string."""
    lookup = build_lookup_table(rows)
    pred_comp_id = PREDICTOR_ID_MAP[predictor_choice]

    if (pred_comp_id, branch_workload_choice) not in lookup:
        sys.stderr.write(f"[ERROR] Workload '{branch_workload_choice}' for '{predictor_choice}' not found in CSV.\n")
        sys.exit(1)
    if ("direct_mapped_cache", cache_workload_choice) not in lookup:
        sys.stderr.write(f"[ERROR] Cache workload '{cache_workload_choice}' not found in CSV.\n")
        sys.exit(1)

    # 1. Predictor Comparison Table
    pred_lines = []
    pred_lines.append("Branch Predictor Results\n")
    pred_lines.append(f"{'Workload':<18} {'1-bit':<10} {'2-bit':<10}")
    pred_lines.append("-" * 38)

    accuracy_diffs = {}
    for wl in BRANCH_WORKLOADS:
        row_1bit = lookup.get(("branch_predictor_1bit", wl))
        row_2bit = lookup.get(("branch_predictor_2bit", wl))

        val_1bit = f"{row_1bit['metric_val_float']:.2f}%" if row_1bit else "N/A"
        val_2bit = f"{row_2bit['metric_val_float']:.2f}%" if row_2bit else "N/A"

        if row_1bit and row_2bit:
            accuracy_diffs[wl] = row_2bit['metric_val_float'] - row_1bit['metric_val_float']

        display_name = WORKLOAD_DISPLAY_NAMES.get(wl, wl)
        pred_lines.append(f"{display_name:<18} {val_1bit:<10} {val_2bit:<10}")

    pred_table_str = "\n".join(pred_lines)

    # 2. Cache Results Table
    cache_lines = []
    cache_lines.append("Cache Results\n")
    cache_lines.append(f"{'Workload':<18} {'Hit Rate':<10}")
    cache_lines.append("-" * 28)

    cache_hit_rates = {}
    for wl in MEMORY_WORKLOADS:
        row_cache = lookup.get(("direct_mapped_cache", wl))
        val_cache = f"{row_cache['metric_val_float']:.2f}%" if row_cache else "N/A"
        if row_cache:
            cache_hit_rates[wl] = row_cache['metric_val_float']
        display_name = WORKLOAD_DISPLAY_NAMES.get(wl, wl)
        cache_lines.append(f"{display_name:<18} {val_cache:<10}")

    cache_table_str = "\n".join(cache_lines)

    # 3. Selected Scenario Performance Calculations
    branch_row = lookup[(pred_comp_id, branch_workload_choice)]
    cache_row = lookup[("direct_mapped_cache", cache_workload_choice)]

    branch_mispredicts = branch_row["incorrect_or_misses"]
    branch_events = branch_row["total_events"]

    cache_misses = cache_row["incorrect_or_misses"]
    memory_accesses = cache_row["total_events"]

    base_cycles = float(instructions) * base_cpi
    extra_branch_cycles = float(branch_mispredicts) * branch_penalty
    extra_cache_cycles = float(cache_misses) * cache_miss_penalty
    total_cycles = base_cycles + extra_branch_cycles + extra_cache_cycles
    estimated_cpi = total_cycles / float(instructions)

    # 4. Data-Driven Observations
    obs_lines = []
    if "loop" in accuracy_diffs:
        diff_loop = accuracy_diffs["loop"]
        obs_lines.append(f"- 2-bit predictor improves loop-workload accuracy by {diff_loop:+.2f} percentage points over 1-bit.")

    row_1bit_alt = lookup.get(("branch_predictor_1bit", "alternating"))
    if row_1bit_alt and row_1bit_alt["metric_val_float"] < 5.0:
        obs_lines.append(f"- Alternating branch behavior is especially poor for the 1-bit predictor ({row_1bit_alt['metric_val_float']:.2f}% accuracy).")

    if cache_hit_rates:
        best_cache_wl = max(cache_hit_rates, key=cache_hit_rates.get)
        worst_cache_wl = min(cache_hit_rates, key=cache_hit_rates.get)
        obs_lines.append(f"- {WORKLOAD_DISPLAY_NAMES.get(best_cache_wl, best_cache_wl)} workload produced the highest cache hit rate ({cache_hit_rates[best_cache_wl]:.2f}%).")
        obs_lines.append(f"- {WORKLOAD_DISPLAY_NAMES.get(worst_cache_wl, worst_cache_wl)} workload produced the lowest cache hit rate ({cache_hit_rates[worst_cache_wl]:.2f}%).")

    obs_str = "\n".join(obs_lines)

    # Construct full report text
    report = f"""============================================================
CPU MICROARCHITECTURE PERFORMANCE REPORT
============================================================

Regression Status: PASS

{pred_table_str}

{cache_table_str}

Selected Performance Scenario

Predictor:                  {predictor_choice} ({pred_comp_id})
Branch Workload:            {branch_workload_choice}
Cache Workload:             {cache_workload_choice}

Performance Model Parameters

Instructions:               {instructions}
Base CPI:                   {base_cpi:.2f}
Branch Mispredict Penalty:  {branch_penalty} cycles
Cache Miss Penalty:         {cache_miss_penalty} cycles

Observed Regression Counts

Branch Events:              {branch_events}
Branch Mispredictions:      {branch_mispredicts}
Memory Accesses:            {memory_accesses}
Cache Misses:               {cache_misses}

Estimated Performance

Base Instruction Cycles:    {base_cycles:.1f}
Extra Branch Cycles:        {extra_branch_cycles:.1f}
Extra Cache Cycles:         {extra_cache_cycles:.1f}
Estimated Total Cycles:     {total_cycles:.1f}
Estimated CPI:              {estimated_cpi:.4f}

Key Observations

{obs_str}

Important:
Estimated CPI is a simplified analytical metric, not measured real CPU CPI.
Branch and cache traces are independent synthetic workloads.
============================================================
"""
    return report


# ============================================================================
# CLI & Main Entry Point
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="CPU Microarchitecture Performance Analyzer & Analytical CPI Calculator."
    )
    parser.add_argument(
        "--csv-file",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help="Path to regression results CSV file (default: results/regression_results.csv)"
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Path to output text performance report (default: results/performance_report.txt)"
    )
    parser.add_argument(
        "--instructions",
        type=int,
        default=10000,
        help="Modeled total instruction count for analytical CPI calculation (default: 10000)"
    )
    parser.add_argument(
        "--base-cpi",
        type=float,
        default=1.0,
        help="Base instruction execution CPI without stall penalties (default: 1.0)"
    )
    parser.add_argument(
        "--branch-penalty",
        type=int,
        default=3,
        help="Stall cycles incurred per branch misprediction (default: 3)"
    )
    parser.add_argument(
        "--cache-miss-penalty",
        type=int,
        default=10,
        help="Stall cycles incurred per cache miss (default: 10)"
    )
    parser.add_argument(
        "--predictor",
        choices=["1bit", "2bit"],
        default="2bit",
        help="Selected predictor for performance scenario (default: 2bit)"
    )
    parser.add_argument(
        "--branch-workload",
        choices=BRANCH_WORKLOADS,
        default="loop",
        help="Selected branch workload for performance scenario (default: loop)"
    )
    parser.add_argument(
        "--cache-workload",
        choices=MEMORY_WORKLOADS,
        default="high_locality",
        help="Selected cache workload for performance scenario (default: high_locality)"
    )

    args = parser.parse_args()

    # CLI parameter validation
    if args.instructions <= 0:
        sys.stderr.write("[ERROR] --instructions must be greater than 0.\n")
        sys.exit(1)
    if args.base_cpi <= 0.0:
        sys.stderr.write("[ERROR] --base-cpi must be greater than 0.0.\n")
        sys.exit(1)
    if args.branch_penalty < 0:
        sys.stderr.write("[ERROR] --branch-penalty must be non-negative.\n")
        sys.exit(1)
    if args.cache_miss_penalty < 0:
        sys.stderr.write("[ERROR] --cache-miss-penalty must be non-negative.\n")
        sys.exit(1)

    rows = parse_regression_csv(args.csv_file)

    report_text = generate_performance_report(
        rows=rows,
        instructions=args.instructions,
        base_cpi=args.base_cpi,
        branch_penalty=args.branch_penalty,
        cache_miss_penalty=args.cache_miss_penalty,
        predictor_choice=args.predictor,
        branch_workload_choice=args.branch_workload,
        cache_workload_choice=args.cache_workload,
    )

    # Print to console
    print(report_text)

    # Save to file
    args.report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(args.report_file, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"Saved performance report: {args.report_file}")


if __name__ == "__main__":
    main()
