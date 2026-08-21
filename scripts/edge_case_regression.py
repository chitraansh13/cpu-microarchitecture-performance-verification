#!/usr/bin/env python3
"""
Directed Edge-Case Verification Runner for CPU Microarchitecture Performance Verification.

Generates programmatically targeted branch and memory workload files under
workloads/edge_cases/ to test boundary, pathological, minimum-length, byte-offset,
saturation, and conflict behaviors across:
- 1-Bit Branch Predictor
- 2-Bit Saturating Branch Predictor
- Direct-Mapped Cache

Compares RTL outputs transaction-by-transaction against software golden models.
Outputs results to terminal and logs summary to results/edge_case_results.csv.

Standard Library Only.
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from reference_models import (
    OneBitBranchPredictor,
    TwoBitBranchPredictor,
    DirectMappedCache,
    run_branch_trace,
    run_cache_trace,
)
from regression import (
    check_toolchain,
    compile_simulation,
    parse_branch_events,
    parse_cache_events,
    read_workload_file,
)

EDGE_WORKLOADS_DIR = REPO_ROOT / "workloads" / "edge_cases"
BRANCH_EDGE_DIR = EDGE_WORKLOADS_DIR / "branches"
MEMORY_EDGE_DIR = EDGE_WORKLOADS_DIR / "memory"
RESULTS_DIR = REPO_ROOT / "results"
BUILD_DIR = REPO_ROOT / "build"


# ============================================================================
# Local File Utilities
# ============================================================================

def save_workload(file_path: Path, workload: List[int]) -> None:
    """Saves a workload list to a file, one integer per line."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        for item in workload:
            f.write(f"{item}\n")


# ============================================================================
# Directed Workload Generator Functions
# ============================================================================

def generate_directed_branch_workloads() -> Dict[str, List[int]]:
    """Generates directed branch edge-case workload dictionary."""
    return {
        "all_taken": [1] * 100,
        "all_not_taken": [0] * 100,
        "single_taken": [1],
        "single_not_taken": [0],
        "opposite_1_0": [1, 0],
        "opposite_0_1": [0, 1],
        "strict_alternating": [1 if i % 2 == 0 else 0 for i in range(100)],
        "long_taken_then_one_not_taken": ([1] * 99) + [0],
        "long_not_taken_then_one_taken": ([0] * 99) + [1],
        "repeated_loop_exit": ([1, 1, 1, 1, 1, 0] * 17)[:100],
        "saturation_transition": ([0] * 10) + ([1] * 10),
    }


def generate_directed_memory_workloads() -> Dict[str, List[int]]:
    """Generates directed cache edge-case workload dictionary."""
    return {
        "same_address_repeated": [0] * 100,
        "same_block_offsets": [0, 1, 2, 3, 0, 1, 2, 3] * 12,
        "every_index": [0, 4, 8, 12, 0, 4, 8, 12] * 12,
        "conflict_thrashing": ([0, 16] * 50),
        "multiple_same_index_tags": ([0, 16, 32, 48, 64] * 20),
        "max_address": ([65532, 65533, 65534, 65535] * 25),
        "address_zero": [0],
        "block_boundary": [0, 1, 2, 3, 4, 5, 6, 7],
        "capacity_pressure": ([0, 4, 8, 12, 16, 20, 24, 28] * 12),
    }


def create_directed_workload_files() -> Tuple[Dict[str, Path], Dict[str, Path]]:
    """Programmatically writes directed trace files to workloads/edge_cases/."""
    BRANCH_EDGE_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_EDGE_DIR.mkdir(parents=True, exist_ok=True)

    branch_workloads = generate_directed_branch_workloads()
    branch_paths = {}
    for name, trace in branch_workloads.items():
        file_path = BRANCH_EDGE_DIR / f"{name}.txt"
        save_workload(file_path, trace)
        branch_paths[name] = file_path

    memory_workloads = generate_directed_memory_workloads()
    memory_paths = {}
    for name, trace in memory_workloads.items():
        file_path = MEMORY_EDGE_DIR / f"{name}.txt"
        save_workload(file_path, trace)
        memory_paths[name] = file_path

    return branch_paths, memory_paths


# ============================================================================
# Directed Case Execution & Checking
# ============================================================================

def run_directed_branch_case(
    component_id: str,
    exe_path: Path,
    case_name: str,
    workload_file: Path,
    model_factory: Any
) -> Dict[str, Any]:
    """Runs a directed branch edge-case against RTL and Python golden model."""
    workload_data = read_workload_file(workload_file)

    golden_model = model_factory()
    golden_res = run_branch_trace(golden_model, workload_data)
    golden_events = golden_res["events"]

    import subprocess
    cmd = ["vvp", str(exe_path), f"+WORKLOAD={workload_file}"]
    sim_res = subprocess.run(cmd, capture_output=True, text=True)

    if sim_res.returncode != 0:
        return {
            "component": component_id,
            "test_case": case_name,
            "status": "FAIL",
            "error": f"Simulation runtime error (exit code {sim_res.returncode}):\n{sim_res.stderr}",
            "metric_name": "accuracy",
            "metric_value": golden_res["accuracy"],
            "total_events": golden_res["total"],
            "correct_or_hits": golden_res["correct"],
            "incorrect_or_misses": golden_res["incorrect"]
        }

    rtl_events = parse_branch_events(sim_res.stdout)

    if len(rtl_events) != len(golden_events):
        return {
            "component": component_id,
            "test_case": case_name,
            "status": "FAIL",
            "error": f"Event count mismatch: RTL produced {len(rtl_events)} events, Python expected {len(golden_events)}",
            "metric_name": "accuracy",
            "metric_value": golden_res["accuracy"],
            "total_events": len(rtl_events),
            "correct_or_hits": golden_res["correct"],
            "incorrect_or_misses": golden_res["incorrect"]
        }

    mismatch_msg = None
    for i, (rtl_e, gold_e) in enumerate(zip(rtl_events, golden_events)):
        if (rtl_e["actual"] != gold_e["actual"] or
            rtl_e["prediction"] != gold_e["prediction"] or
            rtl_e["branch_num"] != gold_e["branch_num"]):
            mismatch_msg = (
                f"First mismatch at branch {gold_e['branch_num']}:\n"
                f"  Actual         : {gold_e['actual']}\n"
                f"  RTL prediction : {rtl_e['prediction']}\n"
                f"  Python expected: {gold_e['prediction']}"
            )
            break

    status = "FAIL" if mismatch_msg else "PASS"

    return {
        "component": component_id,
        "test_case": case_name,
        "status": status,
        "error": mismatch_msg,
        "metric_name": "accuracy",
        "metric_value": golden_res["accuracy"],
        "total_events": golden_res["total"],
        "correct_or_hits": golden_res["correct"],
        "incorrect_or_misses": golden_res["incorrect"]
    }


def run_directed_cache_case(
    component_id: str,
    exe_path: Path,
    case_name: str,
    workload_file: Path
) -> Dict[str, Any]:
    """Runs a directed cache edge-case against RTL and Python golden model."""
    workload_data = read_workload_file(workload_file)

    cache_model = DirectMappedCache()
    golden_res = run_cache_trace(cache_model, workload_data)
    golden_events = golden_res["events"]

    import subprocess
    cmd = ["vvp", str(exe_path), f"+WORKLOAD={workload_file}"]
    sim_res = subprocess.run(cmd, capture_output=True, text=True)

    if sim_res.returncode != 0:
        return {
            "component": component_id,
            "test_case": case_name,
            "status": "FAIL",
            "error": f"Simulation runtime error (exit code {sim_res.returncode}):\n{sim_res.stderr}",
            "metric_name": "hit_rate",
            "metric_value": golden_res["hit_rate"],
            "total_events": golden_res["total"],
            "correct_or_hits": golden_res["hits"],
            "incorrect_or_misses": golden_res["misses"]
        }

    rtl_events = parse_cache_events(sim_res.stdout)

    if len(rtl_events) != len(golden_events):
        return {
            "component": component_id,
            "test_case": case_name,
            "status": "FAIL",
            "error": f"Event count mismatch: RTL produced {len(rtl_events)} events, Python expected {len(golden_events)}",
            "metric_name": "hit_rate",
            "metric_value": golden_res["hit_rate"],
            "total_events": len(rtl_events),
            "correct_or_hits": golden_res["hits"],
            "incorrect_or_misses": golden_res["misses"]
        }

    mismatch_msg = None
    for i, (rtl_e, gold_e) in enumerate(zip(rtl_events, golden_events)):
        gold_hit_int = 1 if gold_e["hit"] else 0
        if (rtl_e["address"] != gold_e["address"] or
            rtl_e["hit"] != gold_hit_int or
            rtl_e["access_num"] != gold_e["access_num"]):
            mismatch_msg = (
                f"First mismatch at access {gold_e['access_num']}:\n"
                f"  Address        : {gold_e['address']}\n"
                f"  RTL hit        : {rtl_e['hit']}\n"
                f"  Python expected: {gold_hit_int}"
            )
            break

    status = "FAIL" if mismatch_msg else "PASS"

    return {
        "component": component_id,
        "test_case": case_name,
        "status": status,
        "error": mismatch_msg,
        "metric_name": "hit_rate",
        "metric_value": golden_res["hit_rate"],
        "total_events": golden_res["total"],
        "correct_or_hits": golden_res["hits"],
        "incorrect_or_misses": golden_res["misses"]
    }


def save_edge_case_csv(results: List[Dict[str, Any]]) -> None:
    """Saves edge case regression results to results/edge_case_results.csv."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    csv_file = RESULTS_DIR / "edge_case_results.csv"

    fieldnames = [
        "component",
        "test_case",
        "status",
        "total_events",
        "metric_name",
        "metric_value"
    ]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "component": r["component"],
                "test_case": r["test_case"],
                "status": r["status"],
                "total_events": r["total_events"],
                "metric_name": r["metric_name"],
                "metric_value": f"{r['metric_value']:.2f}%"
            })


# ============================================================================
# Main Entry Point
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Directed edge-case verification runner for CPU microarchitecture models."
    )
    args = parser.parse_args()

    check_toolchain()

    print("============================================================")
    print("DIRECTED EDGE-CASE REGRESSION")
    print("============================================================")

    branch_paths, memory_paths = create_directed_workload_files()
    all_results = []

    # 1. Compile Simulators
    ok_1bit, exe_1bit, err_1bit = compile_simulation(
        "edge_branch_1bit_sim", "rtl/branch_predictor_1bit.sv", "tb/branch_predictor_1bit_tb.sv"
    )
    ok_2bit, exe_2bit, err_2bit = compile_simulation(
        "edge_branch_2bit_sim", "rtl/branch_predictor_2bit.sv", "tb/branch_predictor_2bit_tb.sv"
    )
    ok_cache, exe_cache, err_cache = compile_simulation(
        "edge_cache_sim", "rtl/direct_mapped_cache.sv", "tb/cache_tb.sv"
    )

    # 2. 1-Bit Branch Predictor Suite
    print("\n1-BIT BRANCH PREDICTOR")
    if not ok_1bit:
        print(f"  [COMPILATION ERROR] {err_1bit}")
    else:
        for case_name, filepath in branch_paths.items():
            res = run_directed_branch_case(
                "branch_predictor_1bit", exe_1bit, case_name, filepath, OneBitBranchPredictor
            )
            all_results.append(res)
            print(f"  {case_name:<30} {res['status']:<6}")
            if res["status"] == "FAIL" and res["error"]:
                print(f"    FAIL: branch_predictor_1bit / {case_name}")
                print(f"    {res['error']}")

    # 3. 2-Bit Branch Predictor Suite
    print("\n2-BIT BRANCH PREDICTOR")
    if not ok_2bit:
        print(f"  [COMPILATION ERROR] {err_2bit}")
    else:
        for case_name, filepath in branch_paths.items():
            res = run_directed_branch_case(
                "branch_predictor_2bit", exe_2bit, case_name, filepath, TwoBitBranchPredictor
            )
            all_results.append(res)
            print(f"  {case_name:<30} {res['status']:<6}")
            if res["status"] == "FAIL" and res["error"]:
                print(f"    FAIL: branch_predictor_2bit / {case_name}")
                print(f"    {res['error']}")

    # 4. Direct-Mapped Cache Suite
    print("\nDIRECT-MAPPED CACHE")
    if not ok_cache:
        print(f"  [COMPILATION ERROR] {err_cache}")
    else:
        for case_name, filepath in memory_paths.items():
            res = run_directed_cache_case(
                "direct_mapped_cache", exe_cache, case_name, filepath
            )
            all_results.append(res)
            print(f"  {case_name:<30} {res['status']:<6}")
            if res["status"] == "FAIL" and res["error"]:
                print(f"    FAIL: direct_mapped_cache / {case_name}")
                print(f"    {res['error']}")

    total_cases = len(all_results)
    passed_cases = sum(1 for r in all_results if r["status"] == "PASS")
    failed_cases = total_cases - passed_cases
    total_events = sum(r["total_events"] for r in all_results)
    overall_status = "PASS" if (failed_cases == 0 and total_cases > 0) else "FAIL"

    print("\n------------------------------------------------------------")
    print(f"Directed Cases:       {total_cases}")
    print(f"Passed:               {passed_cases}")
    print(f"Failed:               {failed_cases}")
    print(f"Verified RTL Events:  {total_events}")
    print(f"Overall Status:       {overall_status}")
    print("------------------------------------------------------------")

    if all_results:
        save_edge_case_csv(all_results)
        print(f"\nSaved edge case CSV: results/edge_case_results.csv")

    sys.exit(0 if overall_status == "PASS" else 1)


if __name__ == "__main__":
    main()
