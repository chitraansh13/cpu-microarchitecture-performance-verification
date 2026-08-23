import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    HealthResponse,
    ToolchainStatus,
    VerifyRequest,
    VerifyResponse,
    RegressionRequest,
    RegressionResponse,
    StressRequest,
    StressResponse,
    EdgeCasesResponse,
    BranchRunRequest,
    BranchRunResponse,
    CacheRunRequest,
    CacheRunResponse,
)
from .verification_service import (
    check_toolchain_availability,
    execute_interactive_verify,
    execute_baseline_regression,
    execute_stress_regression,
    execute_edge_case_regression,
    execute_branch_run,
    execute_cache_run,
)


app = FastAPI(
    title="CPU Microarchitecture Performance Verification API",
    description="Backend service providing interactive RTL execution, golden-model comparison, and regression execution.",
    version="1.0.0",
)

# Configure CORS origins from environment variable
frontend_origin_env = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
if frontend_origin_env == "*":
    origins = ["*"]
else:
    origins = [o.strip() for o in frontend_origin_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/branch/run", response_model=BranchRunResponse)
def run_branch(request: BranchRunRequest):
    """Triggers custom or predefined branch predictor verification against real RTL."""
    return execute_branch_run(request)


@app.post("/api/cache/run", response_model=CacheRunResponse)
def run_cache(request: CacheRunRequest):
    """Triggers custom or predefined cache verification against real RTL."""
    return execute_cache_run(request)


@app.get("/api/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint returning system status and toolchain availability."""
    tc = check_toolchain_availability()
    return HealthResponse(
        status="ok",
        service="cpu-microarchitecture-verification",
        toolchain=ToolchainStatus(iverilog=tc["iverilog"], vvp=tc["vvp"]),
    )


@app.post("/api/verify", response_model=VerifyResponse)
def verify_interactive(request: VerifyRequest):
    """
    Triggers an interactive dual-path verification run for selected predictor & cache configurations.
    Executes temporary workload generation, Python golden modeling, Icarus RTL compilation & simulation,
    event-level comparison, and Estimated CPI calculation.
    """
    return execute_interactive_verify(request)


@app.post("/api/regression", response_model=RegressionResponse)
def run_baseline_regression(request: RegressionRequest = RegressionRequest()):
    """Executes the standard 14-case baseline regression suite."""
    return execute_baseline_regression(request)


@app.post("/api/stress", response_model=StressResponse)
def run_stress_regression(request: StressRequest = StressRequest()):
    """Executes multi-seed randomized stress regression across the specified seed range."""
    return execute_stress_regression(request)


@app.post("/api/edge-cases", response_model=EdgeCasesResponse)
def run_edge_cases():
    """Executes the 31 directed edge-case regression suite."""
    return execute_edge_case_regression()
