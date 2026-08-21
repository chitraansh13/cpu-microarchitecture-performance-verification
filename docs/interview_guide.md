# CPU Microarchitecture Verification — Interview Guide

This guide provides concise, interview-ready answers to key technical questions about the CPU Microarchitecture Performance Verification project.

---

### 1. What does the project do?
This project models, verifies, and analyzes fundamental CPU microarchitecture sub-blocks (1-bit branch predictor, 2-bit saturating branch predictor, and direct-mapped cache) using SystemVerilog for RTL hardware design and Python for automated workload generation, software golden reference modeling, co-verification regression testing, and performance analysis.

### 2. Why SystemVerilog and Python?
SystemVerilog is the industry-standard Hardware Description Language (HDL) used for synthesizable RTL hardware modeling and testbench verification. Python provides flexible, rapid software infrastructure for workload generation, reference modeling, file parsing, and regression orchestration.

### 3. What is a branch predictor?
A branch predictor is a microarchitectural sub-block that speculatively predicts the direction (Taken or Not Taken) of conditional branch instructions before they are resolved in the execution stage, reducing pipeline stall penalties.

### 4. How does the 1-bit predictor work?
The 1-bit dynamic predictor maintains a 1-bit flip-flop storing the outcome of the most recent branch (`1` = Taken, `0` = Not Taken). It predicts that the next branch outcome will equal the previous branch direction (`prediction = state`), and updates `state <= actual_taken` on clock edges.

### 5. Why does 1-bit perform badly on alternating branches?
On alternating branch traces (`1, 0, 1, 0...`), a 1-bit predictor flips its internal state after every single branch, causing every subsequent branch to mispredict. This results in ~0% prediction accuracy.

### 6. How does the 2-bit saturating predictor work?
The 2-bit predictor uses a 2-bit saturating counter representing four states: `00` (Strongly Not Taken), `01` (Weakly Not Taken), `10` (Weakly Taken), and `11` (Strongly Taken). The MSB (`state[1]`) outputs the prediction. Taken outcomes increment the counter (saturating at `3`), while Not Taken outcomes decrement it (saturating at `0`).

### 7. Why can 2-bit outperform 1-bit?
The 2-bit predictor adds state hysteresis. An isolated anomalous branch outcome (e.g., a loop exit) moves state from `11` (Strongly Taken) to `10` (Weakly Taken). Because state `10` still predicts Taken, the predictor avoids mispredicting when the loop restarts on the next branch.

### 8. What is a direct-mapped cache?
A direct-mapped cache is a cache memory architecture where each memory address maps to exactly one specific cache line index (`Index = Address mod Cache_Lines`). It has low lookup latency and minimal hardware overhead.

### 9. What are tag/index/offset?
- **Offset**: Bits selecting the specific byte within a cache line block.
- **Index**: Bits selecting the specific cache line entry.
- **Tag**: Remaining high-order bits stored in the cache line to verify address match.

### 10. How did you calculate tag/index/offset?
For a 16-bit address, 4 cache lines, and 4-byte blocks:
- **Offset**: $\log_2(4) = 2$ bits (`address[1:0]`).
- **Index**: $\log_2(4) = 2$ bits (`address[3:2]`).
- **Tag**: $16 - 2 - 2 = 12$ bits (`address[15:4]`).

### 11. What is a cold miss?
A cold (or compulsory) miss occurs the very first time a memory block is accessed after system initialization because the cache line `valid` bit is unset (`0`).

### 12. What is a conflict miss?
A conflict miss occurs when two or more active memory addresses map to the exact same cache index, causing them to repeatedly evict each other even though overall cache capacity remains available.

### 13. Why did the conflict workload produce 0% hits?
The conflict workload generated addresses separated by 16-byte strides (`0, 16, 32, 48...`). Because `Index = address[3:2]`, all four addresses share `Index 0` while carrying different tags (`0, 1, 2, 3`), causing 100% line thrashing and 0% hits.

### 14. What is a golden/reference model?
A golden reference model is an independent software implementation (written in Python) that models the exact high-level functional specification of hardware components to generate expected golden outputs for verification.

### 15. Why not just compare final accuracy?
Comparing final accuracy percentages alone can mask cancelling bugs (e.g., mispredicting branch 5 as 0 and branch 6 as 1 yields identical accuracy to mispredicting branch 5 as 1 and branch 6 as 0). Event-by-event transaction matching guarantees 100% functional equivalence.

### 16. How does your regression framework work?
[`scripts/regression.py`](file:///e:/cpu-microarchitecture-performance-verification/scripts/regression.py) compiles SystemVerilog sources using `iverilog -g2012`, executes simulations with `vvp +WORKLOAD=<file>`, parses delimited machine-readable event logs (`REG_BRANCH`, `REG_CACHE`), compares events against Python golden model records, outputs a summary table, writes `results/regression_results.csv`, and returns exit code 0 (PASS) or 1 (FAIL).

### 17. How many regression cases did you run?
14 total cases:
- 1-Bit Predictor: 5 workloads (`mostly_taken`, `mostly_not_taken`, `alternating`, `loop`, `random`).
- 2-Bit Predictor: 5 workloads (`mostly_taken`, `mostly_not_taken`, `alternating`, `loop`, `random`).
- Direct-Mapped Cache: 4 workloads (`high_locality`, `sequential`, `random`, `conflict`).

### 18. What bug did you encounter?
In the initial cache testbench, driving `address` on `negedge clk` and sampling combinational `hit` immediately in the same simulation time step caused a delta-cycle race condition where stale hit values were read before combinational propagation completed.

### 19. What is a SystemVerilog delta cycle/event scheduling issue?
A delta cycle is an infinitesimal simulation time step used to evaluate combinational events within the simulator event queue. Sampling a combinational output in the same delta cycle in which inputs change can read stale values before signals settle.

### 20. Why was the RTL not necessarily wrong when the simulation failed?
Because testbench sampling errors (such as delta-cycle race conditions) can mis-evaluate valid RTL outputs. Verification requires ensuring both testbench timing and RTL logic are correct.

### 21. What is Estimated CPI?
Estimated CPI (Cycles Per Instruction) is a simplified analytical metric combining base instruction execution cycles with stall penalties from branch mispredictions and cache misses:
$$\text{Estimated CPI} = \frac{\text{Base Cycles} + \text{Branch Penalty Cycles} + \text{Cache Penalty Cycles}}{\text{Instructions}}$$

### 22. Is your CPI real CPU CPI?
No. It is a simplified analytical metric used for comparative trade-off study. It is not measured from a physical CPU core or cycle-accurate pipeline simulation.

### 23. How did you calculate Estimated CPI?
Using empirical mispredictions and cache misses from regression CSV results:
- Base Cycles = $10,000 \times 1.0 = 10,000$
- Branch Stall Cycles = $166 \times 3 = 498$
- Cache Stall Cycles = $4 \times 10 = 40$
- Total Cycles = $10,538$, giving Estimated CPI = $1.0538$.

### 24. Why are branch and cache workloads independent?
The synthetic branch and memory trace files are generated independently to stress specific sub-block edge cases (such as loop exits vs. 16-byte index aliasing) rather than tracing a single compiled binary executable.

### 25. What would you improve next if you had more time?
1. Implement a 2-level global branch history (gshare) predictor with a Pattern History Table (PHT).
2. Implement a 2-way or 4-way set-associative cache with LRU replacement logic.
3. Parameterize cache line count, block size, and address bit widths in SystemVerilog.
