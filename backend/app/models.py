from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class ToolchainStatus(BaseModel):
    iverilog: bool
    vvp: bool


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "cpu-microarchitecture-verification"
    toolchain: ToolchainStatus


class VerifyRequest(BaseModel):
    predictor: Literal["1bit", "2bit"] = Field(
        default="2bit", description="Branch predictor hardware implementation type"
    )
    branch_workload: Literal["mostly_taken", "mostly_not_taken", "alternating", "loop", "random"] = Field(
        default="loop", description="Targeted synthetic branch outcome workload"
    )
    cache_workload: Literal["high_locality", "sequential", "random", "conflict"] = Field(
        default="high_locality", description="Targeted synthetic memory address workload"
    )
    seed: int = Field(default=42, description="Deterministic workload generation seed")
    branch_count: int = Field(default=1000, ge=1, le=5000, description="Number of branch transactions")
    memory_count: int = Field(default=1000, ge=1, le=5000, description="Number of memory transactions")
    instructions: int = Field(default=10000, ge=1, le=100000, description="Modeled instructions for CPI calculation")
    base_cpi: float = Field(default=1.0, ge=0.1, le=10.0, description="Ideal base CPI without stalls")
    branch_penalty: int = Field(default=3, ge=0, le=20, description="Branch misprediction penalty cycles")
    cache_miss_penalty: int = Field(default=10, ge=0, le=50, description="Cache miss penalty cycles")


class BranchVerifyResult(BaseModel):
    verified: bool
    total: int
    correct: int
    mispredictions: int
    accuracy: float


class CacheVerifyResult(BaseModel):
    verified: bool
    total: int
    hits: int
    misses: int
    hit_rate: float


class PerformanceResult(BaseModel):
    instructions: int
    base_cpi: float
    branch_penalty: int
    cache_miss_penalty: int
    base_cycles: float
    branch_penalty_cycles: float
    cache_penalty_cycles: float
    estimated_total_cycles: float
    estimated_cpi: float


class VerifyResponse(BaseModel):
    status: str
    configuration: Dict[str, Any]
    branch: Optional[BranchVerifyResult] = None
    cache: Optional[CacheVerifyResult] = None
    performance: Optional[PerformanceResult] = None
    error: Optional[str] = None
    mismatch_detail: Optional[str] = None


class RegressionRequest(BaseModel):
    seed: int = Field(default=42, description="Deterministic seed for regression workloads")
    branch_count: int = Field(default=1000, ge=1, le=5000)
    memory_count: int = Field(default=1000, ge=1, le=5000)


class CaseResult(BaseModel):
    component: str
    workload: str
    status: str
    total_events: int
    metric_name: str
    metric_value: float


class RegressionResponse(BaseModel):
    status: str
    cases: int
    passed: int
    failed: int
    verified_events: int
    results: List[Dict[str, Any]]
    error: Optional[str] = None


class StressRequest(BaseModel):
    start_seed: int = Field(default=1, ge=1, description="Starting seed index")
    num_seeds: int = Field(default=20, ge=1, le=20, description="Number of consecutive seeds to test (max 20)")
    branch_count: int = Field(default=1000, ge=1, le=5000)
    memory_count: int = Field(default=1000, ge=1, le=5000)


class StressResponse(BaseModel):
    status: str
    seeds_tested: int
    total_cases: int
    passed: int
    failed: int
    verified_events: int
    error: Optional[str] = None


class EdgeCasesResponse(BaseModel):
    status: str
    cases: int
    passed: int
    failed: int
    verified_events: int
    results: List[Dict[str, Any]]
    error: Optional[str] = None


class BranchRunRequest(BaseModel):
    predictor: Literal["1bit", "2bit", "both"] = Field(
        default="both", description="Branch predictor type or comparison mode"
    )
    workload_type: Literal["mostly_taken", "mostly_not_taken", "alternating", "loop", "random", "custom"] = Field(
        default="custom", description="Workload trace type"
    )
    trace: Optional[str] = Field(
        default="T T N T N N T T T N", description="Custom branch outcome trace string"
    )
    seed: int = Field(default=42, ge=0)
    count: int = Field(default=1000, ge=1, le=5000)


class BranchRunResponse(BaseModel):
    status: str
    input_trace: List[int] = Field(default_factory=list)
    predictor: Optional[str] = None
    verified: bool = False
    total: Optional[int] = None
    correct: Optional[int] = None
    incorrect: Optional[int] = None
    accuracy: Optional[float] = None
    events: Optional[List[Dict[str, Any]]] = None
    predictors: Optional[Dict[str, Any]] = None
    accuracy_delta: Optional[float] = None
    trace_length: Optional[int] = None
    error: Optional[str] = None


class CacheRunRequest(BaseModel):
    workload_type: Literal["high_locality", "sequential", "random", "conflict", "custom"] = Field(
        default="custom", description="Memory address workload trace type"
    )
    addresses: Optional[str] = Field(
        default="0x100 0x104 0x108 0x100", description="Custom memory address trace string"
    )
    seed: int = Field(default=42, ge=0)
    count: int = Field(default=1000, ge=1, le=5000)


class CacheConfiguration(BaseModel):
    cache_lines: int = 4
    block_size_bytes: int = 4
    address_width_bits: int = 16


class CacheRunResponse(BaseModel):
    status: str
    verified: bool = False
    configuration: CacheConfiguration = Field(default_factory=CacheConfiguration)
    input_addresses: List[int] = Field(default_factory=list)
    total: int = 0
    hits: int = 0
    misses: int = 0
    hit_rate: float = 0.0
    miss_rate: float = 0.0
    events: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
