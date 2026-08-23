#!/usr/bin/env python3
"""
Verification Engine for CPU Microarchitecture Performance Verification.

Provides programmatic APIs for executing arbitrary in-memory branch traces and
memory address traces through real SystemVerilog RTL modules (compiled via iverilog)
and verifying output correctness transaction-by-transaction against software golden models.

RTL Cache Parameters (Fixed in Hardware):
  - Cache Lines: 4
  - Block Size: 4 Bytes
  - Address Space: 16-bit (0x0000 to 0xFFFF / 0 to 65535)

Standard Library Only.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

# Locate repository root and scripts directory
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
RTL_DIR = REPO_ROOT / "rtl"
TB_DIR = REPO_ROOT / "tb"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import reference_models as ref
import regression as reg

MAX_CUSTOM_BRANCH_EVENTS = 5000
MAX_CUSTOM_MEMORY_EVENTS = 5000


# ============================================================================
# Toolchain & System Utilities
# ============================================================================

def check_verification_toolchain() -> Dict[str, bool]:
    """Checks if iverilog and vvp simulation tools are available in system PATH."""
    return {
        "iverilog": shutil.which("iverilog") is not None,
        "vvp": shutil.which("vvp") is not None,
    }


# ============================================================================
# Trace Normalization Utilities
# ============================================================================

def normalize_branch_trace(trace: Any) -> List[int]:
    """
    Normalizes arbitrary branch trace input formats to a list of integers (0 or 1).

    Supported Inputs:
      - String: "T T N T", "T,T,N,T", "1 1 0 1", "1,1,0,1", "T N T T N"
      - List: ["T", "T", "N", "T"], [1, 1, 0, 1], ["1", "0", "1"]

    Rules:
      - T / t / 1 / "1" -> 1 (Taken)
      - N / n / 0 / "0" -> 0 (Not Taken)

    Raises:
      ValueError if trace is empty, malformed, contains invalid tokens, or exceeds max length.
    """
    if trace is None or (isinstance(trace, (list, str)) and len(trace) == 0):
        raise ValueError("Branch trace cannot be empty.")

    raw_tokens: List[str] = []

    if isinstance(trace, str):
        parts = re.split(r"[\s,;]+", trace.strip())
        raw_tokens = [p for p in parts if p]
    elif isinstance(trace, list):
        for item in trace:
            if isinstance(item, int):
                raw_tokens.append(str(item))
            elif isinstance(item, str):
                raw_tokens.append(item.strip())
            else:
                raise ValueError(f"Invalid branch token type '{type(item).__name__}': {item}")
    else:
        raise ValueError(f"Unsupported branch trace type '{type(trace).__name__}'. Expected string or list.")

    if not raw_tokens:
        raise ValueError("Branch trace contains no valid tokens.")

    if len(raw_tokens) > MAX_CUSTOM_BRANCH_EVENTS:
        raise ValueError(f"Branch trace length {len(raw_tokens)} exceeds maximum limit of {MAX_CUSTOM_BRANCH_EVENTS} events.")

    normalized: List[int] = []
    for idx, token in enumerate(raw_tokens):
        t_upper = token.upper()
        if t_upper in ("T", "1"):
            normalized.append(1)
        elif t_upper in ("N", "0"):
            normalized.append(0)
        else:
            raise ValueError(f"Invalid branch token '{token}' at position {idx+1}. Must be 'T', 'N', '1', or '0'.")

    return normalized


def normalize_memory_trace(trace: Any) -> List[int]:
    """
    Normalizes arbitrary memory address trace input formats to an integer list (0 to 65535).

    Supported Inputs:
      - String: "0x100 0x104 0x108", "0x100, 0x104", "256 260 264 256"
      - List: ["0x100", "0x104"], [256, 260]

    Validates:
      - 0 <= address <= 65535 (16-bit address space)
      - Supports unaligned addresses (byte offsets verified in Phase 9B)

    Raises:
      ValueError if trace is empty, malformed, outside 16-bit bounds, or exceeds max length.
    """
    if trace is None or (isinstance(trace, (list, str)) and len(trace) == 0):
        raise ValueError("Memory address trace cannot be empty.")

    raw_tokens: List[str] = []

    if isinstance(trace, str):
        parts = re.split(r"[\s,;]+", trace.strip())
        raw_tokens = [p for p in parts if p]
    elif isinstance(trace, list):
        for item in trace:
            if isinstance(item, int):
                raw_tokens.append(str(item))
            elif isinstance(item, str):
                raw_tokens.append(item.strip())
            else:
                raise ValueError(f"Invalid memory token type '{type(item).__name__}': {item}")
    else:
        raise ValueError(f"Unsupported memory trace type '{type(trace).__name__}'. Expected string or list.")

    if not raw_tokens:
        raise ValueError("Memory address trace contains no valid tokens.")

    if len(raw_tokens) > MAX_CUSTOM_MEMORY_EVENTS:
        raise ValueError(f"Memory trace length {len(raw_tokens)} exceeds maximum limit of {MAX_CUSTOM_MEMORY_EVENTS} events.")

    normalized: List[int] = []
    for idx, token in enumerate(raw_tokens):
        try:
            if token.lower().startswith("0x"):
                addr = int(token, 16)
            else:
                addr = int(token, 10)
        except ValueError:
            raise ValueError(f"Invalid address token '{token}' at position {idx+1}. Must be valid integer or hex (e.g. 0x100).")

        if addr < 0 or addr > 65535:
            raise ValueError(f"Address {addr} (token '{token}') at position {idx+1} outside 16-bit range [0, 65535].")

        normalized.append(addr)

    return normalized


# ============================================================================
# Arbitrary Workload Verification APIs
# ============================================================================

def _write_temp_workload_file(filepath: Path, values: List[int]) -> None:
    """Helper to write workload integer values to a text file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        for val in values:
            f.write(f"{val}\n")


def verify_branch_trace(trace: Any, predictor: str = "2bit") -> Dict[str, Any]:
    """
    Executes an arbitrary branch trace through real SystemVerilog predictor RTL and
    compares event-by-event against the software golden model.

    Parameters:
      - trace: Arbitrary branch trace (string or list)
      - predictor: '1bit' or '2bit'

    Returns:
      Structured result dictionary with status, metrics, and detailed event array.
    """
    if predictor not in ("1bit", "2bit"):
        raise ValueError(f"Invalid predictor type '{predictor}'. Must be '1bit' or '2bit'.")

    normalized_trace = normalize_branch_trace(trace)
    toolchain = check_verification_toolchain()
    if not (toolchain["iverilog"] and toolchain["vvp"]):
        return {
            "status": "FAIL",
            "predictor": predictor,
            "verified": False,
            "error": "Icarus Verilog toolchain (iverilog/vvp) is missing or not in PATH.",
        }

    rtl_file = RTL_DIR / f"branch_predictor_{predictor}.sv"
    tb_file = TB_DIR / f"branch_predictor_{predictor}_tb.sv"

    if not rtl_file.exists() or not tb_file.exists():
        return {
            "status": "FAIL",
            "predictor": predictor,
            "verified": False,
            "error": f"RTL or testbench file missing for predictor '{predictor}'.",
        }

    try:
        with tempfile.TemporaryDirectory(prefix="branch_verify_") as tmpdir:
            tmp_path = Path(tmpdir)
            workload_file = tmp_path / "custom_branch_workload.txt"
            sim_exe = tmp_path / "sim_branch.vvp"

            _write_temp_workload_file(workload_file, normalized_trace)

            # 1. Compile SystemVerilog RTL
            cmd_compile = [
                "iverilog", "-g2012", "-o", str(sim_exe),
                str(rtl_file), str(tb_file)
            ]
            res_comp = subprocess.run(cmd_compile, capture_output=True, text=True, timeout=30)
            if res_comp.returncode != 0:
                return {
                    "status": "FAIL",
                    "predictor": predictor,
                    "verified": False,
                    "error": f"RTL compilation error: {res_comp.stderr.strip()}",
                }

            # 2. Run simulation via vvp
            cmd_run = ["vvp", str(sim_exe), f"+WORKLOAD={workload_file}"]
            res_run = subprocess.run(cmd_run, capture_output=True, text=True, timeout=30)
            if res_run.returncode != 0:
                return {
                    "status": "FAIL",
                    "predictor": predictor,
                    "verified": False,
                    "error": f"Simulation runtime error: {res_run.stderr.strip()}",
                }

            # 3. Parse RTL Event Log
            rtl_events = reg.parse_branch_events(res_run.stdout)

            # 4. Run Python Golden Reference Model
            model = ref.OneBitBranchPredictor() if predictor == "1bit" else ref.TwoBitBranchPredictor()
            py_res = ref.run_branch_trace(model, normalized_trace)
            py_events = py_res["events"]

            # 5. Equivalence Comparison
            total = len(normalized_trace)
            if len(rtl_events) != total:
                return {
                    "status": "FAIL",
                    "predictor": predictor,
                    "verified": False,
                    "error": f"Event count mismatch: RTL produced {len(rtl_events)} events, expected {total}.",
                }

            event_details = []
            mismatch_evt = None
            correct_count = 0

            for idx in range(total):
                r_evt = rtl_events[idx]
                p_evt = py_events[idx]

                is_correct_pred = (r_evt["prediction"] == r_evt["actual"])
                if is_correct_pred:
                    correct_count += 1

                is_match = (
                    r_evt["actual"] == p_evt["actual"] and
                    r_evt["prediction"] == p_evt["prediction"]
                )

                evt_obj = {
                    "branch": idx + 1,
                    "actual": r_evt["actual"],
                    "prediction": r_evt["prediction"],
                    "expected_prediction": p_evt["prediction"],
                    "correct": is_correct_pred,
                    "match": is_match,
                }
                event_details.append(evt_obj)

                if not is_match and mismatch_evt is None:
                    mismatch_evt = {
                        "branch": idx + 1,
                        "actual": r_evt["actual"],
                        "rtl_prediction": r_evt["prediction"],
                        "golden_expected": p_evt["prediction"],
                    }

            mispredictions = total - correct_count
            accuracy = round((correct_count / total * 100.0), 2) if total > 0 else 0.0

            if mismatch_evt is not None:
                return {
                    "status": "FAIL",
                    "predictor": predictor,
                    "verified": False,
                    "total": total,
                    "correct": correct_count,
                    "incorrect": mispredictions,
                    "accuracy": accuracy,
                    "first_mismatch": mismatch_evt,
                    "error": f"First mismatch at branch {mismatch_evt['branch']}: RTL pred {mismatch_evt['rtl_prediction']}, Golden expected {mismatch_evt['golden_expected']}",
                    "events": event_details,
                }

            return {
                "status": "PASS",
                "predictor": predictor,
                "verified": True,
                "total": total,
                "correct": correct_count,
                "incorrect": mispredictions,
                "accuracy": accuracy,
                "events": event_details,
            }

    except subprocess.TimeoutExpired:
        return {
            "status": "FAIL",
            "predictor": predictor,
            "verified": False,
            "error": "Simulation execution timed out after 30 seconds.",
        }
    except Exception as exc:
        return {
            "status": "FAIL",
            "predictor": predictor,
            "verified": False,
            "error": f"Unexpected {type(exc).__name__} during branch verification: {str(exc)}",
        }


def compare_branch_predictors(trace: Any) -> Dict[str, Any]:
    """
    Executes the SAME arbitrary branch trace independently through both
    1-bit and 2-bit SystemVerilog predictor RTL modules.

    Returns:
      Combined comparison dictionary with predictor outputs and accuracy delta.
    """
    normalized_trace = normalize_branch_trace(trace)
    res_1bit = verify_branch_trace(normalized_trace, "1bit")
    res_2bit = verify_branch_trace(normalized_trace, "2bit")

    overall_pass = (res_1bit.get("verified", False) and res_2bit.get("verified", False))

    accuracy_delta = 0.0
    if res_1bit.get("status") == "PASS" and res_2bit.get("status") == "PASS":
        accuracy_delta = round(res_2bit["accuracy"] - res_1bit["accuracy"], 2)

    return {
        "status": "PASS" if overall_pass else "FAIL",
        "verified": overall_pass,
        "trace_length": len(normalized_trace),
        "accuracy_delta": accuracy_delta,
        "predictors": {
            "1bit": res_1bit,
            "2bit": res_2bit,
        }
    }


def verify_cache_trace(addresses: Any) -> Dict[str, Any]:
    """
    Executes an arbitrary memory address trace through real direct-mapped cache RTL
    and compares event-by-event against the software golden model.

    RTL Cache Geometry: 4 lines, 4-byte blocks, 16-bit address space.

    Returns:
      Structured result dictionary with hit/miss metrics and detailed event breakdown.
    """
    normalized_addresses = normalize_memory_trace(addresses)
    toolchain = check_verification_toolchain()
    if not (toolchain["iverilog"] and toolchain["vvp"]):
        return {
            "status": "FAIL",
            "verified": False,
            "error": "Icarus Verilog toolchain (iverilog/vvp) is missing or not in PATH.",
        }

    rtl_file = RTL_DIR / "direct_mapped_cache.sv"
    tb_file = TB_DIR / "cache_tb.sv"

    if not rtl_file.exists() or not tb_file.exists():
        return {
            "status": "FAIL",
            "verified": False,
            "error": "Direct-mapped cache RTL or testbench file missing.",
        }

    try:
        with tempfile.TemporaryDirectory(prefix="cache_verify_") as tmpdir:
            tmp_path = Path(tmpdir)
            workload_file = tmp_path / "custom_memory_workload.txt"
            sim_exe = tmp_path / "sim_cache.vvp"

            _write_temp_workload_file(workload_file, normalized_addresses)

            # 1. Compile Cache RTL
            cmd_compile = [
                "iverilog", "-g2012", "-o", str(sim_exe),
                str(rtl_file), str(tb_file)
            ]
            res_comp = subprocess.run(cmd_compile, capture_output=True, text=True, timeout=30)
            if res_comp.returncode != 0:
                return {
                    "status": "FAIL",
                    "verified": False,
                    "error": f"Cache RTL compilation error: {res_comp.stderr.strip()}",
                }

            # 2. Run Simulation
            cmd_run = ["vvp", str(sim_exe), f"+WORKLOAD={workload_file}"]
            res_run = subprocess.run(cmd_run, capture_output=True, text=True, timeout=30)
            if res_run.returncode != 0:
                return {
                    "status": "FAIL",
                    "verified": False,
                    "error": f"Cache simulation runtime error: {res_run.stderr.strip()}",
                }

            # 3. Parse RTL Events
            rtl_events = reg.parse_cache_events(res_run.stdout)

            # 4. Golden Model Execution
            model = ref.DirectMappedCache()
            py_res = ref.run_cache_trace(model, normalized_addresses)
            py_events = py_res["events"]

            # 5. Equivalence Comparison
            total = len(normalized_addresses)
            if len(rtl_events) != total:
                return {
                    "status": "FAIL",
                    "verified": False,
                    "error": f"Cache event count mismatch: RTL produced {len(rtl_events)} events, expected {total}.",
                }

            event_details = []
            mismatch_evt = None
            hits_count = 0

            for idx in range(total):
                r_evt = rtl_events[idx]
                p_evt = py_events[idx]
                addr = normalized_addresses[idx]

                index_val = (addr >> 2) & 0b11
                tag_val = addr >> 4
                is_hit = bool(r_evt["hit"])

                if is_hit:
                    hits_count += 1

                is_match = (bool(r_evt["hit"]) == bool(p_evt["hit"]) and r_evt["address"] == p_evt["address"])

                evt_obj = {
                    "access": idx + 1,
                    "address": addr,
                    "address_hex": f"0x{addr:04X}",
                    "index": index_val,
                    "tag": tag_val,
                    "hit": is_hit,
                    "expected_hit": bool(p_evt["hit"]),
                    "match": is_match,
                }
                event_details.append(evt_obj)

                if not is_match and mismatch_evt is None:
                    mismatch_evt = {
                        "access": idx + 1,
                        "address": addr,
                        "rtl_hit": is_hit,
                        "golden_expected_hit": bool(p_evt["hit"]),
                    }

            misses_count = total - hits_count
            hit_rate = round((hits_count / total * 100.0), 2) if total > 0 else 0.0
            miss_rate = round(100.0 - hit_rate, 2)

            if mismatch_evt is not None:
                return {
                    "status": "FAIL",
                    "verified": False,
                    "total": total,
                    "hits": hits_count,
                    "misses": misses_count,
                    "hit_rate": hit_rate,
                    "miss_rate": miss_rate,
                    "first_mismatch": mismatch_evt,
                    "error": f"First mismatch at access {mismatch_evt['access']} (addr {mismatch_evt['address']}): RTL hit {mismatch_evt['rtl_hit']}, Golden expected {mismatch_evt['golden_expected_hit']}",
                    "events": event_details,
                }

            return {
                "status": "PASS",
                "verified": True,
                "total": total,
                "hits": hits_count,
                "misses": misses_count,
                "hit_rate": hit_rate,
                "miss_rate": miss_rate,
                "events": event_details,
            }

    except subprocess.TimeoutExpired:
        return {
            "status": "FAIL",
            "verified": False,
            "error": "Simulation execution timed out after 30 seconds.",
        }
    except Exception as exc:
        return {
            "status": "FAIL",
            "verified": False,
            "error": f"Unexpected {type(exc).__name__} during cache verification: {str(exc)}",
        }


# ============================================================================
# Analytical Performance Helper
# ============================================================================

def calculate_estimated_performance(
    instructions: int,
    base_cpi: float,
    branch_mispredictions: int,
    cache_misses: int,
    branch_penalty: int = 3,
    cache_miss_penalty: int = 10,
) -> Dict[str, Any]:
    """
    Calculates analytical Estimated CPI using stall penalties from component metrics.

    Validation:
      - instructions > 0
      - base_cpi > 0
      - branch_penalty >= 0
      - cache_miss_penalty >= 0
      - branch_mispredictions >= 0
      - cache_misses >= 0

    Returns:
      Dictionary with cycle breakdown and Estimated CPI.
    """
    if instructions <= 0:
        raise ValueError("Instruction count must be greater than 0.")
    if base_cpi <= 0.0:
        raise ValueError("Base CPI must be greater than 0.0.")
    if branch_penalty < 0 or cache_miss_penalty < 0:
        raise ValueError("Stall penalties cannot be negative.")
    if branch_mispredictions < 0 or cache_misses < 0:
        raise ValueError("Misprediction and miss counts cannot be negative.")

    base_cycles = float(instructions) * float(base_cpi)
    branch_penalty_cycles = float(branch_mispredictions) * float(branch_penalty)
    cache_penalty_cycles = float(cache_misses) * float(cache_miss_penalty)

    estimated_total_cycles = base_cycles + branch_penalty_cycles + cache_penalty_cycles
    estimated_cpi = estimated_total_cycles / float(instructions)

    return {
        "instructions": instructions,
        "base_cpi": base_cpi,
        "branch_penalty": branch_penalty,
        "cache_miss_penalty": cache_miss_penalty,
        "branch_mispredictions": branch_mispredictions,
        "cache_misses": cache_misses,
        "base_cycles": round(base_cycles, 2),
        "branch_penalty_cycles": round(branch_penalty_cycles, 2),
        "cache_penalty_cycles": round(cache_penalty_cycles, 2),
        "estimated_total_cycles": round(estimated_total_cycles, 2),
        "estimated_cpi": round(estimated_cpi, 4),
    }
