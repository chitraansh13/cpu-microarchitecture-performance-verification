# Verified Results Summary

This document summarizes the verified performance and regression metrics for the CPU Microarchitecture Performance Verification project.

---

## 1. Automated Regression Status

- **Total Test Cases**: 14
- **Passed**: 14
- **Failed**: 0
- **Overall Status**: **PASS**

---

## 2. Branch Predictor Performance Summary

Trace length: 1,000 branch outcomes per workload.

| Workload | 1-bit Predictor Accuracy | 2-bit Predictor Accuracy | Accuracy Gain (2-bit vs 1-bit) |
| :--- | ---: | ---: | ---: |
| **Mostly Taken** | 79.80% | **88.50%** | +8.70% |
| **Mostly Not Taken** | 83.70% | **90.30%** | +6.60% |
| **Alternating** | 0.10% | **50.00%** | +49.90% |
| **Loop** | 66.80% | **83.40%** | +16.60% |
| **Random** | 49.20% | **49.70%** | +0.50% |

---

## 3. Cache Performance Summary

Trace length: 1,000 memory accesses per workload (4 cache lines, 4-byte block size).

| Workload | Hits | Misses | Hit Rate | Miss Rate |
| :--- | ---: | ---: | ---: | ---: |
| **High Locality** | 996 | 4 | **99.60%** | 0.40% |
| **Sequential** | 0 | 1000 | **0.00%** | 100.00% |
| **Random** | 1 | 999 | **0.10%** | 99.90% |
| **Conflict** | 0 | 1000 | **0.00%** | 100.00% |

---

## 4. Default Analytical Performance Scenario

- **Scenario**: 2-bit Predictor (`loop` workload) + Direct-Mapped Cache (`high_locality` workload)
- **Modeled Instructions**: 10,000
- **Base CPI**: 1.0
- **Branch Mispredict Penalty**: 3 cycles
- **Cache Miss Penalty**: 10 cycles

| Metric | Value |
| :--- | :--- |
| **Branch Mispredictions** | 166 |
| **Cache Misses** | 4 |
| **Base Instruction Cycles** | 10,000.0 |
| **Extra Branch Cycles** | 498.0 |
| **Extra Cache Cycles** | 40.0 |
| **Estimated Total Cycles** | **10,538.0** |
| **Estimated CPI** | **1.0538** |

*Note: Estimated CPI is a simplified analytical metric and is NOT measured real CPU CPI.*

---

## 5. Multi-Seed Stress Regression Summary

- **Seeds Tested**: 20 (Seeds 1 to 20)
- **Regression Cases / Seed**: 14
- **Total Regression Cases**: 280
- **Passed**: 280
- **Failed**: 0
- **Verified RTL Transaction Events**: 280,000
- **Overall Status**: **PASS**

---

## 6. Key Technical Findings

1. **Hysteresis Benefits**: The 2-bit predictor achieves an 83.40% accuracy on loop patterns (vs 66.80% for 1-bit), demonstrating that counter hysteresis effectively eliminates re-entry mispredictions following loop exits.
2. **Pathological Predictor Patterns**: Alternating branch streams cause 1-bit state flipping on every branch (0.10% accuracy), whereas 2-bit hysteresis stabilizes prediction at chance level (50.00%).
3. **Working Set Fit**: Small working sets fitting within the 4-line cache achieve a 99.60% hit rate, bounded only by initial cold misses.
4. **Index Aliasing Thrashing**: Address streams differing by 16-byte strides (`0, 16, 32, 48`) alias to `Index 0`, demonstrating 100% conflict miss thrashing in direct-mapped caches.
5. **Multi-Seed Equivalence**: Verified 280,000 transaction events across 20 randomized seeds with 100% RTL vs Python golden model equivalence.
