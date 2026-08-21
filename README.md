# CPU Microarchitecture Performance Verification

## Overview

This project implements, verifies, and analyzes fundamental CPU microarchitectural sub-blocks—specifically **1-bit** and **2-bit dynamic branch predictors** and a **direct-mapped cache**—using **SystemVerilog** for hardware modeling and **Python** for verification infrastructure. 

The framework features automated synthetic workload generation, software golden reference models, event-by-event co-verification regression testing via Icarus Verilog (`iverilog` / `vvp`), and an analytical performance analyzer that evaluates prediction accuracy, cache hit rates, and Estimated CPI. This repository isolates core microarchitecture components to study hardware design trade-offs and verification methodologies without the overhead of a full CPU core.

## What This Project Demonstrates

- **SystemVerilog RTL Hardware Modeling**: Clean, synthesizable SystemVerilog implementations of dynamic branch predictors and direct-mapped cache memory structures.
- **Verification & Testbench Development**: Race-free, cycle-accurate SystemVerilog testbenches supporting both interactive manual debug and file-driven regression modes.
- **Software Golden Reference Models**: Object-oriented Python reference models (`OneBitBranchPredictor`, `TwoBitBranchPredictor`, `DirectMappedCache`) used as independent behavioral specifications.
- **Automated Co-Verification Regression**: Full automation compiling RTL, executing simulations with trace plusargs (`+WORKLOAD`), parsing machine-readable event streams (`REG_BRANCH`, `REG_CACHE`), and verifying 100% transaction-level equivalence.
- **Workload-Driven Performance Analysis**: Data-driven evaluation across diverse synthetic branch and memory traces, computing analytical Estimated CPI and component penalty trade-offs.
- **Simulation Timing & Debugging**: Diagnosis and resolution of delta-cycle race conditions in SystemVerilog testbenches.
- **Clean Repository Architecture**: Professional project structure following industry hardware verification conventions.

## Architecture

The diagram below illustrates the co-verification pipeline connecting Python tooling and SystemVerilog RTL execution:

```text
               +----------------------------------+
               |     Python Workload Generator    |
               |  (scripts/workload_generator.py) |
               +-----------------+----------------+
                                 |
                                 v
                       +-------------------+
                       |  Workload Files   |
                       | (workloads/*/*.txt|
                       +---------+---------+
                                 |
           +---------------------+---------------------+
           |                                           |
           v                                           v
+-----------------------+                   +--------------------+
|  SystemVerilog RTL &  |                   |   Python Golden    |
|      Testbenches      |                   |  Reference Models  |
|  (rtl/*, tb/*_tb.sv)  |                   | (scripts/ref_...py)|
+----------+------------+                   +----------+---------+
           |                                           |
           v                                           |
+-----------------------+                              |
| Icarus Verilog (vvp)  |                              |
+----------+------------+                              |
           |                                           |
           v                                           v
+-----------------------+                   +--------------------+
| Machine-Readable Logs |                   | Golden Transaction |
| (REG_BRANCH/REG_CACHE)|                   |   Event Records    |
+----------+------------+                   +----------+---------+
           |                                           |
           +---------------------+---------------------+
                                 |
                                 v
                   +---------------------------+
                   |  Event-by-Event Checking  |
                   |   (scripts/regression.py) |
                   +-------------+-------------+
                                 |
                                 v
                   +---------------------------+
                   |   Regression Summary CSV  |
                   | (results/reg_results.csv) |
                   +-------------+-------------+
                                 |
                                 v
                   +---------------------------+
                   |    Performance Analyzer   |
                   | (scripts/perf_analyzer.py)|
                   +-------------+-------------+
                                 |
                                 v
                   +---------------------------+
                   |  Estimated CPI Report     |
                   | (results/perf_report.txt) |
                   +---------------------------+
```

Both SystemVerilog RTL simulations and Python golden reference models independently consume identical synthetic trace workloads. The regression runner compares outputs transaction-by-transaction to confirm functional equivalence before reporting regression status.

## Implemented Components

### 1-Bit Dynamic Branch Predictor
- **Module**: [`rtl/branch_predictor_1bit.sv`](file:///e:/cpu-microarchitecture-performance-verification/rtl/branch_predictor_1bit.sv)
- **Concept**: Single-bit dynamic predictor where `prediction = previous_actual_outcome`.
- **Reset**: Initializes state to Taken (`1'b1`).
- **Behavior**: Updates stored state to `actual_taken` on every rising clock edge.

### 2-Bit Saturating Branch Predictor
- **Module**: [`rtl/branch_predictor_2bit.sv`](file:///e:/cpu-microarchitecture-performance-verification/rtl/branch_predictor_2bit.sv)
- **Concept**: 2-bit saturating counter implementing state hysteresis to prevent transient branch anomalies from flipping prediction state.
- **State Encoding**:
  - `00`: Strongly Not Taken (Predict `0`)
  - `01`: Weakly Not Taken (Predict `0`)
  - `10`: Weakly Taken (Predict `1`)
  - `11`: Strongly Taken (Predict `1`)
- **Reset**: Initializes state to Strongly Taken (`2'b11`).
- **Transitions**: Saturating increment towards `11` on Taken (`1`); saturating decrement towards `00` on Not Taken (`0`). Driven combinationally by MSB `state[1]`.

### Direct-Mapped Cache
- **Module**: [`rtl/direct_mapped_cache.sv`](file:///e:/cpu-microarchitecture-performance-verification/rtl/direct_mapped_cache.sv)
- **Configuration**: 16-bit address space, 4 cache lines (2 index bits), 4-byte block size (2 offset bits), 12 tag bits (`[15:4] Tag | [3:2] Index | [1:0] Offset`).
- **Storage**: Contains `valid` bit array and `tag` array per cache line (data array omitted as access behavior is the primary metric).
- **Behavior**: Evaluates hit combinationally (`valid[index] && tag[index] == incoming_tag`); updates valid bit and tag sequentially on clock edge during misses or accesses.

## Workloads

Synthetic trace workloads are generated by [`scripts/workload_generator.py`](file:///e:/cpu-microarchitecture-performance-verification/scripts/workload_generator.py) (1,000 entries per workload file):

### Branch Workloads ([`workloads/branches/`](file:///e:/cpu-microarchitecture-performance-verification/workloads/branches))
- **Mostly Taken**: ~90% Taken outcomes. Evaluates steady-state loop execution.
- **Mostly Not Taken**: ~90% Not Taken outcomes. Tests baseline performance for biased non-branching code.
- **Alternating**: Deterministic `1, 0, 1, 0...` pattern. Stresses 1-bit and 2-bit state stability.
- **Loop Pattern**: Repeating 5 Taken branches followed by 1 Not Taken exit branch. Stresses loop exit penalties.
- **Random**: Uniform 50/50 probability distribution of Taken and Not Taken outcomes.

### Memory Workloads ([`workloads/memory/`](file:///e:/cpu-microarchitecture-performance-verification/workloads/memory))
- **High Locality**: Repeated accesses to a 4-address working set (`0, 4, 8, 12`). Tests temporal and spatial locality.
- **Sequential**: Linear streaming memory addresses with 4-byte stride (`0, 4, 8, 12, 16...`). Tests compulsory cold misses vs spatial block reuse.
- **Random**: Random 4-byte aligned 16-bit memory addresses. Evaluates un-clustered memory behavior.
- **Conflict**: Addresses aliasing to the exact same cache index (`Index = address[3:2]`) separated by 16-byte strides (`0, 16, 32, 48...`), inducing continuous conflict evictions.

*Why Targeted Workloads*: Targeted synthetic traces isolate specific architectural corner cases (such as loop exit penalties and index aliasing) far more effectively than generic random testing.

## Verification Methodology

1. **Deterministic Workload Generation**: Python generates repeatable, seeded trace files.
2. **Dual-Path Execution**: Trace files are fed simultaneously to SystemVerilog RTL via `+WORKLOAD=<path>` testbench plusargs and Python golden models (`scripts/reference_models.py`).
3. **Machine-Readable Delimited Logging**: Testbenches output structured event lines (`REG_BRANCH,<num>,<pred>,<actual>` and `REG_CACHE,<num>,<addr>,<hit>`).
4. **Transaction-by-Transaction Comparison**: [`scripts/regression.py`](file:///e:/cpu-microarchitecture-performance-verification/scripts/regression.py) compares every individual simulation event against software golden model records.
5. **Strict PASS/FAIL Criteria**: A test case passes **only if 100% of event records match**. Overall percentage metrics alone are never used to determine correctness.

**Regression Status**: **14 / 14 Cases PASS** (10 branch cases, 4 cache cases).

## Verified Results

### Branch Predictor Results

| Workload | 1-bit Predictor Accuracy | 2-bit Predictor Accuracy |
| :--- | ---: | ---: |
| **Mostly Taken** | 79.80% | **88.50%** |
| **Mostly Not Taken** | 83.70% | **90.30%** |
| **Alternating** | 0.10% | **50.00%** |
| **Loop** | 66.80% | **83.40%** |
| **Random** | 49.20% | **49.70%** |

#### Key Observations
- **Loop Hysteresis Advantage**: The 2-bit predictor improves loop workload accuracy by **+16.60 percentage points** (83.40% vs 66.80%) because transitioning from `11` to `10` on loop exit preserves a `Taken` prediction for loop re-entry.
- **Alternating Pathological Case**: The 1-bit predictor fails completely on alternating patterns (0.10% accuracy) due to state flipping after every branch, whereas the 2-bit predictor settles into a neutral state yielding 50.00% accuracy.
- **Random Baseline**: Both predictors perform at ~50% (chance level) under random branch noise.

### Cache Results

| Workload | Hit Rate |
| :--- | ---: |
| **High Locality** | **99.60%** |
| **Sequential** | **0.00%** |
| **Random** | **0.10%** |
| **Conflict** | **0.00%** |

#### Key Observations
- **High Locality Dominance**: High-locality accesses achieve 99.60% hit rate because the 4-address working set fits perfectly into the 4-line cache after 4 compulsory cold misses.
- **Compulsory Cold Misses on Streaming**: Sequential streaming with a stride of 4 bytes achieves 0.00% hit rate because every access hits a new 4-byte block (compulsory cold miss in a single-word-line cache).
- **Index Conflict Thrashing**: Conflict workload addresses (`0, 16, 32, 48`) all alias to `Index 0` (`address[3:2] == 2'b00`), causing 100% conflict miss thrashing.

## Estimated Performance Model

System performance is evaluated using an analytical stall-penalty model implemented in [`scripts/performance_analyzer.py`](file:///e:/cpu-microarchitecture-performance-verification/scripts/performance_analyzer.py):

$$\text{Base Instruction Cycles} = \text{Instructions} \times \text{Base CPI}$$

$$\text{Extra Branch Cycles} = \text{Branch Mispredictions} \times \text{Branch Penalty}$$

$$\text{Extra Cache Cycles} = \text{Cache Misses} \times \text{Cache Miss Penalty}$$

$$\text{Estimated Total Cycles} = \text{Base Instruction Cycles} + \text{Extra Branch Cycles} + \text{Extra Cache Cycles}$$

$$\text{Estimated CPI} = \frac{\text{Estimated Total Cycles}}{\text{Instructions}}$$

### Verified Default Scenario
- **Scenario Configuration**: 2-bit Predictor, `loop` branch workload (166 mispredicts), `high_locality` cache workload (4 misses).
- **Model Parameters**: 10,000 Modeled Instructions, Base CPI = 1.0, Branch Mispredict Penalty = 3 cycles, Cache Miss Penalty = 10 cycles.

$$\text{Base Cycles} = 10000 \times 1.0 = 10000.0$$

$$\text{Extra Branch Cycles} = 166 \times 3 = 498.0$$

$$\text{Extra Cache Cycles} = 4 \times 10 = 40.0$$

$$\text{Estimated Total Cycles} = 10000.0 + 498.0 + 40.0 = 10538.0$$

$$\text{Estimated CPI} = \frac{10538.0}{10000} = \mathbf{1.0538}$$

**Important**: *Estimated CPI is a simplified analytical metric and is NOT measured real CPU CPI. Branch and memory traces originate from independent synthetic workloads.*

## Repository Structure

```text
cpu-microarchitecture-performance-verification/
├── rtl/                                    # SystemVerilog RTL modules
│   ├── branch_predictor_1bit.sv            # 1-bit dynamic branch predictor
│   ├── branch_predictor_2bit.sv            # 2-bit saturating counter branch predictor
│   └── direct_mapped_cache.sv              # 4-line direct-mapped cache
├── tb/                                     # SystemVerilog testbenches
│   ├── branch_predictor_1bit_tb.sv         # 1-bit predictor testbench (+WORKLOAD support)
│   ├── branch_predictor_2bit_tb.sv         # 2-bit predictor testbench (+WORKLOAD support)
│   └── cache_tb.sv                         # Cache testbench (+WORKLOAD support)
├── scripts/                                # Python verification & analysis tooling
│   ├── workload_generator.py               # Synthetic workload generator
│   ├── reference_models.py                 # Software golden reference models
│   ├── regression.py                       # Automated RTL vs Python regression runner
│   ├── stress_regression.py                # Multi-seed randomized stress regression runner
│   ├── edge_case_regression.py             # Directed edge-case verification runner
│   └── performance_analyzer.py             # Performance analyzer & Estimated CPI calculator
├── workloads/                              # Synthetic workload traces
│   ├── branches/                           # Branch trace files (*.txt)
│   ├── memory/                             # Memory address trace files (*.txt)
│   └── edge_cases/                         # Directed edge-case trace files
├── results/                                # Output reports and regression data
│   ├── regression_results.csv              # Machine-readable regression test results
│   ├── stress_regression_results.csv       # Multi-seed stress regression results
│   ├── edge_case_results.csv               # Directed edge-case regression results
│   └── performance_report.txt              # Formatted analytical performance report
├── docs/                                   # Project documentation & interview guides
│   ├── project_learning_log.md             # Comprehensive development & study log
│   ├── interview_guide.md                  # 25 Q&A interview revision guide
│   └── results_summary.md                  # Concise verified results summary
├── .gitignore                              # Git ignore rules (build artifacts ignored)
└── README.md                               # Primary project documentation
```

## How to Run

### Prerequisites
- **Python 3.8+**
- **Icarus Verilog (`iverilog`, `vvp`)**
- **Git**
- *GTKWave* (Optional for manual VCD waveform inspection)

### 1. Generate Synthetic Workloads
```bash
python scripts/workload_generator.py
```

### 2. Run Automated Regression Suite (14 Cases)
```bash
python scripts/regression.py
```

### 3. Run Multi-Seed Stress Regression
```bash
python scripts/stress_regression.py --start-seed 1 --num-seeds 20
```

### 4. Run Directed Edge-Case Regression
```bash
python scripts/edge_case_regression.py
```

### 5. Generate Analytical Performance Report
```bash
python scripts/performance_analyzer.py
```

### 6. Interactive Manual Testbench Runs (Optional)
```bash
# Compile and run 1-bit predictor manual test
iverilog -g2012 -o build/branch_1bit_sim rtl/branch_predictor_1bit.sv tb/branch_predictor_1bit_tb.sv
vvp build/branch_1bit_sim

# Compile and run cache manual test
iverilog -g2012 -o build/cache_sim rtl/direct_mapped_cache.sv tb/cache_tb.sv
vvp build/cache_sim
```

## Interesting Debugging Case Study

### Testbench Delta-Cycle Timing Race Condition
During initial Phase 3 cache verification, the testbench reported an unexpected `6 Hits / 1 Miss` outcome on a 7-access trace where Address 4 was reported as a `HIT` even when the cache line `valid` bit was `0`.

- **Root Cause**: The testbench drove `address` and `access_valid` on `negedge clk` and sampled the combinational `hit` signal immediately in the exact same simulation delta cycle. Because combinational assignment propagation requires simulator delta cycles (`address -> index/tag extraction -> hit equality check`), `hit` was sampled prior to signal propagation, reading stale values from previous iterations.
- **Resolution**: Added a `#1;` time step delay after driving inputs on `negedge clk` to allow combinational logic to settle before sampling `hit`. The RTL implementation required zero code changes, reinforcing the principle that simulation failures do not automatically imply hardware RTL defects.

## Scope & Limitations

- **Not a Full CPU**: Isolates standalone microarchitecture sub-blocks (branch predictors and caches); does not implement a full instruction pipeline, decoder, register file, or ALU.
- **Tag-Only Cache**: Models valid bits and tag registers to measure hit/miss access rates; data storage arrays and bus interfaces are omitted.
- **Analytical Performance Metric**: Estimated CPI is derived from an analytical stall-penalty model applied to standalone component stats, not measured from a cycle-accurate physical CPU core.
- **Independent Traces**: Branch and memory traces originate from independent synthetic generators rather than instruction execution traces.

## Development Status

```text
Phase 1 — 1-bit branch predictor       PASS
Phase 2 — 2-bit branch predictor       PASS
Phase 3 — Direct-mapped cache          PASS
Phase 4 — Workload generator           PASS
Phase 5 — Python reference models      PASS
Phase 6 — Regression runner            PASS
Phase 7 — Performance analyzer         PASS
Phase 8 — Final documentation/polish   COMPLETE
Phase 9A — Multi-seed stress runner    PASS
```

## Resume Description

- Built a SystemVerilog/Python CPU microarchitecture verification framework modeling 1-bit/2-bit branch predictors and a direct-mapped cache, with event-level RTL checking against software golden models across 14 automated regression scenarios.
- Developed deterministic workload generation and performance analysis to compare branch prediction accuracy, cache hit rates, and simplified Estimated CPI using Icarus Verilog simulation outputs.

## Interview Summary (30-Second Overview)

> *"I built a CPU microarchitecture verification framework using SystemVerilog models for 1-bit and 2-bit branch predictors and a direct-mapped cache. Python generates targeted workloads, runs Icarus simulations, compares RTL outputs event-by-event against independent software golden models, runs 14 regression cases, and analyzes predictor accuracy, cache hit rate, and a simplified Estimated CPI."*
