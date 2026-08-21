#!/usr/bin/env python3
"""
Automated Regression Runner for CPU Microarchitecture Performance Verification.

Automates:
1. RTL Compilation via Icarus Verilog (iverilog -g2012)
2. Simulation execution via vvp with workload plusargs (+WORKLOAD=...)
3. Machine-readable event log parsing (REG_BRANCH, REG_CACHE)
4. Event-by-event equivalence checking against Python golden reference models
5. CSV result logging (results/regression_results.csv)
6. Summary reporting and exit code status (0 for PASS, 1 for FAIL)

Standard Library Only.
"""

import argparse
import csv
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

# Ensure scripts directory is in sys.path to import reference_models
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

BUILD_DIR = REPO_ROOT / "build"
WORKLOADS_DIR = REPO_ROOT / "workloads"
RESULTS_DIR = REPO_ROOT / "results"

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


# ============================================================================
# Helper Functions & Tooling Checks
# ============================================================================

def check_toolchain() -> None:
    """Verifies that iverilog and vvp are available in PATH."""
    if shutil.which("iverilog") is None:
        sys.stderr.write("[ERROR] 'iverilog' compiler not found in PATH.\n")
        sys.exit(1)
    if shutil.which("vvp") is None:
        sys.stderr.write("[ERROR] 'vvp' simulator not found in PATH.\n")
        sys.exit(1)


def compile_simulation(
    target_name: str,
    rtl_rel_path: str,
    tb_rel_path: str
) -> Tuple[bool, Path, str]:
    """Compiles RTL and Testbench into build directory using iverilog -g2012."""
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    out_exe = BUILD_DIR / target_name
    rtl_path = REPO_ROOT / rtl_rel_path
    tb_path = REPO_ROOT / tb_rel_path

    cmd = [
        "iverilog",
        "-g2012",
        "-o", str(out_exe),
        str(rtl_path),
        str(tb_path)
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        err_msg = f"Compilation failed for {target_name}:\n{res.stderr}"
        return False, out_exe, err_msg

    return True, out_exe, ""


def read_workload_file(filepath: Path) -> List[int]:
    """Reads integer list from a workload file."""
    if not filepath.exists():
        raise FileNotFoundError(f"Workload file not found: {filepath}")

    data = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(int(line))
    return data


# ============================================================================
# Machine-Readable RTL Event Parsers
# ============================================================================

def parse_branch_events(stdout: str) -> List[Dict[str, int]]:
    """Parses lines beginning with REG_BRANCH,<num>,<pred>,<actual>."""
    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("REG_BRANCH,"):
            parts = line.split(",")
            if len(parts) == 4:
                events.append({
                    "branch_num": int(parts[1]),
                    "prediction": int(parts[2]),
                    "actual": int(parts[3]),
                })
    return events


def parse_cache_events(stdout: str) -> List[Dict[str, Any]]:
    """Parses lines beginning with REG_CACHE,<num>,<address>,<hit>."""
    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("REG_CACHE,"):
            parts = line.split(",")
            if len(parts) == 4:
                events.append({
                    "access_num": int(parts[1]),
                    "address": int(parts[2]),
                    "hit": int(parts[3]),
                })
    return events


# ============================================================================
# Regression Case Runners
# ============================================================================

def run_branch_regression_case(
    component_id: str,
    exe_path: Path,
    workload_name: str,
    model_factory: Any
) -> Dict[str, Any]:
    """Runs a single branch predictor regression case and checks against Python golden model."""
    workload_file = WORKLOADS_DIR / "branches" / f"{workload_name}.txt"
    try:
        workload_data = read_workload_file(workload_file)
    except Exception as e:
        return {
            "component": component_id,
            "workload": workload_name,
            "status": "FAIL",
            "error": f"Failed to load workload file: {e}",
            "metric_name": "accuracy",
            "metric_value": 0.0,
            "total_events": 0,
            "correct_or_hits": 0,
            "incorrect_or_misses": 0
        }

    # Run Python Golden Reference Model
    golden_model = model_factory()
    golden_res = run_branch_trace(golden_model, workload_data)
    golden_events = golden_res["events"]

    # Run Simulation via vvp
    cmd = ["vvp", str(exe_path), f"+WORKLOAD={workload_file}"]
    sim_res = subprocess.run(cmd, capture_output=True, text=True)

    if sim_res.returncode != 0:
        return {
            "component": component_id,
            "workload": workload_name,
            "status": "FAIL",
            "error": f"Simulation runtime error (exit code {sim_res.returncode}):\n{sim_res.stderr}",
            "metric_name": "accuracy",
            "metric_value": golden_res["accuracy"],
            "total_events": golden_res["total"],
            "correct_or_hits": golden_res["correct"],
            "incorrect_or_misses": golden_res["incorrect"]
        }

    rtl_events = parse_branch_events(sim_res.stdout)

    # Event-by-event check
    if len(rtl_events) != len(golden_events):
        return {
            "component": component_id,
            "workload": workload_name,
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
                f"  RTL prediction : {rtl_e['prediction']} (actual: {rtl_e['actual']})\n"
                f"  Python expected: {gold_e['prediction']} (actual: {gold_e['actual']})"
            )
            break

    status = "FAIL" if mismatch_msg else "PASS"

    return {
        "component": component_id,
        "workload": workload_name,
        "status": status,
        "error": mismatch_msg,
        "metric_name": "accuracy",
        "metric_value": golden_res["accuracy"],
        "total_events": golden_res["total"],
        "correct_or_hits": golden_res["correct"],
        "incorrect_or_misses": golden_res["incorrect"]
    }


def run_cache_regression_case(
    component_id: str,
    exe_path: Path,
    workload_name: str
) -> Dict[str, Any]:
    """Runs a single direct-mapped cache regression case and checks against Python golden model."""
    workload_file = WORKLOADS_DIR / "memory" / f"{workload_name}.txt"
    try:
        workload_data = read_workload_file(workload_file)
    except Exception as e:
        return {
            "component": component_id,
            "workload": workload_name,
            "status": "FAIL",
            "error": f"Failed to load workload file: {e}",
            "metric_name": "hit_rate",
            "metric_value": 0.0,
            "total_events": 0,
            "correct_or_hits": 0,
            "incorrect_or_misses": 0
        }

    # Run Python Golden Reference Model
    cache_model = DirectMappedCache()
    golden_res = run_cache_trace(cache_model, workload_data)
    golden_events = golden_res["events"]

    # Run Simulation via vvp
    cmd = ["vvp", str(exe_path), f"+WORKLOAD={workload_file}"]
    sim_res = subprocess.run(cmd, capture_output=True, text=True)

    if sim_res.returncode != 0:
        return {
            "component": component_id,
            "workload": workload_name,
            "status": "FAIL",
            "error": f"Simulation runtime error (exit code {sim_res.returncode}):\n{sim_res.stderr}",
            "metric_name": "hit_rate",
            "metric_value": golden_res["hit_rate"],
            "total_events": golden_res["total"],
            "correct_or_hits": golden_res["hits"],
            "incorrect_or_misses": golden_res["misses"]
        }

    rtl_events = parse_cache_events(sim_res.stdout)

    # Event-by-event check
    if len(rtl_events) != len(golden_events):
        return {
            "component": component_id,
            "workload": workload_name,
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
        "workload": workload_name,
        "status": status,
        "error": mismatch_msg,
        "metric_name": "hit_rate",
        "metric_value": golden_res["hit_rate"],
        "total_events": golden_res["total"],
        "correct_or_hits": golden_res["hits"],
        "incorrect_or_misses": golden_res["misses"]
    }


# ============================================================================
# CSV Report Generator
# ============================================================================

def save_regression_csv(results: List[Dict[str, Any]]) -> None:
    """Saves regression case metrics and status to results/regression_results.csv."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    csv_file = RESULTS_DIR / "regression_results.csv"

    fieldnames = [
        "component",
        "workload",
        "status",
        "total_events",
        "correct_or_hits",
        "incorrect_or_misses",
        "metric_name",
        "metric_value"
    ]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for res in results:
            writer.writerow({
                "component": res["component"],
                "workload": res["workload"],
                "status": res["status"],
                "total_events": res["total_events"],
                "correct_or_hits": res["correct_or_hits"],
                "incorrect_or_misses": res["incorrect_or_misses"],
                "metric_name": res["metric_name"],
                "metric_value": f"{res['metric_value']:.2f}%"
            })


# ============================================================================
# Main Regression Orchestration
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automated RTL vs Python regression test suite."
    )
    parser.add_argument(
        "--component",
        choices=["all", "1bit", "2bit", "cache"],
        default="all",
        help="Specific component suite to test (default: all)"
    )
    args = parser.parse_args()

    check_toolchain()

    print("============================================================")
    print("CPU MICROARCHITECTURE REGRESSION")
    print("============================================================")

    all_results = []
    compilation_failures = 0

    # 1. 1-Bit Branch Predictor Suite
    if args.component in ("all", "1bit"):
        print("\n1-BIT BRANCH PREDICTOR")
        ok, exe, err = compile_simulation(
            "branch_1bit_sim",
            "rtl/branch_predictor_1bit.sv",
            "tb/branch_predictor_1bit_tb.sv"
        )
        if not ok:
            print(f"  [COMPILATION ERROR] {err}")
            compilation_failures += len(BRANCH_WORKLOADS)
        else:
            for wl in BRANCH_WORKLOADS:
                res = run_branch_regression_case(
                    "branch_predictor_1bit", exe, wl, OneBitBranchPredictor
                )
                all_results.append(res)
                metric_str = f"{res['metric_name']}={res['metric_value']:.2f}%"
                print(f"  {wl:<18} {res['status']:<6} {metric_str}")
                if res["status"] == "FAIL" and res["error"]:
                    print(f"    -> {res['error']}")

    # 2. 2-Bit Branch Predictor Suite
    if args.component in ("all", "2bit"):
        print("\n2-BIT BRANCH PREDICTOR")
        ok, exe, err = compile_simulation(
            "branch_2bit_sim",
            "rtl/branch_predictor_2bit.sv",
            "tb/branch_predictor_2bit_tb.sv"
        )
        if not ok:
            print(f"  [COMPILATION ERROR] {err}")
            compilation_failures += len(BRANCH_WORKLOADS)
        else:
            for wl in BRANCH_WORKLOADS:
                res = run_branch_regression_case(
                    "branch_predictor_2bit", exe, wl, TwoBitBranchPredictor
                )
                all_results.append(res)
                metric_str = f"{res['metric_name']}={res['metric_value']:.2f}%"
                print(f"  {wl:<18} {res['status']:<6} {metric_str}")
                if res["status"] == "FAIL" and res["error"]:
                    print(f"    -> {res['error']}")

    # 3. Direct-Mapped Cache Suite
    if args.component in ("all", "cache"):
        print("\nDIRECT-MAPPED CACHE")
        ok, exe, err = compile_simulation(
            "cache_sim",
            "rtl/direct_mapped_cache.sv",
            "tb/cache_tb.sv"
        )
        if not ok:
            print(f"  [COMPILATION ERROR] {err}")
            compilation_failures += len(MEMORY_WORKLOADS)
        else:
            for wl in MEMORY_WORKLOADS:
                res = run_cache_regression_case(
                    "direct_mapped_cache", exe, wl
                )
                all_results.append(res)
                metric_str = f"{res['metric_name']}={res['metric_value']:.2f}%"
                print(f"  {wl:<18} {res['status']:<6} {metric_str}")
                if res["status"] == "FAIL" and res["error"]:
                    print(f"    -> {res['error']}")

    # Summary calculation
    total_cases = len(all_results) + compilation_failures
    passed_cases = sum(1 for r in all_results if r["status"] == "PASS")
    failed_cases = total_cases - passed_cases
    overall_status = "PASS" if (failed_cases == 0 and total_cases > 0) else "FAIL"

    print("\n------------------------------------------------------------")
    print(f"Regression Cases: {total_cases}")
    print(f"Passed:           {passed_cases}")
    print(f"Failed:            {failed_cases}")
    print(f"Overall Status:   {overall_status}")
    print("------------------------------------------------------------")

    # Save CSV Report
    if all_results:
        save_regression_csv(all_results)
        print(f"\nSaved regression CSV: results/regression_results.csv")

    sys.exit(0 if overall_status == "PASS" else 1)


if __name__ == "__main__":
    main()
