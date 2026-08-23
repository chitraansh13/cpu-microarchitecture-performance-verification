import React from 'react';
import { Cpu, Activity, Database, ShieldCheck, Zap, Layers, Terminal } from 'lucide-react';

interface PageShellProps {
  children: React.ReactNode;
  activeSection: string;
  setActiveSection: (section: string) => void;
  isEngineOnline?: boolean | null;
}

export const PageShell: React.FC<PageShellProps> = ({
  children,
  activeSection,
  setActiveSection,
  isEngineOnline = null,
}) => {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: Cpu, badge: 'Home' },
    { id: 'branch', label: 'Branch Predictor', icon: Activity, badge: 'Lab' },
    { id: 'cache', label: 'Cache', icon: Database, badge: 'Lab' },
    { id: 'regression', label: 'Regression', icon: ShieldCheck, badge: 'Suite' },
    { id: 'performance', label: 'Performance', icon: Zap, badge: 'Model' },
    { id: 'architecture', label: 'Architecture', icon: Layers, badge: 'Map' },
  ];

  return (
    <div className="min-h-screen bg-[#F6F2EA] text-[#10213A] flex flex-col md:flex-row font-sans">
      {/* Warm Light Chrome Sidebar */}
      <aside className="w-full md:w-64 bg-[#F1EADF] border-b md:border-b-0 md:border-r border-[#D8D0C1] flex-shrink-0 p-5 flex flex-col justify-between text-[#10213A]">
        <div>
          {/* Brand Product Header */}
          <div className="flex items-center gap-3 mb-8 px-1 pt-1">
            <div className="w-9 h-9 rounded-xl bg-[#112A4E] flex items-center justify-center text-[#FFFDF8] font-mono font-bold text-xs shadow-xs border border-[#B58B4A]/50">
              RTL
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <h1 className="text-sm font-serif-hero font-bold text-[#10213A] tracking-tight">CPU LAB</h1>
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-[#FFFDF8] text-[#B58B4A] border border-[#D8D0C1] font-bold">v1.0</span>
              </div>
              <p className="text-[10px] text-[#5B6370] font-mono mt-0.5">Microarchitecture Verification</p>
            </div>
          </div>

          {/* Navigation Items */}
          <div className="text-[10px] font-mono uppercase tracking-wider text-[#5B6370] font-semibold px-2 mb-3">
            Navigation Workspace
          </div>
          <nav className="space-y-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeSection === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveSection(item.id)}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all text-left ${
                    isActive
                      ? 'bg-[#FFFDF8] text-[#112A4E] border border-[#B58B4A]/70 shadow-xs font-bold'
                      : 'text-[#5B6370] hover:text-[#10213A] hover:bg-[#E8DFD0] border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`w-4 h-4 transition-colors ${isActive ? 'text-[#B58B4A]' : 'text-[#7D8592]'}`} />
                    <span>{item.label}</span>
                  </div>
                  <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${
                    isActive ? 'bg-[#112A4E] text-[#FFFDF8]' : 'text-[#7D8592]'
                  }`}>
                    {item.badge}
                  </span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Sidebar Footer RTL Engine Status */}
        <div className="mt-8 pt-4 border-t border-[#D8D0C1] font-mono text-[11px]">
          <div className="p-3 rounded-xl bg-[#FFFDF8] border border-[#D8D0C1]">
            <div className="flex items-center justify-between">
              <span className="text-[#5B6370] text-[10px] uppercase font-semibold">RTL Engine</span>
              <Terminal className="w-3.5 h-3.5 text-[#7D8592]" />
            </div>
            {isEngineOnline === true ? (
              <div className="flex items-center gap-2 mt-1.5 text-[#356044] font-bold text-xs">
                <span className="w-2 h-2 rounded-full bg-[#356044] animate-pulse"></span>
                <span>ONLINE</span>
              </div>
            ) : isEngineOnline === false ? (
              <div className="flex items-center gap-2 mt-1.5 text-[#B58B4A] font-bold text-xs">
                <span className="w-2 h-2 rounded-full bg-[#B58B4A]"></span>
                <span>OFFLINE</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 mt-1.5 text-[#5B6370] font-bold text-xs">
                <span className="w-2 h-2 rounded-full bg-[#7D8592]"></span>
                <span>CHECKING...</span>
              </div>
            )}
            <div className="text-[#5B6370] mt-1 text-[10px]">Icarus Verilog + Python</div>
          </div>
        </div>
      </aside>

      {/* Main Workspace Container */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#F6F2EA]">
        {/* Workspace Top Header */}
        <header className="bg-[#FFFDF8] border-b border-[#D8D0C1] px-6 py-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-2xs">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#112A4E]"></span>
              <h1 className="text-base font-serif-hero font-bold text-[#10213A] tracking-tight">
                CPU Microarchitecture Verification Workspace
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#F1EADF] border border-[#D8D0C1] text-xs font-mono text-[#5B6370]">
              <span>DUT:</span>
              <strong className="text-[#10213A] font-semibold">1bit &middot; 2bit &middot; DirectCache</strong>
            </div>
            <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium border ${
              isEngineOnline === true
                ? 'bg-[#EAF2EC] text-[#356044] border-[#C3DCC8]'
                : 'bg-[#FDF8EE] text-[#B58B4A] border-[#F3E3C3]'
            }`}>
              <span className={`w-2 h-2 rounded-full ${isEngineOnline === true ? 'bg-[#356044]' : 'bg-[#B58B4A]'}`} />
              {isEngineOnline === true ? 'RTL ONLINE' : 'RTL OFFLINE'}
            </span>
          </div>
        </header>

        {/* Main Content Workspace */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8 max-w-6xl w-full mx-auto animate-reveal space-y-6">
          {children}
        </main>
      </div>
    </div>
  );
};
