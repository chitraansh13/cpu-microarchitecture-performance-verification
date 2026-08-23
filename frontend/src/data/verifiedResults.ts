export interface BranchResult {
  workload: string;
  oneBit: number;
  twoBit: number;
}

export interface CacheResult {
  workload: string;
  hits: number;
  misses: number;
  hitRate: number;
}

export interface VerificationCampaign {
  id: string;
  title: string;
  status: 'PASS' | 'COMPLETE' | 'EXPECTED FAIL DETECTED';
  badgeType: 'emerald' | 'cyan' | 'slate' | 'amber';
  metrics: { label: string; value: string }[];
  description: string;
  isFaultInjection?: boolean;
}

export interface PerformanceScenario {
  predictor: string;
  branchWorkload: string;
  cacheWorkload: string;
  instructions: number;
  baseCpi: number;
  branchPenalty: number;
  cachePenalty: number;
  branchMispredictions: number;
  cacheMisses: number;
  baseCycles: number;
  extraBranchCycles: number;
  extraCacheCycles: number;
  estimatedTotalCycles: number;
  estimatedCpi: number;
}

export const VERIFIED_BRANCH_RESULTS: BranchResult[] = [
  { workload: 'Mostly Taken', oneBit: 79.80, twoBit: 88.50 },
  { workload: 'Mostly Not Taken', oneBit: 83.70, twoBit: 90.30 },
  { workload: 'Alternating', oneBit: 0.10, twoBit: 50.00 },
  { workload: 'Loop', oneBit: 66.80, twoBit: 83.40 },
  { workload: 'Random', oneBit: 49.20, twoBit: 49.70 },
];

export const VERIFIED_CACHE_RESULTS: CacheResult[] = [
  { workload: 'High Locality', hits: 996, misses: 4, hitRate: 99.60 },
  { workload: 'Sequential', hits: 0, misses: 1000, hitRate: 0.00 },
  { workload: 'Random', hits: 1, misses: 999, hitRate: 0.10 },
  { workload: 'Conflict', hits: 0, misses: 1000, hitRate: 0.00 },
];

export const VERIFIED_PERFORMANCE_SCENARIO: PerformanceScenario = {
  predictor: '2-bit Saturating',
  branchWorkload: 'loop',
  cacheWorkload: 'high_locality',
  instructions: 10000,
  baseCpi: 1.0,
  branchPenalty: 3,
  cachePenalty: 10,
  branchMispredictions: 166,
  cacheMisses: 4,
  baseCycles: 10000.0,
  extraBranchCycles: 498.0,
  extraCacheCycles: 40.0,
  estimatedTotalCycles: 10538.0,
  estimatedCpi: 1.0538,
};

export const VERIFICATION_CAMPAIGNS: VerificationCampaign[] = [
  {
    id: 'baseline',
    title: 'Baseline Regression',
    status: 'PASS',
    badgeType: 'emerald',
    metrics: [
      { label: 'Cases Run', value: '14' },
      { label: 'Passed', value: '14' },
      { label: 'Failed', value: '0' },
      { label: 'Seed', value: '42' },
    ],
    description: 'SystemVerilog RTL co-verification against Python golden reference models across 5 1-bit branch, 5 2-bit branch, and 4 cache trace workloads.'
  },
  {
    id: 'stress',
    title: 'Multi-Seed Stress Regression',
    status: 'PASS',
    badgeType: 'cyan',
    metrics: [
      { label: 'Seeds Tested', value: '20' },
      { label: 'Cases Run', value: '280' },
      { label: 'Passed', value: '280' },
      { label: 'Verified Events', value: '280,000' },
    ],
    description: 'Multi-seed random stress testing scaling verification depth to 280,000 transaction events across 20 deterministic seeds.'
  },
  {
    id: 'directed',
    title: 'Directed Edge-Case Verification',
    status: 'PASS',
    badgeType: 'slate',
    metrics: [
      { label: 'Cases Run', value: '31' },
      { label: 'Branch Runs', value: '22' },
      { label: 'Cache Runs', value: '9' },
      { label: 'Verified Events', value: '1,949' },
    ],
    description: 'Targeted boundary testing including unaligned block byte offsets (0,1,2,3), 2-bit counter saturation boundaries, and index thrashing.'
  },
  {
    id: 'fault_injection',
    title: 'Fault-Injection Validation',
    status: 'EXPECTED FAIL DETECTED',
    badgeType: 'amber',
    isFaultInjection: true,
    metrics: [
      { label: 'Fault Location', value: 'branch_predictor_2bit.sv' },
      { label: 'Fault Expression', value: 'prediction = state[0]' },
      { label: 'Affected Cases', value: '5 / 5 Flagged FAIL' },
      { label: 'Post-Restore', value: '14 / 14 PASS' },
    ],
    description: 'Negative testing validation proving framework sensitivity. Intentionally modifying prediction bit selection caused all 5 2-bit cases to fail with exact first-mismatch trace logs.'
  }
];
