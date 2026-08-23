const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface HealthResponse {
  status: string;
  service: string;
  toolchain: {
    iverilog: boolean;
    vvp: boolean;
  };
}

export interface VerifyPayload {
  predictor: '1bit' | '2bit';
  branch_workload: 'mostly_taken' | 'mostly_not_taken' | 'alternating' | 'loop' | 'random';
  cache_workload: 'high_locality' | 'sequential' | 'random' | 'conflict';
  seed: number;
  branch_count: number;
  memory_count: number;
  instructions: number;
  base_cpi: number;
  branch_penalty: number;
  cache_miss_penalty: number;
}

export interface VerifyResponseData {
  status: 'PASS' | 'FAIL';
  configuration: Record<string, any>;
  branch?: {
    verified: boolean;
    total: number;
    correct: number;
    mispredictions: number;
    accuracy: number;
  };
  cache?: {
    verified: boolean;
    total: number;
    hits: number;
    misses: number;
    hit_rate: number;
  };
  performance?: {
    instructions: number;
    base_cpi: number;
    branch_penalty: number;
    cache_miss_penalty: number;
    base_cycles: number;
    branch_penalty_cycles: number;
    cache_penalty_cycles: number;
    estimated_total_cycles: number;
    estimated_cpi: number;
  };
  error?: string;
  mismatch_detail?: string;
}

export interface RegressionPayload {
  seed?: number;
  branch_count?: number;
  memory_count?: number;
}

export interface RegressionResponseData {
  status: 'PASS' | 'FAIL';
  cases: number;
  passed: number;
  failed: number;
  verified_events: number;
  results: any[];
  error?: string;
}

export interface StressPayload {
  start_seed?: number;
  num_seeds?: number;
  branch_count?: number;
  memory_count?: number;
}

export interface StressResponseData {
  status: 'PASS' | 'FAIL';
  seeds_tested: number;
  total_cases: number;
  passed: number;
  failed: number;
  verified_events: number;
  error?: string;
}

export interface EdgeCasesResponseData {
  status: 'PASS' | 'FAIL';
  cases: number;
  passed: number;
  failed: number;
  verified_events: number;
  results: any[];
  error?: string;
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${BASE_URL}/api/health`);
  if (!res.ok) {
    throw new Error(`Health check failed with status ${res.status}`);
  }
  return res.json();
}

export async function runVerification(payload: VerifyPayload): Promise<VerifyResponseData> {
  const res = await fetch(`${BASE_URL}/api/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Verification API failed (${res.status}): ${errorText}`);
  }
  return res.json();
}

export async function runBaselineRegression(payload: RegressionPayload = {}): Promise<RegressionResponseData> {
  const res = await fetch(`${BASE_URL}/api/regression`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Regression API failed (${res.status}): ${errorText}`);
  }
  return res.json();
}

export async function runStressRegression(payload: StressPayload = {}): Promise<StressResponseData> {
  const res = await fetch(`${BASE_URL}/api/stress`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Stress API failed (${res.status}): ${errorText}`);
  }
  return res.json();
}

export async function runEdgeCases(): Promise<EdgeCasesResponseData> {
  const res = await fetch(`${BASE_URL}/api/edge-cases`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Edge cases API failed (${res.status}): ${errorText}`);
  }
  return res.json();
}

export interface BranchRunPayload {
  predictor: '1bit' | '2bit' | 'both';
  workload_type: 'mostly_taken' | 'mostly_not_taken' | 'alternating' | 'loop' | 'random' | 'custom';
  trace?: string;
  seed?: number;
  count?: number;
}

export interface BranchEvent {
  branch: number;
  actual: number;
  prediction: number;
  expected_prediction: number;
  correct: boolean;
  match: boolean;
}

export interface BranchRunResponseData {
  status: 'PASS' | 'FAIL';
  input_trace: number[];
  predictor?: string;
  verified: boolean;
  total?: number;
  correct?: number;
  incorrect?: number;
  accuracy?: number;
  events?: BranchEvent[];
  predictors?: Record<string, any>;
  accuracy_delta?: number;
  trace_length?: number;
  error?: string;
}

export interface CacheRunPayload {
  workload_type: 'high_locality' | 'sequential' | 'random' | 'conflict' | 'custom';
  addresses?: string;
  seed?: number;
  count?: number;
}

export interface CacheEvent {
  access: number;
  address: number;
  address_hex: string;
  index: number;
  tag: number;
  hit: boolean;
  expected_hit: boolean;
  match: boolean;
}

export interface CacheRunResponseData {
  status: 'PASS' | 'FAIL';
  verified: boolean;
  configuration: {
    cache_lines: number;
    block_size_bytes: number;
    address_width_bits: number;
  };
  input_addresses: number[];
  total: number;
  hits: number;
  misses: number;
  hit_rate: number;
  miss_rate: number;
  events: CacheEvent[];
  error?: string;
}

export async function runBranchVerification(payload: BranchRunPayload): Promise<BranchRunResponseData> {
  const res = await fetch(`${BASE_URL}/api/branch/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Branch verification API failed (${res.status}): ${errorText}`);
  }
  return res.json();
}

export async function runCacheVerification(payload: CacheRunPayload): Promise<CacheRunResponseData> {
  const res = await fetch(`${BASE_URL}/api/cache/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Cache verification API failed (${res.status}): ${errorText}`);
  }
  return res.json();
}
