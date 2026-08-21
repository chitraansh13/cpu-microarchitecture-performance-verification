# CPU Microarchitecture Performance Verification

This project studies and verifies simplified CPU microarchitecture components using SystemVerilog for hardware RTL modeling and Python for verification, workload generation, reference modeling, and performance analysis.

## Overview

Hardware performance in modern processors relies on critical microarchitectural sub-blocks such as dynamic branch predictors and cache memories. This project establishes a focused environment to design simplified SystemVerilog models for these components, verify their behavior against Python software reference models, and evaluate performance under synthetic workloads.

## Project Goals

- **RTL Hardware Modeling**: Design clean, modular SystemVerilog models for basic CPU microarchitecture sub-blocks.
- **Verification Infrastructure**: Construct a Python verification framework with behavioral reference models to validate RTL execution correctness.
- **Performance Evaluation**: Compute key architectural metrics including branch prediction accuracy, cache hit/miss rates, cycle counts, and analytical CPI.
- **Automated Analysis**: Develop Python tooling to generate workloads, execute regression suites, parse simulation logs, and compile performance summaries.

## Planned Components

The project focuses on isolated microarchitectural components:

1. **1-Bit Branch Predictor**: A single-bit dynamic history branch prediction module.
2. **2-Bit Saturating Branch Predictor**: A 2-bit saturating counter branch predictor with state hysteresis.
3. **Direct-Mapped Cache**: A direct-mapped cache memory module supporting tag, index, and offset address decomposition.

## Verification Approach

Verification relies on co-evaluating hardware RTL execution against high-level software models:

- **SystemVerilog RTL**: Used strictly for modeling the hardware sub-blocks and module-level simulation testbenches.
- **Python Reference Models**: High-level algorithmic reference models implemented in Python reflect expected component functionality.
- **Co-Verification & Automation**: Python automation scripts feed identical workload traces to RTL simulations and reference models, comparing cycle-by-cycle or transaction-level outputs to confirm functional equivalence.
- **Metrics Collected**:
  - **Branch Prediction Accuracy**: Ratio of correct predictions to total branch instructions.
  - **Cache Hit / Miss Rate**: Proportions of memory accesses resulting in cache hits versus misses.
  - **Estimated Cycles**: Total clock cycles required to process a given workload trace.
  - **Estimated CPI (Cycles Per Instruction)**: Evaluated using a simplified analytical model based on base instruction cycles plus misprediction and cache miss stall penalties. *Note: Estimated CPI is a simplified analytical model and is NOT measured real CPU CPI.*

## Technology Stack

- **Hardware Modeling & Testbenches**: SystemVerilog (`.sv`)
- **Verification, Tooling & Modeling**: Python (`.py`)
- **Simulation**: Icarus Verilog (`iverilog`, `vvp`)
- **Waveform Inspection**: GTKWave (`.vcd`, optional for manual debug)

## Repository Structure

```text
rtl/
tb/
scripts/
workloads/
    branches/
    memory/
results/
docs/
```

- `rtl/`: SystemVerilog source files for hardware components.
- `tb/`: SystemVerilog testbench files.
- `scripts/`: Python scripts for reference models, regression execution, and performance analysis.
- `workloads/`: Synthetic trace files for evaluation.
  - `branches/`: Branch trace files for branch predictor testing.
  - `memory/`: Memory address trace files for cache testing.
- `results/`: Simulation outputs, log files, and generated performance summaries.
- `docs/`: Microarchitecture design notes, verification plans, and project documentation.

## Development Roadmap

The planned implementation sequence for this repository is:

1. 1-bit branch predictor *(RTL & Testbench implemented; simulation pending)*
2. 2-bit branch predictor
3. Direct-mapped cache
4. Workload generator
5. Python reference models
6. Regression runner
7. Performance analyzer
8. Final documentation

*(Note: Phase 1 RTL model and SystemVerilog testbench created. Simulation execution pending per execution rules.)*

## Scope / Limitations

- **Not a Full CPU**: This project isolates specific microarchitectural sub-blocks for study and verification; it does not contain a full CPU core, execution pipeline, register file, or instruction decoder.
- **Analytical Performance Modeling**: Metrics like Estimated CPI are derived from simplified analytical calculations (penalty summation) rather than measured from full pipeline cycle-accurate hardware execution.
- **Minimal Dependencies**: The repository avoids complex external frameworks, commercial EDA tools, or heavy infrastructure in favor of standard SystemVerilog and Python.
