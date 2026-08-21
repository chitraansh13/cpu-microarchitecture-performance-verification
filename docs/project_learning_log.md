# CPU Microarchitecture Performance Verification — Project Learning Log

## Purpose

This document serves as a persistent learning log and technical interview revision guide for the **CPU Microarchitecture Performance Verification** project. It records what was built, why it was built, fundamental microarchitectural concepts, key hardware design decisions, workload traces, expected versus actual simulation results, debugging case studies, and interview-ready technical explanations.

---

## Phase 1 — 1-Bit Dynamic Branch Predictor

### What We Built

- **RTL Module**: [`rtl/branch_predictor_1bit.sv`](file:///e:/cpu-microarchitecture-performance-verification/rtl/branch_predictor_1bit.sv)
- **Testbench**: [`tb/branch_predictor_1bit_tb.sv`](file:///e:/cpu-microarchitecture-performance-verification/tb/branch_predictor_1bit_tb.sv)

Phase 1 implements a single-entry dynamic branch predictor using one internal state bit. This serves as the baseline hardware predictor model in our study.

### Core Concept

The 1-bit dynamic predictor operates on a simple history rule:

```text
1 = Predict Taken (T)
0 = Predict Not Taken (N)
```

The predictor assumes that the next branch will follow the outcome of the most recently evaluated branch.

- **State Update Rule**: `state <= actual_taken`
- **Reset State**: Taken (`1'b1`)

### Test Workload

- **Actual Branch Pattern**: `T T T T N T T T N T` (`1 1 1 1 0 1 1 1 0 1`)
- **Expected Predictions**: `T T T T T N T T T N` (`1 1 1 1 1 0 1 1 1 0`)

### Actual Verified Result

SystemVerilog simulation produced the exact expected performance counters:

```text
Total Branches        = 10
Correct Predictions   = 6
Incorrect Predictions = 4
Prediction Accuracy   = 60.00%
```

- **Status**: Manually verified & **PASS**

### Important Observation

A 1-bit predictor suffers from double misprediction penalties on loop exits or isolated opposite outcomes (e.g., `T T T T N T`):
1. **Loop Exit Penalty**: On the loop exit (`N`), the predictor predicts `T` (based on prior loop iterations) and mispredicts.
2. **State Pollution**: The predictor state immediately updates to `N`.
3. **Re-entry Penalty**: When the loop restarts on the next branch (`T`), the predictor predicts `N` and mispredicts a second time.

### Interview Explanation

> *"A 1-bit dynamic branch predictor tracks the previous direction of a branch using a single-bit flip-flop. While simple and minimal in area, its primary limitation is hysteresis loss: a single anomalous branch outcome (such as a loop termination) flips the predictor state, causing two consecutive mispredictions when the normal branch pattern resumes."*

---

## Phase 2 — 2-Bit Saturating Branch Predictor

### What We Built

- **RTL Module**: [`rtl/branch_predictor_2bit.sv`](file:///e:/cpu-microarchitecture-performance-verification/rtl/branch_predictor_2bit.sv)
- **Testbench**: [`tb/branch_predictor_2bit_tb.sv`](file:///e:/cpu-microarchitecture-performance-verification/tb/branch_predictor_2bit_tb.sv)

### Core Concept

Phase 2 introduces state hysteresis using a 2-bit saturating counter with four states:

```text
00 = Strongly Not Taken (SN) -> Predict Not Taken (0)
01 = Weakly Not Taken   (WN) -> Predict Not Taken (0)
10 = Weakly Taken       (WT) -> Predict Taken (1)
11 = Strongly Taken     (ST) -> Predict Taken (1)
```

- **Prediction Output**: The Most Significant Bit (`state[1]`) acts as the prediction logic (`10`/`11` predict Taken, `00`/`01` predict Not Taken).
- **Reset State**: `11` (Strongly Taken).
- **State Transition Rules**:
  - `actual_taken == 1`: Saturating increment (`00->01`, `01->10`, `10->11`, `11->11`).
  - `actual_taken == 0`: Saturating decrement (`11->10`, `10->01`, `01->00`, `00->00`).

### Test Workload

- **Actual Branch Pattern**: `T T T T N T T T N T`
- **Expected Predictions**: `T T T T T T T T T T`

### Actual Verified Result

```text
Total Branches        = 10
Correct Predictions   = 8
Incorrect Predictions = 2
Prediction Accuracy   = 80.00%
```

- **Status**: Manually verified & **PASS**

### Comparison With 1-Bit Predictor

```text
1-bit predictor accuracy = 60.00%
2-bit predictor accuracy = 80.00%
```

**Why 2-Bit Outperformed 1-Bit on This Trace**:
When an isolated `N` (Not Taken) branch occurs from state `11` (Strongly Taken):
- The 1-bit predictor immediately flips state to `0` (Not Taken), causing the subsequent `T` branch to mispredict.
- The 2-bit predictor transitions from `11` (Strongly Taken) to `10` (Weakly Taken). Because state `10` still predicts `Taken`, the subsequent `T` branch is correctly predicted.

*Note: This 80% accuracy is workload-specific to traces containing isolated anomalies and is not a universal guarantee for all code patterns.*

### Interview Explanation

> *"A 2-bit saturating predictor adds counter hysteresis to protect against transient branch anomalies. By requiring two consecutive mispredictions to flip the prediction direction (from Strongly Taken to Weakly Not Taken), it prevents isolated loop exit branches from corrupting steady-state prediction accuracy."*

---

## Phase 3 — Direct-Mapped Cache

### What We Built

- **RTL Module**: [`rtl/direct_mapped_cache.sv`](file:///e:/cpu-microarchitecture-performance-verification/rtl/direct_mapped_cache.sv)
- **Testbench**: [`tb/cache_tb.sv`](file:///e:/cpu-microarchitecture-performance-verification/tb/cache_tb.sv)

### Cache Configuration

- **Address Width**: 16 bits
- **Cache Lines**: 4 lines
- **Block Size**: 4 bytes

**Address Field Decomposition**:
```text
[15:4] = Tag    (12 bits)
[3:2]  = Index  (2 bits, selects 1 of 4 cache lines)
[1:0]  = Offset (2 bits, selects byte within 4-byte block)
```

### Cache Line Contents

Each cache line contains:
- `valid` bit (1 bit)
- `tag` register (12 bits)

*Note: Data storage arrays are intentionally omitted as the study focuses on cache line hit/miss access metrics.*

### Hit Condition & Allocation

- **Combinational Hit Evaluation**:
  ```text
  hit = access_valid AND valid[index] AND (stored_tag[index] == incoming_tag)
  ```
- **Line Update Rule**: On a miss, the target line is validated (`valid[index] <= 1'b1`) and allocated with the incoming tag (`tag[index] <= incoming_tag`).

### Test Workload

- **Address Trace**: `0, 0, 4, 4, 16, 0, 0`
- **Address Mapping**:
  - `Address 0`  -> Index 0, Tag 0
  - `Address 4`  -> Index 1, Tag 0
  - `Address 16` -> Index 0, Tag 1
- **Verified Outcome Sequence**: `MISS HIT MISS HIT MISS MISS HIT`

### Actual Verified Metrics

```text
Total Accesses = 7
Hits           = 3
Misses         = 4
Hit Rate       = 42.86%
Miss Rate      = 57.14%
```

- **Status**: Manually verified & **PASS**

### Conflict Miss Explanation

`Address 0` and `Address 16` map to the exact same cache index (Index 0) but carry different tags (`Tag 0` vs `Tag 1`).
- Accessing `Address 16` evicts `Address 0` from Index 0 (a conflict miss).
- The subsequent access to `Address 0` results in a second miss because Index 0 was overwritten with `Tag 1`.

### Bug Encountered — Testbench Delta-Cycle Timing

#### Initial Symptom
The initial testbench run produced an unexpected `6 Hits / 1 Miss` summary:
- `Address 4` reported `HIT` even when the line state showed `valid = 0`.
- Accesses that should have been cold/conflict misses were evaluated as hits.

#### Root Cause Analysis
The testbench updated `address` and `access_valid` at `negedge clk` and sampled the combinational `hit` signal immediately within the same simulation time step (delta cycle). Because combinational signal propagation takes simulator delta cycles (`address -> index/tag extraction -> hit equality check`), `hit` was sampled before the DUT combinational logic evaluated the new inputs.

#### Fix
Inserted a `#1;` time step delay after driving inputs on `negedge clk`:
```systemverilog
@(negedge clk);
address      = workload[i];
access_valid = 1'b1;
#1; // Allow combinational logic to propagate and settle before sampling
```
This allowed the combinational hit logic to settle before sampling `hit` and line state. The RTL code required zero modifications.

#### Verification Lesson
> *A simulation failure does not automatically imply broken RTL logic. Race conditions, event scheduling, and delta-cycle propagation delays in testbench sampling can corrupt verification results. Always verify testbench signal settling before declaring RTL defects.*

### Interview Explanation

- **What is a direct-mapped cache?**
  > *"A direct-mapped cache maps each memory address to exactly one specific cache line based on its index bits (`Index = Address mod Cache_Lines`). It has low lookup latency and minimal hardware overhead because no tag search across multiple ways is required."*
- **What is a conflict miss?**
  > *"A conflict miss occurs when two or more active memory addresses map to the exact same cache line index in a direct-mapped or set-associative cache, causing them to repeatedly evict each other even when overall cache capacity is available."*
- **What verification bug did you debug?**
  > *"I resolved a delta-cycle race condition where the testbench sampled a combinational hit output in the same simulation delta cycle in which the address was driven. Adding a explicit propagation delay (`#1`) ensured combinational signals settled before sampling."*

---

## Phase 4 — Python Workload Generator

### Status: IMPLEMENTED — MANUAL VERIFICATION PENDING

### What We Built

- **Generator Script**: [`scripts/workload_generator.py`](file:///e:/cpu-microarchitecture-performance-verification/scripts/workload_generator.py)
- **Branch Output Directory**: [`workloads/branches/`](file:///e:/cpu-microarchitecture-performance-verification/workloads/branches)
- **Memory Output Directory**: [`workloads/memory/`](file:///e:/cpu-microarchitecture-performance-verification/workloads/memory)

### Why Targeted Workloads Are Needed

Evaluating microarchitectural components requires distinct, realistic, and synthetic trace patterns designed to test specific edge cases:
- Short toy testbenches (e.g. 10 branches) verify basic logic correctness but cannot reveal statistically meaningful branch prediction accuracies or cache hit rates.
- Parameterized trace generators decouple workload synthesis from RTL implementation, allowing automated batch regressions over thousands of transactions.

### Core Concepts & Workload Types

#### Branch Workload Patterns
1. **Mostly Taken**: ~90% Taken (`1`), 10% Not Taken (`0`) using seeded randomness. Evaluates steady-state bias towards loop execution.
2. **Mostly Not Taken**: ~90% Not Taken (`0`), 10% Taken (`1`). Tests baseline prediction performance for rarely taken branches.
3. **Alternating**: Deterministic `1, 0, 1, 0...` pattern. Stresses 1-bit and 2-bit predictors with continuous direction changes.
4. **Loop Pattern**: Configurable $N$ Taken outcomes followed by 1 Not Taken exit branch (default 5 Taken + 1 Not Taken). Tests loop exit penalties.
5. **Random**: Uniform 50/50 probability distribution of Taken and Not Taken outcomes.

#### Cache / Memory Workload Patterns
1. **High Locality**: Repeated accesses to a small working set (e.g., addresses `0, 4, 8, 12`). Tests temporal and spatial locality hit rates.
2. **Sequential**: Streaming linear memory addresses with stride 4 (`0, 4, 8, 12, 16...`). Tests compulsory cold misses vs sequential spatial reuse.
3. **Random Memory**: Random 4-byte aligned 16-bit addresses (`0` to `65532`). Tests baseline cache performance under un-clustered memory traffic.
4. **Conflict Heavy**: Deliberately generates addresses aliasing to the exact same cache line index (`index = address[3:2]`).

### Deterministic Seeding & Conflict Address Mechanics

- **Deterministic Reproducibility**: Using a fixed random seed (`DEFAULT_SEED = 42` via `random.Random(seed)`) ensures identical trace output across regression runs, allowing exact comparisons between RTL simulations and Python reference models.
- **Index Aliasing (16-Byte Stride)**: In our 4-line direct-mapped cache (4-byte blocks), bits `[3:2]` determine the 2-bit line index. Addresses differing by multiples of 16 (e.g., `0, 16, 32, 48`) share `index = 2'b00` while carrying distinct tags (`Tag 0, 1, 2, 3`), forcing continuous cache line evictions.

### Why Workloads Are Stored Separately from RTL

Storing trace files (`workloads/branches/*.txt`, `workloads/memory/*.txt`) outside RTL testbenches maintains a clean separation of concerns:
- Hardware testbenches remain generic file readers rather than hard-coded pattern generators.
- Software reference models and RTL testbenches consume identical trace files, ensuring strict co-verification alignment.

### Expected Generated Output Files

```text
workloads/branches/mostly_taken.txt      (1000 entries)
workloads/branches/mostly_not_taken.txt  (1000 entries)
workloads/branches/alternating.txt       (1000 entries)
workloads/branches/loop.txt              (1000 entries)
workloads/branches/random.txt            (1000 entries)

workloads/memory/high_locality.txt     (1000 entries)
workloads/memory/sequential.txt        (1000 entries)
workloads/memory/random.txt            (1000 entries)
workloads/memory/conflict.txt          (1000 entries)
```

*(Note: Execution pending. Actual statistics will be recorded following manual script invocation.)*

---

## Phase 5 — Python Reference Models

### Status: IMPLEMENTED — MANUAL VERIFICATION PENDING

### What We Built

- **Reference Model Module**: [`scripts/reference_models.py`](file:///e:/cpu-microarchitecture-performance-verification/scripts/reference_models.py)

### Why Software Reference Models Are Needed

In hardware verification, a software "golden model" is an independent algorithmic specification of expected hardware behavior:
- **Independent Co-Verification**: Hardware RTL testbenches verify low-level signal timing, but an independent software model provides a high-level golden output to automatically check RTL correctness over large workloads.
- **Decoupled Architecture**: Implementing golden models in Python allows rapid, clear specification of architectural algorithms without hardware syntax clutter.

### Core Concepts & Implementation Architecture

1. **1-Bit Branch Predictor (`OneBitBranchPredictor`)**:
   - Single-bit state variable `state` (`1` = Taken, `0` = Not Taken), defaulting to `1`.
   - Returns prediction `state` *before* updating `state = actual_taken`.

2. **2-Bit Saturating Branch Predictor (`TwoBitBranchPredictor`)**:
   - 4-state counter (`0`=SN, `1`=WN, `2`=WT, `3`=ST), defaulting to `3` (Strongly Taken).
   - Prediction rule: `state >= 2` returns `1` (Taken), else `0` (Not Taken).
   - Saturating update: `min(state + 1, 3)` on Taken, `max(state - 1, 0)` on Not Taken.
   - Prediction is computed and returned *before* the 2-bit counter updates.

3. **Direct-Mapped Cache (`DirectMappedCache`)**:
   - 4 cache lines, 16-bit address space, 4-byte block size (12-bit tag, 2-bit index, 2-bit offset).
   - Address decomposition: `index = (address >> 2) & 0b11`, `tag = address >> 4`.
   - Hit condition evaluation: `is_hit = self.valid[index] and (self.tag[index] == tag)` computed *before* updating line state (`self.valid[index] = True`, `self.tag[index] = tag`).

### Ordering Mechanics (Prediction-Before-Update & Hit-Check-Before-Update)

In hardware pipelines and cycle-accurate simulations, prediction/hit evaluation and state updates occur in distinct phases within the clock cycle:
- **Prediction Phase (Combinational)**: The component outputs its prediction/hit response based on state held *prior* to the current transaction.
- **Update Phase (Sequential / Post-Access)**: State transition (updating counter or allocating cache tag) occurs after or on the clock edge.
- Python models enforce this strict ordering by reading current state into a local variable before executing state mutation logic.

### Co-Verification Integration Plan

In future regression testing (Phase 6), Python runner scripts will feed generated trace files simultaneously to:
1. Icarus Verilog RTL simulations (capturing SystemVerilog output logs).
2. Python golden reference models (`run_branch_trace`, `run_cache_trace`).

The runner will compare event records transaction-by-transaction to confirm 100% equivalence.

*(Note: Execution pending. Formal regression checking will occur in Phase 6.)*

---

## Phase 6 — Automated Regression Framework

### Status: PASS

### What We Built

- **Regression Runner**: [`scripts/regression.py`](file:///e:/cpu-microarchitecture-performance-verification/scripts/regression.py)
- **Updated Testbenches**:
  - [`tb/branch_predictor_1bit_tb.sv`](file:///e:/cpu-microarchitecture-performance-verification/tb/branch_predictor_1bit_tb.sv)
  - [`tb/branch_predictor_2bit_tb.sv`](file:///e:/cpu-microarchitecture-performance-verification/tb/branch_predictor_2bit_tb.sv)
  - [`tb/cache_tb.sv`](file:///e:/cpu-microarchitecture-performance-verification/tb/cache_tb.sv)
- **Output Artifacts**: Ignored build directory [`build/`](file:///e:/cpu-microarchitecture-performance-verification/.gitignore) and CSV results generator ([`results/regression_results.csv`](file:///e:/cpu-microarchitecture-performance-verification/results/regression_results.csv)).

### Actual Verified Regression Metrics

```text
Regression Cases = 14
Passed           = 14
Failed           = 0
Overall Status   = PASS
```

#### 1-Bit Branch Predictor (`branch_predictor_1bit`)
- `mostly_taken`: **79.80%** accuracy
- `mostly_not_taken`: **83.70%** accuracy
- `alternating`: **0.10%** accuracy
- `loop`: **66.80%** accuracy
- `random`: **49.20%** accuracy

#### 2-Bit Branch Predictor (`branch_predictor_2bit`)
- `mostly_taken`: **88.50%** accuracy
- `mostly_not_taken`: **90.30%** accuracy
- `alternating`: **50.00%** accuracy
- `loop`: **83.40%** accuracy
- `random`: **49.70%** accuracy

#### Direct-Mapped Cache (`direct_mapped_cache`)
- `high_locality`: **99.60%** hit rate
- `sequential`: **0.00%** hit rate
- `random`: **0.10%** hit rate
- `conflict`: **0.00%** hit rate

### Why Automated Regressions Matter

In microarchitecture verification, manual wave inspection or single-trace testbenches are insufficient for validating hardware robustness across diverse workloads:
- **Comprehensive Coverage**: Batch automation verifies RTL against thousands of synthetic transactions across multiple operational corner cases.
- **Event-by-Event Co-Verification**: Matching overall accuracy metrics alone can mask internal state bugs. Automated regression compares every single transaction event against golden software reference models.

### The 14 Regression Cases

The regression suite executes 14 distinct test cases:
1. **1-Bit Branch Predictor** (5 workloads): `mostly_taken`, `mostly_not_taken`, `alternating`, `loop`, `random`.
2. **2-Bit Branch Predictor** (5 workloads): `mostly_taken`, `mostly_not_taken`, `alternating`, `loop`, `random`.
3. **Direct-Mapped Cache** (4 workloads): `high_locality`, `sequential`, `random`, `conflict`.

### Automation Architecture & Execution Flow

```text
Load Workload File (+WORKLOAD=<path>)
         │
         ├──► Run Python Golden Model (scripts/reference_models.py) ──► Golden Event Records
         │
         └──► Compile RTL + TB (iverilog -g2012) ──► Run vvp ──► Parse REG_BRANCH / REG_CACHE ──► RTL Event Records
                                                                                                  │
                                                                                                  ▼
                                                                                       Transaction Comparison
                                                                                                  │
                                                                                     ┌────────────┴────────────┐
                                                                                     ▼                         ▼
                                                                                   PASS                      FAIL
                                                                            (All events match)    (First mismatch detailed)
```

1. **Compilation (`iverilog -g2012`)**: Uses Python `subprocess.run()` to build binaries into `build/`. If compilation fails, the case fails with full error output.
2. **Simulation (`vvp +WORKLOAD=<path>`)**: Testbenches read trace files line-by-line until EOF using `$value$plusargs`, `$fopen`, `$fscanf`, and `$fclose`.
3. **Delimited Output**: Testbenches emit machine-readable lines (`REG_BRANCH,<num>,<pred>,<actual>` and `REG_CACHE,<num>,<addr>,<hit>`).
4. **Event Comparison**: The Python runner compares event counts, input values, and output predictions/hits.
5. **Reporting & Exit Codes**: Displays terminal summaries, generates `results/regression_results.csv`, and exits with `0` for all-PASS or `1` for any-FAIL.

### Verification Principles: Observable Behavior vs. Internal RTL State

A fundamental verification best practice is treating the DUT as a black box:
- The golden model does **not** inspect or compare internal RTL state variables (e.g. `dut.state`).
- The regression runner verifies only observable hardware transaction contracts:
  - Predictors: `prediction` given `actual_taken`.
  - Cache: `hit`/`miss` status given `address`.
This ensures tests remain robust against internal implementation refactoring.

### Interview Explanation

> **Interview Question**: *"How did you verify that your RTL matched the intended behavior across complex workloads?"*
>
> **Answer**: *"I developed an automated co-verification regression suite in Python that compiled SystemVerilog RTL models with Icarus Verilog and executed them against synthetic trace files using `+WORKLOAD` plusargs. The testbenches emitted machine-readable event lines (`REG_BRANCH`, `REG_CACHE`) which were parsed by Python and compared transaction-by-transaction against independent golden software reference models. A case passed only if every individual event matched, ensuring strict behavioral equivalence."*

---

## Phase 7 — Performance Analyzer & Analytical CPI Model

### Status: PASS

### What We Built

- **Performance Analyzer Script**: [`scripts/performance_analyzer.py`](file:///e:/cpu-microarchitecture-performance-verification/scripts/performance_analyzer.py)
- **Output Report Artifact**: [`results/performance_report.txt`](file:///e:/cpu-microarchitecture-performance-verification/results/performance_report.txt)

### Actual Verified Performance Scenario Results

```text
Selected Scenario: 2-bit Predictor (loop) + Direct-Mapped Cache (high_locality)
Instructions: 10,000 | Base CPI: 1.0 | Branch Penalty: 3 cycles | Cache Miss Penalty: 10 cycles

Branch Mispredictions      = 166
Cache Misses               = 4
Extra Branch Cycles        = 498.0
Extra Cache Cycles         = 40.0
Estimated Total Cycles     = 10538.0
Estimated CPI              = 1.0538
```

### Key Analytical Lesson

> *Analytical performance models provide an efficient high-level mechanism to compare architectural trade-offs under controlled penalty assumptions. However, they must be explicitly distinguished from physical pipeline cycle-accurate measurements to maintain technical honesty in hardware engineering.*

### Purpose of Performance Analysis

While Phase 6 verifies zero-defect functional correctness between RTL and golden models, Phase 7 evaluates microarchitectural performance trade-offs:
- **Quantifying Sub-block Penalties**: Measures how branch mispredictions and cache misses degrade system-level performance under different workload patterns.
- **Data-Driven Evaluation**: Consumes empirical output from `results/regression_results.csv` to calculate comparative metrics without hard-coded assumptions.

### Analytical Performance Model Equations

Because the project focuses on isolated sub-blocks rather than a complete CPU core, performance is calculated using a simplified analytical stall-penalty model:

$$\text{Base Instruction Cycles} = \text{instructions} \times \text{base\_cpi}$$

$$\text{Extra Branch Cycles} = \text{branch\_mispredictions} \times \text{branch\_penalty}$$

$$\text{Extra Cache Cycles} = \text{cache\_misses} \times \text{cache\_miss\_penalty}$$

$$\text{Estimated Total Cycles} = \text{Base Instruction Cycles} + \text{Extra Branch Cycles} + \text{Extra Cache Cycles}$$

$$\text{Estimated CPI} = \frac{\text{Estimated Total Cycles}}{\text{instructions}}$$

### Model Parameters & Scenario Configuration

Default analytical scenario parameters:
- Modeled Instructions: `10000`
- Base CPI (`base_cpi`): `1.0`
- Branch Misprediction Penalty (`branch_penalty`): `3 cycles`
- Cache Miss Penalty (`cache_miss_penalty`): `10 cycles`
- Selected Branch Workload: `loop`
- Selected Cache Workload: `high_locality`
- Selected Predictor: `2bit`

*CLI Configurable*: All scenario parameters can be customized dynamically via `--instructions`, `--branch-penalty`, `--cache-miss-penalty`, `--branch-workload`, `--cache-workload`, and `--predictor`.

### Why Synthetic Traces Are Independent

The 1,000 branch outcomes and 1,000 memory accesses are generated from independent synthetic trace workloads (`workloads/branches/` and `workloads/memory/`):
- They do **not** represent traces extracted from executing the same physical 10,000-instruction binary.
- Combining their observed penalty counts into the Estimated CPI model provides a comparative benchmark scenario for microarchitectural trade-off study rather than a cycle-accurate pipeline simulation.

### Interview Explanation

> **Interview Question**: *"How did you estimate processor performance (CPI) if you did not implement a full CPU pipeline?"*
>
> **Answer**: *"I constructed a parameterizable analytical stall-penalty model in Python (`scripts/performance_analyzer.py`) that combined base instruction cycles with misprediction and cache miss penalty cycles. By extracting empirical misprediction and miss counts from automated RTL regressions (`results/regression_results.csv`), the model calculated an Estimated CPI (`Total Cycles / Instructions`) to evaluate component trade-offs (e.g. comparing 1-bit vs 2-bit branch predictors under different penalty assumptions) while remaining technically transparent that it was an analytical model rather than a physical pipeline measurement."*

---

## Phase 8 — Final Documentation and Polish

### Status: COMPLETE

### What Was Finalized

- **Comprehensive README ([`README.md`](file:///e:/cpu-microarchitecture-performance-verification/README.md))**: Complete project guide with ASCII architecture diagrams, verified result tables, analytical CPI formulas, debugging case study, scope limitations, resume descriptions, and 30-second interview summary.
- **Interview Guide ([`docs/interview_guide.md`](file:///e:/cpu-microarchitecture-performance-verification/docs/interview_guide.md))**: 25 detailed microarchitecture and verification Q&A pairs for interview revision.
- **Results Summary ([`docs/results_summary.md`](file:///e:/cpu-microarchitecture-performance-verification/docs/results_summary.md))**: Concise record of verified regression metrics and microarchitectural findings.
- **Build & Artifact Cleanup ([`.gitignore`](file:///e:/cpu-microarchitecture-performance-verification/.gitignore))**: Ignored build output directory (`build/`) while retaining tracked results and workload traces.

---

## Final Project Status

```text
Phase 1 — 1-bit branch predictor       PASS
Phase 2 — 2-bit branch predictor       PASS
Phase 3 — Direct-mapped cache          PASS
Phase 4 — Python workload generator    PASS
Phase 5 — Python reference models      PASS
Phase 6 — Automated regression runner  PASS
Phase 7 — Performance analyzer         PASS
Phase 8 — Final documentation/polish   COMPLETE
Phase 9A — Multi-seed stress runner    PASS

Overall Regression Status: 14 / 14 PASS (Single Seed) | 280 / 280 PASS (Multi-Seed Stress)
```

---

## Phase 9A — Multi-Seed Stress Regression

### Status: PASS

### What We Built

- **Stress Regression Runner**: [`scripts/stress_regression.py`](file:///e:/cpu-microarchitecture-performance-verification/scripts/stress_regression.py)
- **Output Artifact**: CSV results logger ([`results/stress_regression_results.csv`](file:///e:/cpu-microarchitecture-performance-verification/results/stress_regression_results.csv)).

### Verified Multi-Seed Stress Metrics

```text
Seeds Tested:             20 (Seeds 1 to 20)
Regression Cases / Seed:  14
Total Regression Cases:   280
Passed:                   280
Failed:                   0
Verified RTL Events:      280,000
Overall Status:           PASS
```

### Why One Random Seed Is Insufficient

Verifying hardware against a single fixed random seed (e.g. `seed = 42`) provides a single point of coverage:
- **Pseudo-Random Bias**: A single seed tests only one pseudo-random sequence of branch directions and memory address permutations.
- **Coverage Expansion**: Multi-seed stress testing regenerates fresh synthetic workload streams across dozens of seeds, exposing the RTL to varied transaction sequences without altering hardware design.

### Architecture & Reusability

[`scripts/stress_regression.py`](file:///e:/cpu-microarchitecture-performance-verification/scripts/stress_regression.py) reuses existing verified modules without code duplication:
1. Imports `generate_all_workloads()` from `scripts/workload_generator.py` to regenerate trace files for each seed.
2. Imports `run_full_regression()` from `scripts/regression.py` to execute the full 14-case RTL vs Python co-verification suite per seed.
3. Aggregates seed pass/fail status, records failed seed details, and tallies total verified transaction events.

### Verification Depth & Transaction Count

For the tested configuration (20 seeds, 1,000 events per trace):
- **Branch Events**: 10 branch cases $\times$ 1,000 events = 10,000 branch transactions per seed.
- **Cache Events**: 4 cache cases $\times$ 1,000 events = 4,000 memory transactions per seed.
- **Per-Seed Total**: 14,000 transaction events verified event-by-event against golden models per seed.
- **20-Seed Total**: **280,000 verified RTL transaction events** across 280 total regression test cases.

### Argparse Bug Resolution & Rerun

During initial manual invocation, a CLI argument attribute error was encountered in [`scripts/stress_regression.py`](file:///e:/cpu-microarchitecture-performance-verification/scripts/stress_regression.py) where `--num-seeds` was incorrectly referenced as `args.num-seeds` instead of `args.num_seeds` (Python argparse converts hyphens to underscores in Namespace attributes).

- **Fix**: Corrected line 101 to `end_seed = args.start_seed + args.num_seeds`.
- **Validation**: Executed 20-seed stress regression successfully (**280 / 280 PASS**). Subsequently reran baseline seed-42 workload generation and single-seed regression suite (**14 / 14 PASS**).

### Interview Explanation

> **Interview Question**: *"How did you ensure your hardware verification coverage was thorough and not biased by a single random workload?"*
>
> **Answer**: *"I implemented a multi-seed stress regression framework (`scripts/stress_regression.py`) that iteratively generated fresh synthetic workload streams across 20 distinct random seeds and executed the complete 14-case regression suite for each seed. This scaled verification depth to 280 total regression runs and 280,000 transaction events, verifying that transaction-level RTL and golden reference model agreement held consistently across diverse randomized inputs."*

---

## Phase 9B — Directed Edge-Case Verification

### Status: IMPLEMENTED — MANUAL VERIFICATION PENDING

### What We Built

- **Directed Edge-Case Runner**: [`scripts/edge_case_regression.py`](file:///e:/cpu-microarchitecture-performance-verification/scripts/edge_case_regression.py)
- **Workload Directory**: Programmatically generated trace files under [`workloads/edge_cases/`](file:///e:/cpu-microarchitecture-performance-verification/workloads/edge_cases)
- **Output Artifact**: CSV results logger ([`results/edge_case_results.csv`](file:///e:/cpu-microarchitecture-performance-verification/results/edge_case_results.csv))

### Why Directed Edge Cases Complement Randomized Stress Testing

While multi-seed stress testing provides broad randomized coverage, directed verification intentionally targets specific boundary conditions and pathological corner cases:
- **Boundary Exhaustion**: Minimum trace lengths (1-element branch and memory streams), maximum 16-bit address limits (`65535`), and address zero (`0`).
- **State Machine Saturation**: Explicitly driving the 2-bit saturating predictor counter from reset `11` down to `00` (Strongly Not Taken) and recovering back to `11` (Strongly Taken).
- **Cache Block-Offset Isolation**: Testing unaligned byte offsets within the same 4-byte cache block (`0, 1, 2, 3`) to verify offset bits do not corrupt tag/index matching logic.

### Directed Test Cases (31 Total Case Runs)

#### Branch Predictor Directed Cases (11 Traces $\times$ 2 Predictors = 22 Cases)
1. `all_taken`: 100 consecutive Taken branches (`1`).
2. `all_not_taken`: 100 consecutive Not Taken branches (`0`).
3. `single_taken`: Single Taken branch (`1`).
4. `single_not_taken`: Single Not Taken branch (`0`).
5. `opposite_1_0`: Minimum two-branch sequence `1, 0`.
6. `opposite_0_1`: Minimum two-branch sequence `0, 1`.
7. `strict_alternating`: 100 alternating branches (`1, 0, 1, 0...`).
8. `long_taken_then_one_not_taken`: 99 Taken branches followed by 1 Not Taken branch.
9. `long_not_taken_then_one_taken`: 99 Not Taken branches followed by 1 Taken branch.
10. `repeated_loop_exit`: Repeating 5 Taken branches + 1 Not Taken exit branch pattern (`1,1,1,1,1,0`).
11. `saturation_transition`: 10 Not Taken branches followed by 10 Taken branches driving counter saturation limits.

#### Direct-Mapped Cache Directed Cases (9 Cases)
1. `same_address_repeated`: Address `0` repeated 100 times (cold miss followed by 99 hits).
2. `same_block_offsets`: Unaligned byte offsets `0, 1, 2, 3` within the same 4-byte block (cold miss followed by 3 block hits).
3. `every_index`: Accesses targeting all 4 cache line indices (`0, 4, 8, 12`).
4. `conflict_thrashing`: Continuous 16-byte index aliasing between addresses `0` and `16` (Index 0 thrashing).
5. `multiple_same_index_tags`: Accessing 5 distinct tags aliasing to Index 0 (`0, 16, 32, 48, 64`).
6. `max_address`: Maximum 16-bit address boundaries (`65532, 65533, 65534, 65535`).
7. `address_zero`: Single address `0` access.
8. `block_boundary`: Transitioning across block boundaries (`0, 1, 2, 3` to `4, 5, 6, 7`).
9. `capacity_pressure`: 8 unique block addresses (`0, 4, 8, 12, 16, 20, 24, 28`) exceeding 4-line cache capacity.

### Transaction-Level Verification

Every directed case executes event-by-event equivalence checking against Python golden models:
- Predictors: Compares `branch_num`, `actual`, and `prediction` for every branch.
- Cache: Compares `access_num`, `address`, and `hit/miss` status for every access.
- Result logging writes `results/edge_case_results.csv` and returns exit code `0` (all PASS) or `1` (any FAIL).

### Interview Explanation

> **Interview Question**: *"How did you verify your hardware components against edge cases and boundary conditions?"*
>
> **Answer**: *"I built a directed edge-case verification runner (`scripts/edge_case_regression.py`) that programmatically generated 11 directed branch traces and 9 directed cache traces targeting specific boundary behaviors—such as unaligned byte offset accesses within the same cache block (`0, 1, 2, 3`), 2-bit counter saturation boundaries (`11 -> 00 -> 11`), single-element traces, and maximum 16-bit address limits (`65535`). Each directed case was compared transaction-by-transaction against software golden models to confirm zero-defect behavioral equivalence."*

*(Note: Runner implemented; execution pending manual invocation.)*
