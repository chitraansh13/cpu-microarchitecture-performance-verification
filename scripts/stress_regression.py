#!/usr/bin/env python3
"""
Multi-Seed Randomized Stress Regression Runner for CPU Microarchitecture Verification.

Repeatedly generates deterministic synthetic workloads across a range of random seeds
and executes the 14-case RTL vs Python co-verification regression suite for each seed.

Calculates verified RTL event counts and logs summary results to results/stress_regression_results.csv.

Standard Library Only.
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from workload_generator import generate_all_workloads
from regression import run_full_regression, check_toolchain

RESULTS_DIR = REPO_ROOT / "results"
WORKLOADS_DIR = REPO_ROOT / "workloads"


def save_stress_csv(records: List[Dict[str, Any]]) -> None:
    """Saves multi-seed stress regression summary to results/stress_regression_results.csv."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    csv_file = RESULTS_DIR / "stress_regression_results.csv"

    fieldnames = [
        "seed",
        "regression_cases",
        "passed",
        "failed",
        "status",
        "verified_events"
    ]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow(rec)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Multi-seed randomized stress regression runner."
    )
    parser.add_argument(
        "--start-seed",
        type=int,
        default=1,
        help="Starting integer seed for random workload generation (default: 1)"
    )
    parser.add_argument(
        "--num-seeds",
        type=int,
        default=20,
        help="Total number of consecutive seeds to test (default: 20)"
    )
    parser.add_argument(
        "--branch-count",
        type=int,
        default=1000,
        help="Number of branch outcomes per workload trace (default: 1000)"
    )
    parser.add_argument(
        "--memory-count",
        type=int,
        default=1000,
        help="Number of memory accesses per workload trace (default: 1000)"
    )
    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="Halt stress regression immediately upon the first seed failure"
    )

    args = parser.parse_args()

    check_toolchain()

    print("============================================================")
    print("MULTI-SEED STRESS REGRESSION")
    print("============================================================")

    seed_records = []
    total_verified_events = 0
    total_cases_run = 0
    total_cases_passed = 0
    total_cases_failed = 0
    failed_seeds = 0

    end_seed = args.start_seed + args.num_seeds

    for seed in range(args.start_seed, end_seed):
        # 1. Generate workloads deterministically for this seed
        try:
            generate_all_workloads(
                branch_count=args.branch_count,
                memory_count=args.memory_count,
                seed=seed,
                output_dir=WORKLOADS_DIR,
                verbose=False
            )
        except Exception as e:
            print(f"Seed {seed:<5} FAIL   [Workload Generation Error: {e}]")
            failed_seeds += 1
            seed_records.append({
                "seed": seed,
                "regression_cases": 0,
                "passed": 0,
                "failed": 0,
                "status": "FAIL",
                "verified_events": 0
            })
            if args.stop_on_failure:
                break
            continue

        # 2. Run 14-case regression suite
        case_results, overall_pass = run_full_regression(
            component="all",
            verbose=False,
            save_csv=False
        )

        num_cases = len(case_results)
        passed_cnt = sum(1 for r in case_results if r["status"] == "PASS")
        failed_cnt = num_cases - passed_cnt
        seed_events = sum(r["total_events"] for r in case_results)
        status_str = "PASS" if overall_pass else "FAIL"

        total_cases_run += num_cases
        total_cases_passed += passed_cnt
        total_cases_failed += failed_cnt
        total_verified_events += seed_events

        if not overall_pass:
            failed_seeds += 1

        print(f"Seed {seed:<5} {status_str:<6} {passed_cnt}/{num_cases}")

        # If failures occurred, print details
        if not overall_pass:
            for r in case_results:
                if r["status"] == "FAIL" and r["error"]:
                    print(f"  -> [{r['component']}/{r['workload']}] {r['error']}")

        seed_records.append({
            "seed": seed,
            "regression_cases": num_cases,
            "passed": passed_cnt,
            "failed": failed_cnt,
            "status": status_str,
            "verified_events": seed_events
        })

        if not overall_pass and args.stop_on_failure:
            print(f"\n[STRESS REGRESSION HALTED] Seed {seed} failed (--stop-on-failure enabled).")
            break

    seeds_tested = len(seed_records)
    cases_per_seed = 14 if seeds_tested > 0 else 0
    overall_status = "PASS" if (failed_seeds == 0 and seeds_tested > 0) else "FAIL"

    print("\n------------------------------------------------------------")
    print(f"Seeds Tested:             {seeds_tested}")
    print(f"Regression Cases / Seed:  {cases_per_seed}")
    print(f"Total Regression Cases:   {total_cases_run}")
    print(f"Passed:                   {total_cases_passed}")
    print(f"Failed:                   {total_cases_failed}")
    print(f"Verified RTL Events:      {total_verified_events}")
    print(f"Overall Status:           {overall_status}")
    print("------------------------------------------------------------")

    # Save CSV summary
    if seed_records:
        save_stress_csv(seed_records)
        print(f"\nSaved stress regression CSV: results/stress_regression_results.csv")

    sys.exit(0 if overall_status == "PASS" else 1)


if __name__ == "__main__":
    main()
