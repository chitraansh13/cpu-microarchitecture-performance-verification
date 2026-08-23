import { useState, useEffect } from 'react';
import { PageShell } from './components/PageShell';
import { SectionHeader } from './components/SectionHeader';
import { VerificationCard } from './components/VerificationCard';
import { BranchChart } from './components/BranchChart';
import { CacheChart } from './components/CacheChart';
import { StatusBadge } from './components/StatusBadge';
import { PredictorStateMachine } from './components/PredictorStateMachine';
import { CacheVisualization } from './components/CacheVisualization';
import { QuickComposer } from './components/QuickComposer';
import {
  ArrowRight, Activity, Database, ShieldCheck, Play, AlertTriangle, Cpu, Zap, Layers,
  Terminal, Server, Code, FileCode, CheckSquare, RefreshCw, CpuIcon, Sparkles, CheckCircle2,
  Info
} from 'lucide-react';
import {
  VERIFICATION_CAMPAIGNS,
} from './data/verifiedResults';
import {
  checkHealth,
  runBaselineRegression,
  runStressRegression,
  runEdgeCases,
  runBranchVerification,
  runCacheVerification,
  BranchRunPayload,
  BranchRunResponseData,
  CacheRunPayload,
  CacheRunResponseData,
  RegressionResponseData,
  StressResponseData,
  EdgeCasesResponseData,
} from './lib/api';

const formatMetricValue = (val: any): string => {
  if (val === null || val === undefined) return '—';
  if (typeof val === 'number') {
    if (Number.isInteger(val)) {
      return val.toLocaleString();
    }
    return `${val.toFixed(1)}%`;
  }
  const strVal = String(val);
  const numVal = parseFloat(strVal.replace('%', ''));
  if (!isNaN(numVal) && (strVal.includes('.') || strVal.includes('%'))) {
    return `${numVal.toFixed(1)}%`;
  }
  return strVal;
};

const getStatusCopy = (status?: string, error?: string | null) => {
  if (error || status === 'ERROR') return 'Verification could not complete';
  if (status === 'FAIL') return 'RTL differs from Python golden model';
  return 'RTL matches Python golden model';
};

export function App() {
  const [activeSection, setActiveSection] = useState('overview');
  const [isEngineOnline, setIsEngineOnline] = useState<boolean | null>(null);

  // Overview Interactive Command Bar Input State (Fully Editable React State)
  const [overviewInputState, setOverviewInputState] = useState<string>('T T T T N T T T N T');

  // Branch Predictor Interactive State
  const [branchPredictorMode, setBranchPredictorMode] = useState<'1bit' | '2bit' | 'both'>('both');
  const [branchWorkloadType, setBranchWorkloadType] = useState<'mostly_taken' | 'mostly_not_taken' | 'alternating' | 'loop' | 'random' | 'custom'>('custom');
  const [branchCustomTrace, setBranchCustomTrace] = useState<string>('T T T T N T T T N T');
  const [isBranchRunning, setIsBranchRunning] = useState<boolean>(false);
  const [branchResult, setBranchResult] = useState<BranchRunResponseData | null>(null);
  const [branchError, setBranchError] = useState<string | null>(null);

  // Cache Interactive State
  const [cacheWorkloadType, setCacheWorkloadType] = useState<'high_locality' | 'sequential' | 'random' | 'conflict' | 'custom'>('custom');
  const [cacheCustomAddresses, setCacheCustomAddresses] = useState<string>('0x0000 0x0000 0x0004 0x0004 0x0010 0x0000 0x0000');
  const [isCacheRunning, setIsCacheRunning] = useState<boolean>(false);
  const [cacheResult, setCacheResult] = useState<CacheRunResponseData | null>(null);
  const [cacheError, setCacheError] = useState<string | null>(null);

  // Performance Interactive Inputs
  const [perfInstructions, setPerfInstructions] = useState<number>(10000);
  const [perfBaseCpi, setPerfBaseCpi] = useState<number>(1.0);
  const [perfBranchPenalty, setPerfBranchPenalty] = useState<number>(3);
  const [perfCachePenalty, setPerfCachePenalty] = useState<number>(10);

  // Regression Campaign State
  const [activeRunType, setActiveRunType] = useState<'baseline' | 'stress' | 'edge'>('baseline');
  const [baselineRunState, setBaselineRunState] = useState<{ status: 'IDLE' | 'RUNNING' | 'PASS' | 'FAIL' | 'ERROR'; data?: RegressionResponseData; error?: string }>({ status: 'IDLE' });
  const [stressRunState, setStressRunState] = useState<{ status: 'IDLE' | 'RUNNING' | 'PASS' | 'FAIL' | 'ERROR'; numSeeds: number; data?: StressResponseData; error?: string }>({ status: 'IDLE', numSeeds: 20 });
  const [edgeRunState, setEdgeRunState] = useState<{ status: 'IDLE' | 'RUNNING' | 'PASS' | 'FAIL' | 'ERROR'; data?: EdgeCasesResponseData; error?: string }>({ status: 'IDLE' });

  // Initial Health Check
  useEffect(() => {
    let isMounted = true;
    checkHealth()
      .then((data) => {
        if (isMounted) {
          setIsEngineOnline(data.status === 'ok' && data.toolchain.iverilog && data.toolchain.vvp);
        }
      })
      .catch(() => {
        if (isMounted) {
          setIsEngineOnline(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleRunOverviewAnalysis = (commandText: string) => {
    if (!commandText.trim()) return;
    
    // Check if input looks like hex memory addresses (0x...) or branch trace (T/N)
    if (commandText.includes('0x') || commandText.includes('0X')) {
      setCacheWorkloadType('custom');
      setCacheCustomAddresses(commandText);
      setActiveSection('cache');
      handleRunCacheRtl();
    } else {
      setBranchWorkloadType('custom');
      setBranchCustomTrace(commandText);
      setActiveSection('branch');
      handleRunBranchRtl();
    }
  };

  const handleOverviewPreset = (presetType: 'trace' | 'cache' | 'example') => {
    if (presetType === 'trace') {
      setOverviewInputState('T T T T N T T T N T');
    } else if (presetType === 'cache') {
      setOverviewInputState('0x0000 0x0004 0x0010 0x0000 0x0004');
    } else {
      setOverviewInputState('T N T N T N T N T N');
    }
  };

  const handleRunBranchRtl = async () => {
    setIsBranchRunning(true);
    setBranchError(null);
    const payload: BranchRunPayload = {
      predictor: branchPredictorMode,
      workload_type: branchWorkloadType,
      trace: branchWorkloadType === 'custom' ? branchCustomTrace : undefined,
    };
    try {
      const res = await runBranchVerification(payload);
      setBranchResult(res);
      if (res.error) {
        setBranchError(res.error);
      }
    } catch (err: any) {
      setBranchError(err.message || 'Failed to execute branch verification API');
    } finally {
      setIsBranchRunning(false);
    }
  };

  const handleRunCacheRtl = async () => {
    setIsCacheRunning(true);
    setCacheError(null);
    const payload: CacheRunPayload = {
      workload_type: cacheWorkloadType,
      addresses: cacheWorkloadType === 'custom' ? cacheCustomAddresses : undefined,
    };
    try {
      const res = await runCacheVerification(payload);
      setCacheResult(res);
      if (res.error) {
        setCacheError(res.error);
      }
    } catch (err: any) {
      setCacheError(err.message || 'Failed to execute cache verification API');
    } finally {
      setIsCacheRunning(false);
    }
  };

  const handleRunBaseline = async () => {
    setActiveRunType('baseline');
    setBaselineRunState({ status: 'RUNNING' });
    try {
      const res = await runBaselineRegression({ seed: 42 });
      setBaselineRunState({ status: res.status, data: res, error: res.error || undefined });
    } catch (err: any) {
      setBaselineRunState({ status: 'ERROR', error: err.message || 'Baseline regression API error' });
    }
  };

  const handleRunStress = async () => {
    setActiveRunType('stress');
    setStressRunState((prev) => ({ ...prev, status: 'RUNNING' }));
    try {
      const res = await runStressRegression({ start_seed: 1, num_seeds: stressRunState.numSeeds });
      setStressRunState((prev) => ({ ...prev, status: res.status, data: res, error: res.error || undefined }));
    } catch (err: any) {
      setStressRunState((prev) => ({ ...prev, status: 'ERROR', error: err.message || 'Stress regression API error' }));
    }
  };

  const handleRunEdgeCases = async () => {
    setActiveRunType('edge');
    setEdgeRunState({ status: 'RUNNING' });
    try {
      const res = await runEdgeCases();
      setEdgeRunState({ status: res.status, data: res, error: res.error || undefined });
    } catch (err: any) {
      setEdgeRunState({ status: 'ERROR', error: err.message || 'Edge cases API error' });
    }
  };

  // Performance calculations
  const branchMispredictions = 166;
  const cacheMisses = 4;
  const extraBranchCycles = branchMispredictions * perfBranchPenalty;
  const extraCacheCycles = cacheMisses * perfCachePenalty;
  const baseCycles = perfInstructions * perfBaseCpi;
  const estimatedTotalCycles = baseCycles + extraBranchCycles + extraCacheCycles;
  const estimatedCpi = estimatedTotalCycles / perfInstructions;

  // Compute branch trace tokens for state machine visualization
  const parsedBranchTokens = branchCustomTrace
    .trim()
    .split(/[\s,]+/)
    .map((t) => (t.toUpperCase() === 'T' || t === '1' ? 1 : 0));

  return (
    <PageShell activeSection={activeSection} setActiveSection={setActiveSection} isEngineOnline={isEngineOnline}>
      
      {/* Engine Offline Warning */}
      {isEngineOnline === false && (
        <div className="bg-[#FDF8EE] border border-[#F3E3C3] rounded-xl p-4 flex items-start gap-3 text-xs text-[#B58B4A] font-sans shadow-2xs">
          <AlertTriangle className="w-4 h-4 text-[#B58B4A] flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold font-mono text-[#8C6225]">Verification Engine Offline</span> &mdash; Start the FastAPI backend server (`python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`) with Icarus Verilog (`iverilog`/`vvp`) installed to execute live RTL simulations. Static verified benchmarks remain available.
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* HOME / OVERVIEW EDITORIAL LAUNCHER PAGE */}
      {/* ========================================================================= */}
      {activeSection === 'overview' && (
        <section id="overview" className="space-y-6 animate-reveal">
          
          {/* 1. EDITORIAL HERO */}
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 py-4 border-b border-[#D8D0C1] pb-6">
            <div className="max-w-2xl">
              <div className="text-xs font-mono font-bold text-[#B58B4A] tracking-widest uppercase mb-2">
                CPU MICROARCHITECTURE LAB
              </div>
              <h1 className="text-4xl sm:text-5xl font-serif-hero font-extrabold text-[#10213A] tracking-tight leading-[1.15]">
                Verify RTL.<br />
                Compare architectures.<br />
                Analyze behavior.
              </h1>
              <div className="w-16 h-0.5 bg-[#B58B4A] my-3.5"></div>
              <p className="text-base text-[#5B6370] font-sans leading-relaxed">
                Run workload-driven analysis, compare microarchitectures, and surface what matters.
              </p>
            </div>

            {/* Right Side: Technical Summary & SVG Chip Motif */}
            <div className="flex items-center gap-5 self-start lg:self-center font-mono bg-[#FFFDF8] border border-[#D8D0C1] p-5 rounded-2xl shadow-xs">
              <svg className="w-12 h-12 text-[#112A4E] flex-shrink-0" viewBox="0 0 40 40" fill="none">
                <rect x="8" y="8" width="24" height="24" rx="3" stroke="#112A4E" strokeWidth="2" fill="#FCF9F2" />
                <rect x="14" y="14" width="12" height="12" rx="1.5" fill="#B58B4A" fillOpacity="0.3" stroke="#B58B4A" strokeWidth="1.5" />
                <path d="M4 14H8M4 20H8M4 26H8M32 14H36M32 20H36M32 26H36M14 4V8M20 4V8M26 4V8M14 32V36M20 32V36M26 32V36" stroke="#7D8592" strokeWidth="1.5" strokeLinecap="round" />
              </svg>

              <div>
                <div className="text-3xl font-extrabold text-[#10213A] tracking-tight">
                  280,000+
                </div>
                <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#B58B4A] mt-0.5">
                  RTL EVENTS VERIFIED
                </div>
                <div className="text-xs font-mono text-[#5B6370] mt-1">
                  14/14 baseline &middot; 280/280 stress &middot; 31/31 directed
                </div>
              </div>
            </div>
          </div>

          {/* 2. REAL INTERACTIVE COMMAND COMPOSER */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-[#10213A] font-sans">
              Interactive Analysis Command Composer
            </label>
            <QuickComposer
              value={overviewInputState}
              onChange={setOverviewInputState}
              onRunAnalysis={handleRunOverviewAnalysis}
              onPreset={handleOverviewPreset}
            />
          </div>

          {/* 3. FOUR WORKFLOW PANELS */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            
            {/* Panel A — Branch Predictor Lab */}
            <div className="bg-[#FFFDF8] border border-[#D8D0C1] hover:border-[#B58B4A] rounded-2xl p-5 shadow-xs transition-all flex flex-col justify-between group">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-xl bg-[#F1EADF] text-[#112A4E] flex items-center justify-center border border-[#D8D0C1]">
                      <Activity className="w-4 h-4 text-[#B58B4A]" />
                    </div>
                    <h2 className="text-base font-serif-hero font-bold text-[#10213A]">Branch Predictor Lab</h2>
                  </div>
                  <span className="text-xs font-mono bg-[#F1EADF] px-2.5 py-1 rounded-lg text-[#10213A] border border-[#D8D0C1] font-medium">
                    [T] [T] [T] [T] [N]
                  </span>
                </div>
                <p className="text-xs text-[#5B6370] leading-relaxed font-sans mb-3">
                  Compare predictor strategies on real traces.
                </p>

                {/* Token Strip Visual */}
                <div className="flex items-center gap-1 font-mono text-xs my-2">
                  {['T', 'T', 'T', 'T', 'N', 'T', 'T', 'T', 'N', 'T'].map((t, idx) => (
                    <span key={idx} className={`w-6 h-6 rounded flex items-center justify-center font-bold text-[11px] ${
                      t === 'T' ? 'bg-[#EAF2EC] text-[#356044] border border-[#C3DCC8]' : 'bg-[#F1EADF] text-[#5B6370]'
                    }`}>
                      {t}
                    </span>
                  ))}
                </div>
              </div>

              <div className="pt-4 flex items-center justify-between border-t border-[#D8D0C1]/70 mt-3">
                <span className="text-xs font-mono text-[#5B6370]">Accuracy: <strong className="text-[#356044]">80.0%</strong> &middot; 2 Mispredicts</span>
                <button
                  onClick={() => setActiveSection('branch')}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#112A4E] hover:bg-[#0A1A32] text-[#FFFDF8] text-xs font-semibold transition-colors shadow-2xs"
                >
                  Open Branch Lab
                  <ArrowRight className="w-3.5 h-3.5 text-[#B58B4A]" />
                </button>
              </div>
            </div>

            {/* Panel B — Cache Behavior Lab */}
            <div className="bg-[#FFFDF8] border border-[#D8D0C1] hover:border-[#B58B4A] rounded-2xl p-5 shadow-xs transition-all flex flex-col justify-between group">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-xl bg-[#F1EADF] text-[#112A4E] flex items-center justify-center border border-[#D8D0C1]">
                      <Database className="w-4 h-4 text-[#B58B4A]" />
                    </div>
                    <h2 className="text-base font-serif-hero font-bold text-[#10213A]">Cache Behavior Lab</h2>
                  </div>
                  <span className="text-xs font-mono bg-[#F1EADF] px-2.5 py-1 rounded-lg text-[#10213A] border border-[#D8D0C1] font-medium">
                    L0 &middot; L1 &middot; L2 &middot; L3
                  </span>
                </div>
                <p className="text-xs text-[#5B6370] leading-relaxed font-sans mb-3">
                  Inspect hit/miss behavior and memory behavior.
                </p>

                {/* 4-Line Cache Strip Visual */}
                <div className="grid grid-cols-4 gap-1.5 text-center font-mono text-[10px] my-2">
                  <div className="p-1.5 rounded bg-[#EAF2EC] border border-[#C3DCC8] text-[#356044] font-bold">L0: HIT</div>
                  <div className="p-1.5 rounded bg-[#EAF2EC] border border-[#C3DCC8] text-[#356044] font-bold">L1: HIT</div>
                  <div className="p-1.5 rounded bg-[#FDF8EE] border border-[#F3E3C3] text-[#B58B4A] font-bold">L2: MISS</div>
                  <div className="p-1.5 rounded bg-[#FDF8EE] border border-[#F3E3C3] text-[#B58B4A] font-bold">L3: MISS</div>
                </div>
              </div>

              <div className="pt-4 flex items-center justify-between border-t border-[#D8D0C1]/70 mt-3">
                <span className="text-xs font-mono text-[#5B6370]">Hit Rate: <strong className="text-[#112A4E]">42.86%</strong> &middot; 3 Hits</span>
                <button
                  onClick={() => setActiveSection('cache')}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#112A4E] hover:bg-[#0A1A32] text-[#FFFDF8] text-xs font-semibold transition-colors shadow-2xs"
                >
                  Open Cache Lab
                  <ArrowRight className="w-3.5 h-3.5 text-[#B58B4A]" />
                </button>
              </div>
            </div>

            {/* Panel C — Verification Suite Matrix */}
            <div className="bg-[#FFFDF8] border border-[#D8D0C1] hover:border-[#B58B4A] rounded-2xl p-5 shadow-xs transition-all flex flex-col justify-between group">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-xl bg-[#F1EADF] text-[#112A4E] flex items-center justify-center border border-[#D8D0C1]">
                      <ShieldCheck className="w-4 h-4 text-[#B58B4A]" />
                    </div>
                    <h2 className="text-base font-serif-hero font-bold text-[#10213A]">Verification Suite</h2>
                  </div>
                  <span className="text-xs font-mono bg-[#EAF2EC] px-2.5 py-1 rounded-lg text-[#356044] border border-[#C3DCC8] font-bold">
                    ✓ 100% Pass Rate
                  </span>
                </div>
                <p className="text-xs text-[#5B6370] leading-relaxed font-sans mb-3">
                  Run baseline, stress, and directed verification campaigns.
                </p>

                {/* 4x3 Matrix Visual */}
                <div className="text-xs font-mono grid grid-cols-4 gap-1 text-center bg-[#FCF9F2] p-2 rounded-xl border border-[#D8D0C1] my-2">
                  <span className="text-[#5B6370] text-left">suite</span>
                  <span className="text-[#356044] font-bold">base</span>
                  <span className="text-[#356044] font-bold">str</span>
                  <span className="text-[#356044] font-bold">dir</span>
                  <span className="text-left font-medium text-[#10213A]">core</span><span className="text-[#356044]">✓</span><span className="text-[#356044]">✓</span><span className="text-[#356044]">✓</span>
                  <span className="text-left font-medium text-[#10213A]">thrash</span><span className="text-[#356044]">✓</span><span className="text-[#356044]">✓</span><span className="text-[#356044]">✓</span>
                </div>
              </div>

              <div className="pt-4 flex items-center justify-between border-t border-[#D8D0C1]/70 mt-3">
                <span className="text-xs font-mono text-[#5B6370]">325 Total Runs &middot; 0 Failures</span>
                <button
                  onClick={() => setActiveSection('regression')}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#112A4E] hover:bg-[#0A1A32] text-[#FFFDF8] text-xs font-semibold transition-colors shadow-2xs"
                >
                  Open Suite
                  <ArrowRight className="w-3.5 h-3.5 text-[#B58B4A]" />
                </button>
              </div>
            </div>

            {/* Panel D — Performance Model */}
            <div className="bg-[#FFFDF8] border border-[#D8D0C1] hover:border-[#B58B4A] rounded-2xl p-5 shadow-xs transition-all flex flex-col justify-between group">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-xl bg-[#F1EADF] text-[#112A4E] flex items-center justify-center border border-[#D8D0C1]">
                      <Zap className="w-4 h-4 text-[#B58B4A]" />
                    </div>
                    <h2 className="text-base font-serif-hero font-bold text-[#10213A]">Performance Model</h2>
                  </div>
                  <span className="text-xs font-mono bg-[#F1EADF] px-2.5 py-1 rounded-lg text-[#10213A] border border-[#D8D0C1] font-medium">
                    CPI = Base + Penalty
                  </span>
                </div>
                <p className="text-xs text-[#5B6370] leading-relaxed font-sans mb-3">
                  Estimate CPI and inspect penalties using verified results.
                </p>
                <div className="text-xs font-mono bg-[#FCF9F2] p-2 rounded-xl border border-[#D8D0C1] text-[#5B6370] flex justify-between my-2">
                  <span>Base: 1.0</span>
                  <span>Branch: +0.0498</span>
                  <span>L1D: +0.0040</span>
                </div>
              </div>

              <div className="pt-4 flex items-center justify-between border-t border-[#D8D0C1]/70 mt-3">
                <span className="text-xs font-mono text-[#5B6370]">Est. CPI: <strong className="text-[#112A4E]">1.0538</strong></span>
                <button
                  onClick={() => setActiveSection('performance')}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#112A4E] hover:bg-[#0A1A32] text-[#FFFDF8] text-xs font-semibold transition-colors shadow-2xs"
                >
                  Open Model
                  <ArrowRight className="w-3.5 h-3.5 text-[#B58B4A]" />
                </button>
              </div>
            </div>

          </div>

          {/* 4. VERIFICATION PIPELINE */}
          <div className="bg-[#FFFDF8] border border-[#D8D0C1] rounded-2xl p-5 shadow-xs">
            <div className="text-xs font-mono uppercase font-bold text-[#5B6370] tracking-wider mb-3">
              VERIFICATION PIPELINE
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-5 gap-3 font-mono text-xs text-center">
              <div className="p-3 rounded-xl bg-[#FCF9F2] border border-[#D8D0C1] flex items-center justify-center gap-2">
                <Code className="w-4 h-4 text-[#B58B4A]" />
                <span className="font-bold text-[#10213A]">Workload</span>
              </div>
              
              <div className="p-3 rounded-xl bg-[#F1EADF] border border-[#D8D0C1] flex items-center justify-center gap-2 text-[#112A4E]">
                <Cpu className="w-4 h-4 text-[#112A4E]" />
                <span className="font-bold">RTL Simulation</span>
              </div>
              
              <div className="p-3 rounded-xl bg-[#FCF9F2] border border-[#D8D0C1] flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4 text-[#7D8592]" />
                <span className="font-bold text-[#10213A]">Python Golden</span>
              </div>
              
              <div className="p-3 rounded-xl bg-[#FCF9F2] border border-[#D8D0C1] flex items-center justify-center gap-2">
                <CheckSquare className="w-4 h-4 text-[#7D8592]" />
                <span className="font-bold text-[#10213A]">Event Compare</span>
              </div>
              
              <div className="p-3 rounded-xl bg-[#EAF2EC] border border-[#C3DCC8] flex items-center justify-center gap-2 text-[#356044] font-bold">
                <CheckCircle2 className="w-4 h-4 text-[#356044]" />
                <span>Verified</span>
              </div>
            </div>
          </div>

        </section>
      )}

      {/* ========================================================================= */}
      {/* BRANCH PREDICTOR LAB PAGE */}
      {/* ========================================================================= */}
      {activeSection === 'branch' && (
        <section id="branch" className="space-y-6 animate-reveal">
          <SectionHeader
            title="Branch Predictor Lab"
            subtitle="Explore how 1-bit and 2-bit predictors respond to the same branch behavior."
            tag="BRANCH LAB"
          />

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            {/* Top Input Command Composer */}
            <div className="lg:col-span-5 bg-[#FFFDF8] border border-[#D8D0C1] rounded-2xl p-6 shadow-xs space-y-5">
              <div className="flex items-center justify-between border-b border-[#D8D0C1] pb-3">
                <h3 className="text-xs font-bold text-[#5B6370] uppercase tracking-wider font-mono">Trace &amp; Predictor Composer</h3>
                <span className="text-[10px] font-mono text-[#112A4E] bg-[#F1EADF] px-2.5 py-1 rounded-md border border-[#D8D0C1] font-semibold">
                  Icarus Verilog
                </span>
              </div>

              {/* Predictor Selector */}
              <div>
                <label className="block text-xs font-semibold text-[#10213A] mb-2 font-sans">Predictor Target</label>
                <div className="grid grid-cols-3 gap-1.5 bg-[#F1EADF] p-1.5 rounded-xl text-xs font-mono">
                  {(['1bit', '2bit', 'both'] as const).map((mode) => (
                    <button
                      key={mode}
                      onClick={() => setBranchPredictorMode(mode)}
                      className={`py-2 px-2 rounded-lg font-bold text-center transition-all ${
                        branchPredictorMode === mode
                          ? 'bg-[#FFFDF8] text-[#112A4E] shadow-2xs border border-[#D8D0C1]'
                          : 'text-[#5B6370] hover:text-[#10213A]'
                      }`}
                    >
                      {mode === '1bit' ? '1-bit' : mode === '2bit' ? '2-bit' : 'Both'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Workload Selection with Visual Custom vs Preset Separation */}
              <div>
                <label className="block text-xs font-semibold text-[#10213A] mb-1 font-sans">Workload Selection</label>
                <select
                  value={branchWorkloadType}
                  onChange={(e) => setBranchWorkloadType(e.target.value as any)}
                  className="w-full text-xs font-mono bg-[#FCF9F2] border border-[#D8D0C1] rounded-xl p-3 text-[#10213A] focus:outline-none focus:ring-2 focus:ring-[#B58B4A]"
                >
                  <optgroup label="CUSTOM WORKLOAD">
                    <option value="custom">Custom Trace (Editable)</option>
                  </optgroup>
                  <optgroup label="PRESET WORKLOADS">
                    <option value="mostly_taken">Mostly Taken (80% T)</option>
                    <option value="mostly_not_taken">Mostly Not Taken (80% N)</option>
                    <option value="alternating">Alternating (T N T N T N)</option>
                    <option value="loop">Loop Pattern (T T T T N)</option>
                    <option value="random">Random Synthetic</option>
                  </optgroup>
                </select>

                <p className="text-[11px] text-[#5B6370] font-sans mt-1.5 flex items-start gap-1 leading-normal">
                  <Info className="w-3.5 h-3.5 text-[#B58B4A] flex-shrink-0 mt-0.5" />
                  {branchWorkloadType === 'custom'
                    ? 'Custom: Runs exactly the trace you provide through the live SystemVerilog DUT.'
                    : 'Preset: Generates a standard reproducible workload, then runs it through the same live RTL pipeline.'}
                </p>
              </div>

              {/* Custom Trace Textarea */}
              {branchWorkloadType === 'custom' && (
                <div>
                  <label className="block text-xs font-semibold text-[#10213A] mb-1.5 font-sans">
                    Trace <span className="text-[#5B6370] font-mono font-normal">(T = Taken, N = Not Taken)</span>
                  </label>
                  <textarea
                    rows={3}
                    value={branchCustomTrace}
                    onChange={(e) => setBranchCustomTrace(e.target.value)}
                    placeholder="T T T T N T T T N T"
                    className="w-full text-xs font-mono bg-[#FCF9F2] border border-[#D8D0C1] rounded-xl p-3 text-[#10213A] focus:outline-none focus:ring-2 focus:ring-[#B58B4A] tracking-wider"
                  />
                </div>
              )}

              {/* Primary Run Action */}
              <button
                onClick={handleRunBranchRtl}
                disabled={isBranchRunning}
                className="w-full py-3 px-4 rounded-xl bg-[#112A4E] hover:bg-[#0A1A32] disabled:opacity-50 text-[#FFFDF8] text-xs font-bold flex items-center justify-center gap-2 transition-colors shadow-xs tracking-wide font-sans"
              >
                <Play className="w-4 h-4 fill-current text-[#B58B4A]" />
                {isBranchRunning ? 'Executing RTL Simulation...' : 'RUN VERIFICATION'}
              </button>

              {branchError && (
                <div className="p-3 bg-[#FDF2F2] border border-[#E8C5C5] rounded-xl text-xs text-[#9A4744] font-mono">
                  {branchError}
                </div>
              )}
            </div>

            {/* Result Workspace Region */}
            <div className="lg:col-span-7 space-y-5">
              {branchResult ? (
                <div className="bg-[#FFFDF8] border border-[#D8D0C1] rounded-2xl p-6 shadow-xs space-y-6 animate-reveal">
                  
                  {/* RESULT HERO WITH CONDITIONAL STATUS COPY */}
                  <div className="flex items-center justify-between border-b border-[#D8D0C1] pb-4">
                    <div>
                      <span className="text-[10px] font-mono font-bold text-[#356044] uppercase tracking-wider">VERIFICATION STATUS</span>
                      <h3 className="text-lg font-serif-hero font-bold text-[#10213A] mt-0.5">
                        {getStatusCopy(branchResult.status, branchResult.error)}
                      </h3>
                    </div>
                    <StatusBadge status={branchResult.status} type={branchResult.status === 'PASS' ? 'emerald' : 'red'} />
                  </div>

                  {/* PROMINENT ARCHITECTURE COMPARISON HERO METRICS */}
                  <div className="grid grid-cols-3 gap-3 font-mono">
                    <div className="bg-[#FCF9F2] p-4 rounded-xl border border-[#D8D0C1]">
                      <div className="text-[10px] text-[#5B6370] uppercase font-semibold">1-BIT PREDICTOR</div>
                      <div className="text-2xl font-bold text-[#10213A] mt-1">
                        {branchResult.predictors?.['1bit'] ? `${formatMetricValue(branchResult.predictors['1bit'].accuracy)}` : `${formatMetricValue(branchResult.accuracy || 0)}`}
                      </div>
                      <div className="text-[10px] text-[#5B6370] mt-1">
                        {branchResult.predictors?.['1bit']?.incorrect ?? 0} mispredictions
                      </div>
                    </div>

                    <div className="bg-[#F1EADF] p-4 rounded-xl border border-[#D8D0C1] text-[#10213A]">
                      <div className="text-[10px] text-[#112A4E] uppercase font-bold">2-BIT PREDICTOR</div>
                      <div className="text-2xl font-bold text-[#112A4E] mt-1">
                        {branchResult.predictors?.['2bit'] ? `${formatMetricValue(branchResult.predictors['2bit'].accuracy)}` : `${formatMetricValue(branchResult.accuracy || 0)}`}
                      </div>
                      <div className="text-[10px] text-[#5B6370] mt-1">
                        {branchResult.predictors?.['2bit']?.incorrect ?? 0} mispredictions
                      </div>
                    </div>

                    <div className="bg-[#EAF2EC] p-4 rounded-xl border border-[#C3DCC8] text-[#356044]">
                      <div className="text-[10px] text-[#356044] uppercase font-bold">ACCURACY DELTA</div>
                      <div className="text-2xl font-bold text-[#356044] mt-1">
                        +{formatMetricValue(branchResult.accuracy_delta ?? 0)}
                      </div>
                      <div className="text-[10px] text-[#356044] mt-1">percentage points</div>
                    </div>
                  </div>

                  {/* 2-Bit State Machine Diagram Side Visual */}
                  <PredictorStateMachine currentTrace={parsedBranchTokens} />

                  {/* TRACE INSPECTOR TABLE */}
                  {branchResult.events && branchResult.events.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold text-[#10213A] font-mono">Trace Inspector Event Table</h4>
                        <span className="text-[10px] text-[#5B6370] font-mono">Predictor Correct = Quality &middot; RTL Verified = Correctness</span>
                      </div>
                      <div className="overflow-x-auto border border-[#D8D0C1] rounded-xl bg-[#FFFDF8]">
                        <table className="w-full text-left text-xs font-mono">
                          <thead className="bg-[#F1EADF] text-[10px] uppercase text-[#5B6370] border-b border-[#D8D0C1]">
                            <tr>
                              <th className="py-2.5 px-3">#</th>
                              <th className="py-2.5 px-3">Actual</th>
                              <th className="py-2.5 px-3">RTL Pred</th>
                              <th className="py-2.5 px-3">Golden Pred</th>
                              <th className="py-2.5 px-3 text-center">Predictor Correct?</th>
                              <th className="py-2.5 px-3 text-center">RTL Verified?</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-[#D8D0C1]/60">
                            {branchResult.events.map((evt, idx) => (
                              <tr key={idx} className="hover:bg-[#FCF9F2] transition-colors">
                                <td className="py-2.5 px-3 text-[#5B6370]">#{evt.branch}</td>
                                <td className="py-2.5 px-3">
                                  <span className={`px-2 py-0.5 rounded font-bold text-[11px] ${evt.actual === 1 ? 'bg-[#F1EADF] text-[#112A4E] border border-[#D8D0C1]' : 'bg-[#F6F2EA] text-[#5B6370]'}`}>
                                    {evt.actual === 1 ? 'T' : 'N'}
                                  </span>
                                </td>
                                <td className="py-2.5 px-3 font-bold text-[#10213A]">{evt.prediction === 1 ? 'T' : 'N'}</td>
                                <td className="py-2.5 px-3 text-[#5B6370]">{evt.expected_prediction === 1 ? 'T' : 'N'}</td>
                                <td className="py-2.5 px-3 text-center">
                                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${evt.correct ? 'bg-[#EAF2EC] text-[#356044] border border-[#C3DCC8]' : 'bg-[#FDF8EE] text-[#B58B4A] border border-[#F3E3C3]'}`}>
                                    {evt.correct ? 'Correct' : 'Mispredict'}
                                  </span>
                                </td>
                                <td className="py-2.5 px-3 text-center">
                                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${evt.match ? 'bg-[#EAF2EC] text-[#356044] border border-[#C3DCC8]' : 'bg-[#FDF2F2] text-[#9A4744] border border-[#E8C5C5]'}`}>
                                    {evt.match ? 'PASS' : 'FAIL'}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                /* INTENTIONAL MEANINGFUL EMPTY STATE */
                <div className="bg-[#FFFDF8] border border-[#D8D0C1] rounded-2xl p-10 shadow-xs text-center space-y-4">
                  <div className="w-12 h-12 rounded-2xl bg-[#F1EADF] text-[#112A4E] flex items-center justify-center mx-auto border border-[#D8D0C1]">
                    <Activity className="w-6 h-6 text-[#B58B4A]" />
                  </div>
                  <div>
                    <h3 className="text-base font-serif-hero font-bold text-[#10213A]">READY TO VERIFY</h3>
                    <p className="text-xs text-[#5B6370] max-w-md mx-auto mt-1 leading-relaxed">
                      Enter a branch trace and run the RTL simulation to inspect state transitions and golden-model equivalence.
                    </p>
                  </div>
                  <div className="inline-block p-3 rounded-xl bg-[#FCF9F2] border border-[#D8D0C1] font-mono text-xs text-[#5B6370]">
                    Sample trace: <strong className="text-[#10213A]">T T T T N T T T N T</strong>
                  </div>
                </div>
              )}
            </div>

          </div>
        </section>
      )}

      {/* ========================================================================= */}
      {/* CACHE BEHAVIOR LAB PAGE */}
      {/* ========================================================================= */}
      {activeSection === 'cache' && (
        <section id="cache" className="space-y-6 animate-reveal">
          <SectionHeader
            title="Cache Behavior Lab"
            subtitle="Inspect hit/miss behavior, tags, and index mapping on custom memory traces."
            tag="CACHE LAB"
          />

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            {/* Input Composer */}
            <div className="lg:col-span-5 bg-[#FFFDF8] border border-[#D8D0C1] rounded-2xl p-6 shadow-xs space-y-5">
              <div className="flex items-center justify-between border-b border-[#D8D0C1] pb-3">
                <h3 className="text-xs font-bold text-[#5B6370] uppercase tracking-wider font-mono">Memory Trace Composer</h3>
                <span className="text-[10px] font-mono text-[#112A4E] bg-[#F1EADF] px-2.5 py-1 rounded-md border border-[#D8D0C1] font-semibold">
                  Direct Cache
                </span>
              </div>

              {/* Hardware Spec Badge */}
              <div className="p-3.5 bg-[#FCF9F2] rounded-xl border border-[#D8D0C1] text-xs font-mono space-y-1">
                <div className="text-[10px] text-[#5B6370] uppercase font-semibold">Hardware Configuration</div>
                <div className="text-[#10213A] font-bold pt-0.5">
                  4 lines &middot; 4-byte blocks &middot; 16-bit addresses
                </div>
              </div>

              {/* Workload Selection with Visual Custom vs Preset Separation */}
              <div>
                <label className="block text-xs font-semibold text-[#10213A] mb-1 font-sans">Workload Selection</label>
                <select
                  value={cacheWorkloadType}
                  onChange={(e) => setCacheWorkloadType(e.target.value as any)}
                  className="w-full text-xs font-mono bg-[#FCF9F2] border border-[#D8D0C1] rounded-xl p-3 text-[#10213A] focus:outline-none focus:ring-2 focus:ring-[#B58B4A]"
                >
                  <optgroup label="CUSTOM WORKLOAD">
                    <option value="custom">Custom Memory Trace (Editable)</option>
                  </optgroup>
                  <optgroup label="PRESET WORKLOADS">
                    <option value="high_locality">High Spatial &amp; Temporal Locality</option>
                    <option value="sequential">Sequential Streaming (0x0, 0x4, 0x8...)</option>
                    <option value="random">Random Address Stream</option>
                    <option value="conflict">Index Conflict Thrashing</option>
                  </optgroup>
                </select>

                <p className="text-[11px] text-[#5B6370] font-sans mt-1.5 flex items-start gap-1 leading-normal">
                  <Info className="w-3.5 h-3.5 text-[#B58B4A] flex-shrink-0 mt-0.5" />
                  {cacheWorkloadType === 'custom'
                    ? 'Custom: Runs exactly the address trace you provide through the live SystemVerilog DUT.'
                    : 'Preset: Generates a standard reproducible workload, then runs it through the same live RTL pipeline.'}
                </p>
              </div>

              {/* Memory Trace Input */}
              {cacheWorkloadType === 'custom' && (
                <div>
                  <label className="block text-xs font-semibold text-[#10213A] mb-1.5 font-sans">
                    Memory Trace <span className="text-[#5B6370] font-mono font-normal">(Hex or Decimal)</span>
                  </label>
                  <textarea
                    rows={4}
                    value={cacheCustomAddresses}
                    onChange={(e) => setCacheCustomAddresses(e.target.value)}
                    placeholder="0x0000 0x0000 0x0004 0x0004 0x0010 0x0000 0x0000"
                    className="w-full text-xs font-mono bg-[#FCF9F2] border border-[#D8D0C1] rounded-xl p-3 text-[#10213A] focus:outline-none focus:ring-2 focus:ring-[#B58B4A] tracking-wider"
                  />
                </div>
              )}

              {/* Primary Action Button */}
              <button
                onClick={handleRunCacheRtl}
                disabled={isCacheRunning}
                className="w-full py-3 px-4 rounded-xl bg-[#112A4E] hover:bg-[#0A1A32] disabled:opacity-50 text-[#FFFDF8] text-xs font-bold flex items-center justify-center gap-2 transition-colors shadow-xs tracking-wide font-sans"
              >
                <Play className="w-4 h-4 fill-current text-[#B58B4A]" />
                {isCacheRunning ? 'Executing RTL Simulation...' : 'RUN CACHE VERIFICATION'}
              </button>

              {cacheError && (
                <div className="p-3 bg-[#FDF2F2] border border-[#E8C5C5] rounded-xl text-xs text-[#9A4744] font-mono">
                  {cacheError}
                </div>
              )}
            </div>

            {/* Results Workspace */}
            <div className="lg:col-span-7 space-y-5">
              {cacheResult ? (
                <div className="bg-[#FFFDF8] border border-[#D8D0C1] rounded-2xl p-6 shadow-xs space-y-6 animate-reveal">
                  
                  {/* RESULT HERO WITH CONDITIONAL STATUS COPY */}
                  <div className="flex items-center justify-between border-b border-[#D8D0C1] pb-4">
                    <div>
                      <span className="text-[10px] font-mono font-bold text-[#356044] uppercase tracking-wider">VERIFICATION STATUS</span>
                      <h3 className="text-lg font-serif-hero font-bold text-[#10213A] mt-0.5">
                        {getStatusCopy(cacheResult.status, cacheResult.error)}
                      </h3>
                    </div>
                    <StatusBadge status={cacheResult.status} type={cacheResult.status === 'PASS' ? 'emerald' : 'red'} />
                  </div>

                  {/* PRIMARY METRICS HERO GRID */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
                    <div className="bg-[#F1EADF] p-4 rounded-xl border border-[#D8D0C1] text-[#10213A]">
                      <div className="text-2xl font-bold text-[#112A4E]">{formatMetricValue(cacheResult.hit_rate)}</div>
                      <div className="text-[10px] text-[#112A4E] uppercase font-bold mt-0.5">HIT RATE</div>
                    </div>
                    <div className="bg-[#EAF2EC] p-4 rounded-xl border border-[#C3DCC8] text-[#356044]">
                      <div className="text-2xl font-bold text-[#356044]">{cacheResult.hits}</div>
                      <div className="text-[10px] text-[#356044] uppercase font-bold mt-0.5">HITS</div>
                    </div>
                    <div className="bg-[#FDF8EE] p-4 rounded-xl border border-[#F3E3C3] text-[#B58B4A]">
                      <div className="text-2xl font-bold text-[#B58B4A]">{cacheResult.misses}</div>
                      <div className="text-[10px] text-[#B58B4A] uppercase font-bold mt-0.5">MISSES</div>
                    </div>
                    <div className="bg-[#FCF9F2] p-4 rounded-xl border border-[#D8D0C1]">
                      <div className="text-2xl font-bold text-[#10213A]">{cacheResult.total}</div>
                      <div className="text-[10px] text-[#5B6370] uppercase font-semibold mt-0.5">ACCESSES</div>
                    </div>
                  </div>

                  {/* REAL CACHE LINE VISUALIZATION */}
                  <CacheVisualization events={cacheResult.events} />

                  {/* TRACE INSPECTOR TABLE */}
                  {cacheResult.events && cacheResult.events.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold text-[#10213A] font-mono">Trace Inspector Event Table</h4>
                      <div className="overflow-x-auto border border-[#D8D0C1] rounded-xl bg-[#FFFDF8]">
                        <table className="w-full text-left text-xs font-mono">
                          <thead className="bg-[#F1EADF] text-[10px] uppercase text-[#5B6370] border-b border-[#D8D0C1]">
                            <tr>
                              <th className="py-2.5 px-3">Access</th>
                              <th className="py-2.5 px-3">Address</th>
                              <th className="py-2.5 px-3">Index</th>
                              <th className="py-2.5 px-3">Tag</th>
                              <th className="py-2.5 px-3">RTL Result</th>
                              <th className="py-2.5 px-3">Golden Result</th>
                              <th className="py-2.5 px-3 text-center">Verified</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-[#D8D0C1]/60">
                            {cacheResult.events.map((evt, idx) => (
                              <tr key={idx} className="hover:bg-[#FCF9F2] transition-colors">
                                <td className="py-2.5 px-3 text-[#5B6370]">#{evt.access}</td>
                                <td className="py-2.5 px-3 font-bold text-[#10213A]">{evt.address_hex}</td>
                                <td className="py-2.5 px-3 text-[#5B6370]">{evt.index}</td>
                                <td className="py-2.5 px-3 text-[#5B6370]">0x{evt.tag.toString(16)}</td>
                                <td className="py-2.5 px-3">
                                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${evt.hit ? 'bg-[#EAF2EC] text-[#356044] border border-[#C3DCC8]' : 'bg-[#FDF8EE] text-[#B58B4A] border border-[#F3E3C3]'}`}>
                                    {evt.hit ? 'HIT' : 'MISS'}
                                  </span>
                                </td>
                                <td className="py-2.5 px-3 text-[#5B6370] font-semibold">{evt.expected_hit ? 'HIT' : 'MISS'}</td>
                                <td className="py-2.5 px-3 text-center">
                                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${evt.match ? 'bg-[#EAF2EC] text-[#356044] border border-[#C3DCC8]' : 'bg-[#FDF2F2] text-[#9A4744] border border-[#E8C5C5]'}`}>
                                    {evt.match ? 'PASS' : 'FAIL'}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                /* INTENTIONAL MEANINGFUL EMPTY STATE */
                <div className="bg-[#FFFDF8] border border-[#D8D0C1] rounded-2xl p-10 shadow-xs text-center space-y-4">
                  <div className="w-12 h-12 rounded-2xl bg-[#F1EADF] text-[#112A4E] flex items-center justify-center mx-auto border border-[#D8D0C1]">
                    <Database className="w-6 h-6 text-[#B58B4A]" />
                  </div>
                  <div>
                    <h3 className="text-base font-serif-hero font-bold text-[#10213A]">READY TO ANALYZE</h3>
                    <p className="text-xs text-[#5B6370] max-w-md mx-auto mt-1 leading-relaxed">
                      Enter memory addresses to inspect hit/miss behavior, tag comparisons, and index line mappings.
                    </p>
                  </div>
                  <div className="inline-block p-3 rounded-xl bg-[#FCF9F2] border border-[#D8D0C1] font-mono text-xs text-[#5B6370]">
                    Address stream: <strong className="text-[#10213A]">0x0000 &rarr; 0x0004 &rarr; 0x0010</strong>
                  </div>
                </div>
              )}
            </div>

          </div>
        </section>
      )}

      {/* ========================================================================= */}
      {/* REGRESSION SUITE PAGE */}
      {/* ========================================================================= */}
      {activeSection === 'regression' && (
        <section id="regression" className="space-y-6 animate-reveal">
          <SectionHeader
            title="Verification Suite"
            subtitle="Run baseline, stress, and directed verification campaigns."
            tag="VERIFICATION SUITE"
          />

          {/* Regression Pipeline Explanation */}
          <div className="bg-[#FCF9F2] border border-[#D8D0C1] rounded-2xl p-4 text-xs font-sans text-[#5B6370] leading-relaxed space-y-2">
            <div className="font-semibold text-[#10213A] flex items-center gap-1.5">
              <Info className="w-4 h-4 text-[#B58B4A]" />
              <span>How Regression Works</span>
            </div>
            <p>
              Regression campaigns generate predefined verification workloads and execute them through the same SystemVerilog + Python co-verification pipeline.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 font-mono text-[11px] pt-1">
              <div className="p-2 rounded bg-[#FFFDF8] border border-[#D8D0C1]">
                <strong className="text-[#10213A] block">Baseline:</strong> Deterministic standard workloads (14 test cases)
              </div>
              <div className="p-2 rounded bg-[#FFFDF8] border border-[#D8D0C1]">
                <strong className="text-[#10213A] block">Stress:</strong> Same suite repeated across multiple random seeds
              </div>
              <div className="p-2 rounded bg-[#FFFDF8] border border-[#D8D0C1]">
                <strong className="text-[#10213A] block">Directed:</strong> Pathological boundary &amp; edge cases (31 cases)
              </div>
            </div>
          </div>

          {/* Primary Action Controls */}
          <div className="bg-[#FFFDF8] border border-[#D8D0C1] rounded-2xl p-6 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-serif-hero font-bold text-[#10213A]">Verification Control Center</h3>
              <p className="text-xs text-[#5B6370] mt-0.5 font-sans">Execute automated co-verification suites against SystemVerilog RTL.</p>
            </div>
            
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={handleRunBaseline}
                disabled={baselineRunState.status === 'RUNNING'}
                className="px-4 py-2.5 bg-[#112A4E] hover:bg-[#0A1A32] disabled:opacity-50 text-[#FFFDF8] rounded-xl text-xs font-bold flex items-center gap-2 shadow-xs transition-colors tracking-wide font-sans"
              >
                <Play className="w-3.5 h-3.5 fill-current text-[#B58B4A]" />
                {baselineRunState.status === 'RUNNING' ? 'RUNNING BASELINE...' : 'RUN BASELINE'}
              </button>
              <button
                onClick={handleRunStress}
                disabled={stressRunState.status === 'RUNNING'}
                className="px-4 py-2.5 bg-[#F1EADF] hover:bg-[#E7DFC4] text-[#10213A] rounded-xl text-xs font-bold flex items-center gap-1.5 transition-colors border border-[#D8D0C1] font-sans"
              >
                {stressRunState.status === 'RUNNING' ? 'RUNNING STRESS...' : 'RUN STRESS'}
              </button>
              <button
                onClick={handleRunEdgeCases}
                disabled={edgeRunState.status === 'RUNNING'}
                className="px-4 py-2.5 bg-[#F1EADF] hover:bg-[#E7DFC4] text-[#10213A] rounded-xl text-xs font-bold flex items-center gap-1.5 transition-colors border border-[#D8D0C1] font-sans"
              >
                {edgeRunState.status === 'RUNNING' ? 'RUNNING EDGE...' : 'RUN EDGE CASES'}
              </button>
            </div>
          </div>

          {/* CURRENT LIVE RUN OUTPUT SECTION */}

          {/* 1. Baseline Live Output Surface */}
          {activeRunType === 'baseline' && baselineRunState.status !== 'IDLE' && (
            <div className="bg-[#FFFDF8] border border-[#D8D0C1] rounded-2xl p-6 shadow-xs space-y-5 animate-reveal">
              <div className="flex items-center justify-between border-b border-[#D8D0C1] pb-4">
                <div>
                  <span className="text-[10px] font-mono font-bold text-[#112A4E] tracking-wider uppercase">CURRENT LIVE RUN OUTPUT &middot; BASELINE SUITE</span>
                  <h3 className="text-lg font-serif-hero font-bold text-[#10213A] mt-0.5">
                    {getStatusCopy(baselineRunState.status, baselineRunState.error)}
                  </h3>
                </div>
                <StatusBadge
                  status={baselineRunState.status}
                  type={baselineRunState.status === 'PASS' ? 'emerald' : baselineRunState.status === 'FAIL' ? 'red' : baselineRunState.status === 'RUNNING' ? 'cyan' : 'amber'}
                />
              </div>

              {baselineRunState.data && (
                <>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
                    <div className="bg-[#FCF9F2] p-4 rounded-xl border border-[#D8D0C1]">
                      <div className="text-2xl font-bold text-[#10213A]">{baselineRunState.data.cases}</div>
                      <div className="text-[10px] text-[#5B6370] uppercase font-semibold mt-0.5">Cases Run</div>
                    </div>
                    <div className="bg-[#EAF2EC] p-4 rounded-xl border border-[#C3DCC8] text-[#356044]">
                      <div className="text-2xl font-bold text-[#356044]">{baselineRunState.data.passed}</div>
                      <div className="text-[10px] text-[#356044] uppercase font-bold mt-0.5">Passed</div>
                    </div>
                    <div className="bg-[#FCF9F2] p-4 rounded-xl border border-[#D8D0C1]">
                      <div className="text-2xl font-bold text-[#10213A]">{baselineRunState.data.failed}</div>
                      <div className="text-[10px] text-[#5B6370] uppercase font-semibold mt-0.5">Failed</div>
                    </div>
                    <div className="bg-[#F1EADF] p-4 rounded-xl border border-[#D8D0C1] text-[#10213A]">
                      <div className="text-2xl font-bold text-[#112A4E]">{baselineRunState.data.verified_events.toLocaleString()}</div>
                      <div className="text-[10px] text-[#112A4E] uppercase font-bold mt-0.5">Events Verified</div>
                    </div>
                  </div>

                  {/* Results List Table with clean metric formatting */}
                  {baselineRunState.data.results && baselineRunState.data.results.length > 0 && (
                    <div className="overflow-x-auto border border-[#D8D0C1] rounded-xl bg-[#FFFDF8]">
                      <table className="w-full text-left text-xs font-mono">
                        <thead className="bg-[#F1EADF] text-[10px] uppercase text-[#5B6370] border-b border-[#D8D0C1]">
                          <tr>
                            <th className="py-2.5 px-3">Test Case</th>
                            <th className="py-2.5 px-3">Component</th>
                            <th className="py-2.5 px-3">Workload</th>
                            <th className="py-2.5 px-3 text-right">Metric</th>
                            <th className="py-2.5 px-3 text-center">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#D8D0C1]/60">
                          {baselineRunState.data.results.map((res: any, idx: number) => (
                            <tr key={idx} className="hover:bg-[#FCF9F2] transition-colors">
                              <td className="py-2.5 px-3 font-semibold text-[#10213A]">{res.case_name || res.test_name}</td>
                              <td className="py-2.5 px-3 text-[#5B6370]">{res.component}</td>
                              <td className="py-2.5 px-3 text-[#5B6370]">{res.workload || res.pattern}</td>
                              <td className="py-2.5 px-3 text-right font-bold text-[#10213A]">{formatMetricValue(res.metric_value)}</td>
                              <td className="py-2.5 px-3 text-center">
                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${res.status === 'PASS' ? 'bg-[#EAF2EC] text-[#356044] border border-[#C3DCC8]' : 'bg-[#FDF2F2] text-[#9A4744] border border-[#E8C5C5]'}`}>
                                  {res.status}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              )}

              {baselineRunState.error && (
                <div className="p-4 bg-[#FDF8EE] border border-[#F3E3C3] rounded-xl text-xs text-[#B58B4A] font-mono">
                  {baselineRunState.error}
                </div>
              )}
            </div>
          )}

          {/* 2. Stress Live Output Surface */}
          {activeRunType === 'stress' && stressRunState.status !== 'IDLE' && (
            <div className="bg-[#FFFDF8] border border-[#D8D0C1] rounded-2xl p-6 shadow-xs space-y-5 animate-reveal">
              <div className="flex items-center justify-between border-b border-[#D8D0C1] pb-4">
                <div>
                  <span className="text-[10px] font-mono font-bold text-[#112A4E] tracking-wider uppercase">CURRENT LIVE RUN OUTPUT &middot; MULTI-SEED STRESS SUITE</span>
                  <h3 className="text-lg font-serif-hero font-bold text-[#10213A] mt-0.5">
                    {getStatusCopy(stressRunState.status, stressRunState.error)}
                  </h3>
                </div>
                <StatusBadge
                  status={stressRunState.status}
                  type={stressRunState.status === 'PASS' ? 'emerald' : stressRunState.status === 'FAIL' ? 'red' : stressRunState.status === 'RUNNING' ? 'cyan' : 'amber'}
                />
              </div>

              {stressRunState.data && (
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 font-mono text-xs">
                  <div className="bg-[#FCF9F2] p-4 rounded-xl border border-[#D8D0C1]">
                    <div className="text-2xl font-bold text-[#10213A]">{stressRunState.data.seeds_tested}</div>
                    <div className="text-[10px] text-[#5B6370] uppercase font-semibold mt-0.5">Seeds Tested</div>
                  </div>
                  <div className="bg-[#FCF9F2] p-4 rounded-xl border border-[#D8D0C1]">
                    <div className="text-2xl font-bold text-[#10213A]">{stressRunState.data.total_cases}</div>
                    <div className="text-[10px] text-[#5B6370] uppercase font-semibold mt-0.5">Cases Run</div>
                  </div>
                  <div className="bg-[#EAF2EC] p-4 rounded-xl border border-[#C3DCC8] text-[#356044]">
                    <div className="text-2xl font-bold text-[#356044]">{stressRunState.data.passed}</div>
                    <div className="text-[10px] text-[#356044] uppercase font-bold mt-0.5">Passed</div>
                  </div>
                  <div className="bg-[#FCF9F2] p-4 rounded-xl border border-[#D8D0C1]">
                    <div className="text-2xl font-bold text-[#10213A]">{stressRunState.data.failed}</div>
                    <div className="text-[10px] text-[#5B6370] uppercase font-semibold mt-0.5">Failed</div>
                  </div>
                  <div className="bg-[#F1EADF] p-4 rounded-xl border border-[#D8D0C1] text-[#10213A]">
                    <div className="text-2xl font-bold text-[#112A4E]">{stressRunState.data.verified_events.toLocaleString()}</div>
                    <div className="text-[10px] text-[#112A4E] uppercase font-bold mt-0.5">Events Verified</div>
                  </div>
                </div>
              )}

              {stressRunState.error && (
                <div className="p-4 bg-[#FDF8EE] border border-[#F3E3C3] rounded-xl text-xs text-[#B58B4A] font-mono">
                  {stressRunState.error}
                </div>
              )}
            </div>
          )}

          {/* 3. Edge Cases Live Output Surface */}
          {activeRunType === 'edge' && edgeRunState.status !== 'IDLE' && (
            <div className="bg-[#FFFDF8] border border-[#D8D0C1] rounded-2xl p-6 shadow-xs space-y-5 animate-reveal">
              <div className="flex items-center justify-between border-b border-[#D8D0C1] pb-4">
                <div>
                  <span className="text-[10px] font-mono font-bold text-[#112A4E] tracking-wider uppercase">CURRENT LIVE RUN OUTPUT &middot; DIRECTED EDGE CASES</span>
                  <h3 className="text-lg font-serif-hero font-bold text-[#10213A] mt-0.5">
                    {getStatusCopy(edgeRunState.status, edgeRunState.error)}
                  </h3>
                </div>
                <StatusBadge
                  status={edgeRunState.status}
                  type={edgeRunState.status === 'PASS' ? 'emerald' : edgeRunState.status === 'FAIL' ? 'red' : edgeRunState.status === 'RUNNING' ? 'cyan' : 'amber'}
                />
              </div>

              {edgeRunState.data && (
                <>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
                    <div className="bg-[#FCF9F2] p-4 rounded-xl border border-[#D8D0C1]">
                      <div className="text-2xl font-bold text-[#10213A]">{edgeRunState.data.cases}</div>
                      <div className="text-[10px] text-[#5B6370] uppercase font-semibold mt-0.5">Cases Run</div>
                    </div>
                    <div className="bg-[#EAF2EC] p-4 rounded-xl border border-[#C3DCC8] text-[#356044]">
                      <div className="text-2xl font-bold text-[#356044]">{edgeRunState.data.passed}</div>
                      <div className="text-[10px] text-[#356044] uppercase font-bold mt-0.5">Passed</div>
                    </div>
                    <div className="bg-[#FCF9F2] p-4 rounded-xl border border-[#D8D0C1]">
                      <div className="text-2xl font-bold text-[#10213A]">{edgeRunState.data.failed}</div>
                      <div className="text-[10px] text-[#5B6370] uppercase font-semibold mt-0.5">Failed</div>
                    </div>
                    <div className="bg-[#F1EADF] p-4 rounded-xl border border-[#D8D0C1] text-[#10213A]">
                      <div className="text-2xl font-bold text-[#112A4E]">{edgeRunState.data.verified_events.toLocaleString()}</div>
                      <div className="text-[10px] text-[#112A4E] uppercase font-bold mt-0.5">Events Verified</div>
                    </div>
                  </div>

                  {/* Results List Table with clean metric formatting */}
                  {edgeRunState.data.results && edgeRunState.data.results.length > 0 && (
                    <div className="overflow-x-auto border border-[#D8D0C1] rounded-xl bg-[#FFFDF8]">
                      <table className="w-full text-left text-xs font-mono">
                        <thead className="bg-[#F1EADF] text-[10px] uppercase text-[#5B6370] border-b border-[#D8D0C1]">
                          <tr>
                            <th className="py-2.5 px-3">Test Case</th>
                            <th className="py-2.5 px-3">Component</th>
                            <th className="py-2.5 px-3">Workload / Pattern</th>
                            <th className="py-2.5 px-3 text-right">Metric</th>
                            <th className="py-2.5 px-3 text-center">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#D8D0C1]/60">
                          {edgeRunState.data.results.map((res: any, idx: number) => (
                            <tr key={idx} className="hover:bg-[#FCF9F2] transition-colors">
                              <td className="py-2.5 px-3 font-semibold text-[#10213A]">{res.case_name || res.test_case}</td>
                              <td className="py-2.5 px-3 text-[#5B6370]">{res.component}</td>
                              <td className="py-2.5 px-3 text-[#5B6370]">{res.workload || res.test_case}</td>
                              <td className="py-2.5 px-3 text-right font-bold text-[#10213A]">{formatMetricValue(res.metric_value)}</td>
                              <td className="py-2.5 px-3 text-center">
                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${res.status === 'PASS' ? 'bg-[#EAF2EC] text-[#356044] border border-[#C3DCC8]' : 'bg-[#FDF2F2] text-[#9A4744] border border-[#E8C5C5]'}`}>
                                  {res.status}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              )}

              {edgeRunState.error && (
                <div className="p-4 bg-[#FDF8EE] border border-[#F3E3C3] rounded-xl text-xs text-[#B58B4A] font-mono">
                  {edgeRunState.error}
                </div>
              )}
            </div>
          )}

          {/* Separated Historical Verification Records */}
          <div className="space-y-4 pt-2">
            <h3 className="text-xs font-bold text-[#5B6370] uppercase tracking-wider font-mono">
              HISTORICAL VERIFIED RESULTS
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {VERIFICATION_CAMPAIGNS.map((campaign) => (
                <VerificationCard key={campaign.id} campaign={campaign} />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ========================================================================= */}
      {/* PERFORMANCE MODEL PAGE */}
      {/* ========================================================================= */}
      {activeSection === 'performance' && (
        <section id="performance" className="space-y-6 animate-reveal">
          <SectionHeader
            title="WHAT DOES THIS MICROARCHITECTURE COST?"
            subtitle="Analytical Performance Estimate · Estimated CPI stall penalty model."
            tag="PERFORMANCE MODEL"
          />

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            {/* Left: Model Assumptions */}
            <div className="lg:col-span-5 bg-[#FFFDF8] border border-[#D8D0C1] rounded-2xl p-6 shadow-xs space-y-4">
              <h3 className="text-xs font-bold text-[#5B6370] uppercase tracking-wider font-mono">ASSUMPTIONS</h3>
              
              <div className="space-y-4 font-mono text-xs">
                <div>
                  <label className="block text-[#10213A] font-semibold mb-1">Instruction Count</label>
                  <input
                    type="number"
                    value={perfInstructions}
                    onChange={(e) => setPerfInstructions(Number(e.target.value))}
                    className="w-full bg-[#FCF9F2] border border-[#D8D0C1] rounded-xl p-3 text-[#10213A] focus:outline-none focus:ring-2 focus:ring-[#B58B4A]"
                  />
                </div>
                <div>
                  <label className="block text-[#10213A] font-semibold mb-1">Base CPI (Ideal)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={perfBaseCpi}
                    onChange={(e) => setPerfBaseCpi(Number(e.target.value))}
                    className="w-full bg-[#FCF9F2] border border-[#D8D0C1] rounded-xl p-3 text-[#10213A] focus:outline-none focus:ring-2 focus:ring-[#B58B4A]"
                  />
                </div>
                <div>
                  <label className="block text-[#10213A] font-semibold mb-1">Branch Misprediction Penalty (Cycles)</label>
                  <input
                    type="number"
                    value={perfBranchPenalty}
                    onChange={(e) => setPerfBranchPenalty(Number(e.target.value))}
                    className="w-full bg-[#FCF9F2] border border-[#D8D0C1] rounded-xl p-3 text-[#10213A] focus:outline-none focus:ring-2 focus:ring-[#B58B4A]"
                  />
                </div>
                <div>
                  <label className="block text-[#10213A] font-semibold mb-1">Cache Miss Penalty (Cycles)</label>
                  <input
                    type="number"
                    value={perfCachePenalty}
                    onChange={(e) => setPerfCachePenalty(Number(e.target.value))}
                    className="w-full bg-[#FCF9F2] border border-[#D8D0C1] rounded-xl p-3 text-[#10213A] focus:outline-none focus:ring-2 focus:ring-[#B58B4A]"
                  />
                </div>
              </div>
            </div>

            {/* Right: Calculation Visualization & HERO ESTIMATED CPI */}
            <div className="lg:col-span-7 bg-[#FFFDF8] border border-[#D8D0C1] rounded-2xl p-6 shadow-xs space-y-6">
              <div className="flex items-center justify-between border-b border-[#D8D0C1] pb-3">
                <h3 className="text-xs font-bold text-[#5B6370] uppercase tracking-wider font-mono">Analytical Performance Estimate</h3>
                <span className="text-xs font-mono font-bold text-[#112A4E] bg-[#F1EADF] px-3 py-1 rounded-lg border border-[#D8D0C1]">
                  Analytical Model
                </span>
              </div>

              {/* CALCULATION VISUALIZATION */}
              <div className="p-5 bg-[#FCF9F2] rounded-xl border border-[#D8D0C1] font-mono text-xs space-y-2">
                <div className="flex justify-between text-[#5B6370]">
                  <span>Base Instruction Cycles ({perfInstructions.toLocaleString()} &times; {perfBaseCpi}):</span>
                  <span className="font-bold text-[#10213A]">{baseCycles.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-[#5B6370]">
                  <span>+ Branch Penalty ({branchMispredictions} &times; {perfBranchPenalty} cycles):</span>
                  <span className="font-bold text-[#B58B4A]">+{extraBranchCycles}</span>
                </div>
                <div className="flex justify-between text-[#5B6370]">
                  <span>+ Cache Penalty ({cacheMisses} &times; {perfCachePenalty} cycles):</span>
                  <span className="font-bold text-[#B58B4A]">+{extraCacheCycles}</span>
                </div>
                <div className="border-t border-[#D8D0C1] pt-2 flex justify-between font-bold text-sm text-[#10213A]">
                  <span>Estimated Total Cycles:</span>
                  <span className="text-[#112A4E]">{estimatedTotalCycles.toLocaleString()}</span>
                </div>
              </div>

              {/* ESTIMATED CPI HERO RESULT */}
              <div className="p-6 bg-[#F1EADF] rounded-xl border border-[#D8D0C1] text-center font-mono space-y-1">
                <div className="text-xs text-[#B58B4A] font-bold uppercase tracking-wider">TOTAL ESTIMATED CPI HERO RESULT</div>
                <div className="text-4xl font-extrabold text-[#112A4E]">{estimatedCpi.toFixed(4)}</div>
                <div className="text-xs text-[#5B6370]">Cycles Per Instruction (Analytical Estimate)</div>
              </div>
            </div>

          </div>

          {/* Minimal Comparison Visualizations Below */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
            <div className="bg-[#FFFDF8] border border-[#D8D0C1] rounded-2xl p-5 shadow-xs">
              <h4 className="text-xs font-bold text-[#10213A] mb-4 font-mono">Predictor Workload Accuracy Comparison</h4>
              <BranchChart />
            </div>
            <div className="bg-[#FFFDF8] border border-[#D8D0C1] rounded-2xl p-5 shadow-xs">
              <h4 className="text-xs font-bold text-[#10213A] mb-4 font-mono">Cache Workload Hit Rate Comparison</h4>
              <CacheChart />
            </div>
          </div>
        </section>
      )}

      {/* ========================================================================= */}
      {/* ARCHITECTURE SYSTEM MAP PAGE */}
      {/* ========================================================================= */}
      {activeSection === 'architecture' && (
        <section id="architecture" className="space-y-6 animate-reveal">
          <SectionHeader
            title="System Architecture &amp; Map"
            subtitle="Visual node pipeline map of frontend, API, simulator, hardware DUT, and reference model layers."
            tag="SYSTEM MAP"
          />

          {/* Visually Compelling System Map Diagram */}
          <div className="bg-[#FFFDF8] border border-[#D8D0C1] rounded-2xl p-6 sm:p-8 shadow-xs space-y-6">
            <h3 className="text-xs font-bold text-[#5B6370] uppercase tracking-wider font-mono">
              Interactive Layer Pipeline Map
            </h3>

            <div className="space-y-3 font-mono text-xs">
              {[
                { layer: 'UI Layer', node: 'React Frontend', icon: Sparkles, desc: 'Captures workload trace strings & launches interactive verification runs', bg: 'bg-[#F1EADF] border-[#D8D0C1] text-[#112A4E]' },
                { layer: 'API Layer', node: 'FastAPI Backend', icon: Server, desc: 'REST endpoints (/api/branch/run, /api/cache/run, /api/regression)', bg: 'bg-[#FCF9F2] border-[#D8D0C1] text-[#10213A]' },
                { layer: 'Controller', node: 'verification_engine.py', icon: Code, desc: 'Normalizes input traces & orchestrates temp workload files', bg: 'bg-[#FCF9F2] border-[#D8D0C1] text-[#10213A]' },
                { layer: 'Simulator', node: 'Icarus Verilog / vvp', icon: Terminal, desc: 'Compiles RTL files & runs simulation with +WORKLOAD plusargs', bg: 'bg-[#FCF9F2] border-[#D8D0C1] text-[#10213A]' },
                { layer: 'Hardware DUT', node: 'SystemVerilog RTL', icon: CpuIcon, desc: 'branch_predictor_1bit.sv, branch_predictor_2bit.sv, direct_mapped_cache.sv', bg: 'bg-[#FCF9F2] border-[#D8D0C1] text-[#10213A]' },
                { layer: 'Log Stream', node: 'REG_* Event Stream', icon: FileCode, desc: 'Machine-readable stdout event traces emitted by Verilog testbenches', bg: 'bg-[#FCF9F2] border-[#D8D0C1] text-[#10213A]' },
                { layer: 'Golden Model', node: 'Python Reference Models', icon: RefreshCw, desc: 'Bit-accurate Python golden reference models (reference_models.py)', bg: 'bg-[#FCF9F2] border-[#D8D0C1] text-[#10213A]' },
                { layer: 'Verification', node: 'Equivalence Check', icon: CheckSquare, desc: 'Transaction-by-transaction comparison returning PASS / FAIL JSON payload', bg: 'bg-[#EAF2EC] border-[#C3DCC8] text-[#356044] font-bold' },
              ].map((item, idx) => {
                const NodeIcon = item.icon;
                return (
                  <div key={idx} className={`p-4 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 ${item.bg}`}>
                    <div className="flex items-center gap-3">
                      <NodeIcon className="w-4 h-4 flex-shrink-0 text-[#B58B4A]" />
                      <div>
                        <span className="text-[10px] uppercase font-bold text-[#5B6370]">{item.layer}</span>
                        <div className="text-sm font-bold">{item.node}</div>
                      </div>
                    </div>
                    <div className="text-xs text-[#5B6370] text-left sm:text-right font-sans max-w-md">
                      {item.desc}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Two Concise Technical Columns */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-[#FFFDF8] border border-[#D8D0C1] rounded-2xl p-6 shadow-xs space-y-3">
              <div className="flex items-center gap-2 text-[#10213A] font-bold font-mono text-sm border-b border-[#D8D0C1] pb-3">
                <Cpu className="w-4 h-4 text-[#B58B4A]" />
                <span>RTL MODULES</span>
              </div>
              <ul className="text-xs text-[#5B6370] space-y-2 leading-relaxed font-sans">
                <li><strong className="text-[#10213A] font-mono">rtl/branch_predictor_1bit.sv</strong> &mdash; 1-bit dynamic predictor storing previous branch outcome.</li>
                <li><strong className="text-[#10213A] font-mono">rtl/branch_predictor_2bit.sv</strong> &mdash; 2-bit saturating counter state machine (Strongly/Weakly Taken &amp; Not Taken).</li>
                <li><strong className="text-[#10213A] font-mono">rtl/direct_mapped_cache.sv</strong> &mdash; Direct-mapped cache (4 lines, 4B blocks, 16-bit address space).</li>
              </ul>
            </div>

            <div className="bg-[#FFFDF8] border border-[#D8D0C1] rounded-2xl p-6 shadow-xs space-y-3">
              <div className="flex items-center gap-2 text-[#10213A] font-bold font-mono text-sm border-b border-[#D8D0C1] pb-3">
                <Code className="w-4 h-4 text-[#B58B4A]" />
                <span>PYTHON INFRASTRUCTURE</span>
              </div>
              <ul className="text-xs text-[#5B6370] space-y-2 leading-relaxed font-sans">
                <li><strong className="text-[#10213A] font-mono">scripts/reference_models.py</strong> &mdash; Bit-accurate Python golden reference models.</li>
                <li><strong className="text-[#10213A] font-mono">scripts/verification_engine.py</strong> &mdash; Programmatic execution engine for custom trace verification.</li>
                <li><strong className="text-[#10213A] font-mono">scripts/regression.py</strong> &mdash; Full 14-case regression suite runner with event log parsing.</li>
              </ul>
            </div>
          </div>
        </section>
      )}

    </PageShell>
  );
}

export default App;
