import os
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Locate repository root and import verification scripts
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
RTL_DIR = REPO_ROOT / "rtl"
TB_DIR = REPO_ROOT / "tb"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import workload_generator as wg
import reference_models as ref
import regression as reg
import verification_engine as ve
from fastapi import HTTPException
from .performance_service import calculate_performance
from .models import (
    VerifyRequest,
    VerifyResponse,
    BranchVerifyResult,
    CacheVerifyResult,
    PerformanceResult,
    RegressionRequest,
    RegressionResponse,
    StressRequest,
    StressResponse,
    EdgeCasesResponse,
    BranchRunRequest,
    BranchRunResponse,
    CacheRunRequest,
    CacheRunResponse,
    CacheConfiguration,
)


def check_toolchain_availability() -> Dict[str, bool]:
    """Safely checks if iverilog and vvp are available in system PATH."""
    return ve.check_verification_toolchain()


def execute_branch_run(req: BranchRunRequest) -> BranchRunResponse:
    """Executes a branch verification run (custom or predefined) using verification_engine."""
    try:
        if req.workload_type == "custom":
            if not req.trace:
                raise HTTPException(status_code=400, detail="Trace parameter is required when workload_type is custom.")
            normalized_trace = ve.normalize_branch_trace(req.trace)
        else:
            rng = random.Random(req.seed)
            if req.workload_type == "mostly_taken":
                normalized_trace = wg.generate_mostly_taken(count=req.count, rng=rng)
            elif req.workload_type == "mostly_not_taken":
                normalized_trace = wg.generate_mostly_not_taken(count=req.count, rng=rng)
            elif req.workload_type == "alternating":
                normalized_trace = wg.generate_alternating(count=req.count)
            elif req.workload_type == "loop":
                normalized_trace = wg.generate_loop_pattern(count=req.count)
            else:
                normalized_trace = wg.generate_random_branches(count=req.count, rng=rng)

        if req.predictor == "both":
            res = ve.compare_branch_predictors(normalized_trace)
            return BranchRunResponse(
                status=res.get("status", "FAIL"),
                input_trace=normalized_trace,
                predictor="both",
                verified=res.get("verified", False),
                trace_length=res.get("trace_length", len(normalized_trace)),
                predictors=res.get("predictors"),
                accuracy_delta=res.get("accuracy_delta"),
                error=res.get("error")
            )
        else:
            res = ve.verify_branch_trace(normalized_trace, req.predictor)
            return BranchRunResponse(
                status=res.get("status", "FAIL"),
                input_trace=normalized_trace,
                predictor=req.predictor,
                verified=res.get("verified", False),
                total=res.get("total"),
                correct=res.get("correct"),
                incorrect=res.get("incorrect"),
                accuracy=res.get("accuracy"),
                events=res.get("events"),
                error=res.get("error")
            )
    except HTTPException:
        raise
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        return BranchRunResponse(
            status="FAIL",
            input_trace=[],
            error=f"Unexpected {type(exc).__name__}: {str(exc)}"
        )


def execute_cache_run(req: CacheRunRequest) -> CacheRunResponse:
    """Executes a cache verification run (custom or predefined) using verification_engine."""
    try:
        if req.workload_type == "custom":
            if not req.addresses:
                raise HTTPException(status_code=400, detail="Addresses parameter is required when workload_type is custom.")
            normalized_addresses = ve.normalize_memory_trace(req.addresses)
        else:
            rng = random.Random(req.seed)
            if req.workload_type == "high_locality":
                normalized_addresses = wg.generate_high_locality(count=req.count, rng=rng)
            elif req.workload_type == "sequential":
                normalized_addresses = wg.generate_sequential(count=req.count)
            elif req.workload_type == "random":
                normalized_addresses = wg.generate_random_memory(count=req.count, rng=rng)
            else:
                normalized_addresses = wg.generate_conflict_workload(count=req.count)

        res = ve.verify_cache_trace(normalized_addresses)
        return CacheRunResponse(
            status=res.get("status", "FAIL"),
            verified=res.get("verified", False),
            configuration=CacheConfiguration(),
            input_addresses=normalized_addresses,
            total=res.get("total", 0),
            hits=res.get("hits", 0),
            misses=res.get("misses", 0),
            hit_rate=res.get("hit_rate", 0.0),
            miss_rate=res.get("miss_rate", 0.0),
            events=res.get("events", []),
            error=res.get("error")
        )
    except HTTPException:
        raise
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        return CacheRunResponse(
            status="FAIL",
            input_addresses=[],
            error=f"Unexpected {type(exc).__name__}: {str(exc)}"
        )


def _save_temp_workload(filepath: Path, data: List[int]) -> None:
    """Saves a workload integer list to a temporary file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        for val in data:
            f.write(f"{val}\n")


def execute_interactive_verify(req: VerifyRequest) -> VerifyResponse:
    """
    Executes an interactive dual-path co-verification run for selected predictor & cache workloads.
    RTL simulation runs in an isolated temporary directory.
    """
    tc = check_toolchain_availability()
    if not (tc["iverilog"] and tc["vvp"]):
        return VerifyResponse(
            status="FAIL",
            configuration=req.dict(),
            error="Icarus Verilog toolchain (iverilog/vvp) is not available on the server.",
        )

    try:
        with tempfile.TemporaryDirectory(prefix="cpu_verify_") as tmpdir:
            tmp_path = Path(tmpdir)
            branch_file = tmp_path / f"branch_{req.branch_workload}.txt"
            memory_file = tmp_path / f"memory_{req.cache_workload}.txt"
            exe_branch = tmp_path / "sim_branch.vvp"
            exe_cache = tmp_path / "sim_cache.vvp"

            # 1. Generate Workloads with Seed
            rng = random.Random(req.seed)
            if req.branch_workload == "mostly_taken":
                branch_data = wg.generate_mostly_taken(count=req.branch_count, rng=rng)
            elif req.branch_workload == "mostly_not_taken":
                branch_data = wg.generate_mostly_not_taken(count=req.branch_count, rng=rng)
            elif req.branch_workload == "alternating":
                branch_data = wg.generate_alternating(count=req.branch_count)
            elif req.branch_workload == "loop":
                branch_data = wg.generate_loop_pattern(count=req.branch_count)
            else:
                branch_data = wg.generate_random_branches(count=req.branch_count, rng=rng)

            if req.cache_workload == "high_locality":
                cache_data = wg.generate_high_locality(count=req.memory_count, rng=rng)
            elif req.cache_workload == "sequential":
                cache_data = wg.generate_sequential(count=req.memory_count)
            elif req.cache_workload == "random":
                cache_data = wg.generate_random_memory(count=req.memory_count, rng=rng)
            else:
                cache_data = wg.generate_conflict_workload(count=req.memory_count)

            _save_temp_workload(branch_file, branch_data)
            _save_temp_workload(memory_file, cache_data)

            # 2. Run Python Golden Reference Models
            if req.predictor == "1bit":
                predictor_model = ref.OneBitBranchPredictor()
            else:
                predictor_model = ref.TwoBitBranchPredictor()

            py_branch_events = ref.run_branch_trace(predictor_model, branch_data)
            py_cache_events = ref.run_cache_trace(ref.DirectMappedCache(), cache_data)

            # 3. Compile SystemVerilog RTL
            branch_rtl = RTL_DIR / f"branch_predictor_{req.predictor}.sv"
            branch_tb = TB_DIR / f"branch_predictor_{req.predictor}_tb.sv"
            cmd_compile_b = [
                "iverilog", "-g2012", "-o", str(exe_branch),
                str(branch_rtl), str(branch_tb)
            ]
            res_comp_b = subprocess.run(cmd_compile_b, capture_output=True, text=True, timeout=30)
            if res_comp_b.returncode != 0:
                return VerifyResponse(
                    status="FAIL",
                    configuration=req.dict(),
                    error=f"Branch RTL compilation failed: {res_comp_b.stderr}",
                )

            cache_rtl = RTL_DIR / "direct_mapped_cache.sv"
            cache_tb = TB_DIR / "cache_tb.sv"
            cmd_compile_c = [
                "iverilog", "-g2012", "-o", str(exe_cache),
                str(cache_rtl), str(cache_tb)
            ]
            res_comp_c = subprocess.run(cmd_compile_c, capture_output=True, text=True, timeout=30)
            if res_comp_c.returncode != 0:
                return VerifyResponse(
                    status="FAIL",
                    configuration=req.dict(),
                    error=f"Cache RTL compilation failed: {res_comp_c.stderr}",
                )

            # 4. Run Icarus Simulations via vvp
            cmd_run_b = ["vvp", str(exe_branch), f"+WORKLOAD={branch_file}"]
            res_run_b = subprocess.run(cmd_run_b, capture_output=True, text=True, timeout=30)
            if res_run_b.returncode != 0:
                return VerifyResponse(
                    status="FAIL",
                    configuration=req.dict(),
                    error=f"Branch simulation execution failed: {res_run_b.stderr}",
                )

            cmd_run_c = ["vvp", str(exe_cache), f"+WORKLOAD={memory_file}"]
            res_run_c = subprocess.run(cmd_run_c, capture_output=True, text=True, timeout=30)
            if res_run_c.returncode != 0:
                return VerifyResponse(
                    status="FAIL",
                    configuration=req.dict(),
                    error=f"Cache simulation execution failed: {res_run_c.stderr}",
                )

            # 5. Parse Event Logs
            rtl_branch_events = reg.parse_branch_events(res_run_b.stdout)
            rtl_cache_events = reg.parse_cache_events(res_run_c.stdout)

            # 6. Transaction-by-Transaction Equivalence Check
            mismatch = None
            if len(rtl_branch_events) != len(py_branch_events):
                mismatch = f"Branch count mismatch: RTL produced {len(rtl_branch_events)} events, Python expected {len(py_branch_events)}"
            else:
                for idx, (r_evt, p_evt) in enumerate(zip(rtl_branch_events, py_branch_events)):
                    if r_evt["actual"] != p_evt["actual"] or r_evt["prediction"] != p_evt["prediction"]:
                        mismatch = f"Branch mismatch at event {idx+1}: RTL pred {r_evt['prediction']}, Python expected {p_evt['prediction']}"
                        break

            if not mismatch:
                if len(rtl_cache_events) != len(py_cache_events):
                    mismatch = f"Cache count mismatch: RTL produced {len(rtl_cache_events)} events, Python expected {len(py_cache_events)}"
                else:
                    for idx, (r_evt, p_evt) in enumerate(zip(rtl_cache_events, py_cache_events)):
                        if r_evt["hit"] != p_evt["hit"]:
                            mismatch = f"Cache mismatch at event {idx+1} (addr {r_evt['address']}): RTL hit {r_evt['hit']}, Python expected {p_evt['hit']}"
                            break

            # Calculate Branch Metrics
            branch_total = len(py_branch_events)
            branch_correct = sum(1 for e in py_branch_events if e["prediction"] == e["actual"])
            branch_mispredictions = branch_total - branch_correct
            branch_accuracy = round((branch_correct / branch_total * 100.0), 2) if branch_total > 0 else 0.0

            # Calculate Cache Metrics
            cache_total = len(py_cache_events)
            cache_hits = sum(1 for e in py_cache_events if e["hit"] == 1)
            cache_misses = cache_total - cache_hits
            cache_hit_rate = round((cache_hits / cache_total * 100.0), 2) if cache_total > 0 else 0.0

            # Calculate Performance Metrics
            perf_res = calculate_performance(
                instructions=req.instructions,
                base_cpi=req.base_cpi,
                branch_penalty=req.branch_penalty,
                cache_miss_penalty=req.cache_miss_penalty,
                branch_mispredictions=branch_mispredictions,
                cache_misses=cache_misses,
            )

            status_str = "PASS" if not mismatch else "FAIL"

            return VerifyResponse(
                status=status_str,
                configuration=req.dict(),
                branch=BranchVerifyResult(
                    verified=(status_str == "PASS"),
                    total=branch_total,
                    correct=branch_correct,
                    mispredictions=branch_mispredictions,
                    accuracy=branch_accuracy,
                ),
                cache=CacheVerifyResult(
                    verified=(status_str == "PASS"),
                    total=cache_total,
                    hits=cache_hits,
                    misses=cache_misses,
                    hit_rate=cache_hit_rate,
                ),
                performance=PerformanceResult(**perf_res),
                mismatch_detail=mismatch,
            )

    except Exception as exc:
        return VerifyResponse(
            status="FAIL",
            configuration=req.dict(),
            error=f"Verification execution error: {str(exc)}",
        )


def execute_baseline_regression(req: RegressionRequest) -> RegressionResponse:
    """Executes the standard 14-case regression suite using temporary workloads."""
    tc = check_toolchain_availability()
    if not (tc["iverilog"] and tc["vvp"]):
        return RegressionResponse(
            status="ERROR", cases=0, passed=0, failed=0, verified_events=0, results=[],
            error="Toolchain unavailable"
        )

    try:
        # 1. Generate workloads for requested seed and counts
        wg.generate_all_workloads(
            branch_count=req.branch_count,
            memory_count=req.memory_count,
            seed=req.seed,
            output_dir=REPO_ROOT / "workloads",
            verbose=False
        )

        # 2. Run 14-case regression suite
        all_results, overall_pass = reg.run_full_regression(
            component="all",
            verbose=False,
            save_csv=False
        )
        passed = sum(1 for r in all_results if r["status"] == "PASS")
        failed = len(all_results) - passed
        events = sum(r["total_events"] for r in all_results)

        return RegressionResponse(
            status="PASS" if overall_pass else "FAIL",
            cases=len(all_results),
            passed=passed,
            failed=failed,
            verified_events=events,
            results=all_results,
        )
    except Exception as exc:
        return RegressionResponse(
            status="ERROR", cases=0, passed=0, failed=0, verified_events=0, results=[],
            error=str(exc)
        )


def execute_stress_regression(req: StressRequest) -> StressResponse:
    """Executes multi-seed stress regression across specified seed range."""
    tc = check_toolchain_availability()
    if not (tc["iverilog"] and tc["vvp"]):
        return StressResponse(
            status="ERROR", seeds_tested=0, total_cases=0, passed=0, failed=0, verified_events=0,
            error="Toolchain unavailable"
        )

    total_cases = 0
    passed_cases = 0
    failed_cases = 0
    total_events = 0

    try:
        for seed in range(req.start_seed, req.start_seed + req.num_seeds):
            wg.generate_all_workloads(
                branch_count=req.branch_count,
                memory_count=req.memory_count,
                seed=seed,
                output_dir=REPO_ROOT / "workloads",
                verbose=False
            )
            all_results, overall_pass = reg.run_full_regression(
                component="all",
                verbose=False,
                save_csv=False
            )
            t_c = len(all_results)
            p_c = sum(1 for r in all_results if r["status"] == "PASS")
            f_c = t_c - p_c
            e_c = sum(r["total_events"] for r in all_results)

            total_cases += t_c
            passed_cases += p_c
            failed_cases += f_c
            total_events += e_c

        status = "PASS" if failed_cases == 0 and total_cases > 0 else "FAIL"

        return StressResponse(
            status=status,
            seeds_tested=req.num_seeds,
            total_cases=total_cases,
            passed=passed_cases,
            failed=failed_cases,
            verified_events=total_events,
        )
    except Exception as exc:
        return StressResponse(
            status="ERROR",
            seeds_tested=0,
            total_cases=0,
            passed=0,
            failed=0,
            verified_events=0,
            error=str(exc)
        )


def execute_edge_case_regression() -> EdgeCasesResponse:
    """Executes 31 directed edge-case runs."""
    tc = check_toolchain_availability()
    if not (tc["iverilog"] and tc["vvp"]):
        return EdgeCasesResponse(
            status="ERROR", cases=0, passed=0, failed=0, verified_events=0, results=[],
            error="Toolchain unavailable"
        )

    try:
        import edge_case_regression as ecr
        import reference_models as ref

        branch_paths, memory_paths = ecr.create_directed_workload_files()

        ok_1bit, exe_1bit, err_1bit = reg.compile_simulation(
            "edge_branch_1bit_sim", "rtl/branch_predictor_1bit.sv", "tb/branch_predictor_1bit_tb.sv"
        )
        ok_2bit, exe_2bit, err_2bit = reg.compile_simulation(
            "edge_branch_2bit_sim", "rtl/branch_predictor_2bit.sv", "tb/branch_predictor_2bit_tb.sv"
        )
        ok_cache, exe_cache, err_cache = reg.compile_simulation(
            "edge_cache_sim", "rtl/direct_mapped_cache.sv", "tb/cache_tb.sv"
        )

        if not (ok_1bit and ok_2bit and ok_cache):
            return EdgeCasesResponse(
                status="ERROR", cases=0, passed=0, failed=0, verified_events=0, results=[],
                error=f"Edge cases compilation failed: 1bit={err_1bit}, 2bit={err_2bit}, cache={err_cache}"
            )

        edge_results = []
        # 1-Bit Branch (11 cases)
        for case_name, filepath in branch_paths.items():
            res = ecr.run_directed_branch_case(
                "branch_predictor_1bit", exe_1bit, case_name, filepath, ref.OneBitBranchPredictor
            )
            edge_results.append(res)

        # 2-Bit Branch (11 cases)
        for case_name, filepath in branch_paths.items():
            res = ecr.run_directed_branch_case(
                "branch_predictor_2bit", exe_2bit, case_name, filepath, ref.TwoBitBranchPredictor
            )
            edge_results.append(res)

        # Cache (9 cases)
        for case_name, filepath in memory_paths.items():
            res = ecr.run_directed_cache_case(
                "direct_mapped_cache", exe_cache, case_name, filepath
            )
            edge_results.append(res)

        passed = sum(1 for r in edge_results if r["status"] == "PASS")
        failed = len(edge_results) - passed
        events = sum(r["total_events"] for r in edge_results)
        status_str = "PASS" if failed == 0 and len(edge_results) > 0 else "FAIL"

        return EdgeCasesResponse(
            status=status_str,
            cases=len(edge_results),
            passed=passed,
            failed=failed,
            verified_events=events,
            results=edge_results,
        )
    except Exception as exc:
        return EdgeCasesResponse(
            status="ERROR", cases=0, passed=0, failed=0, verified_events=0, results=[],
            error=str(exc)
        )
