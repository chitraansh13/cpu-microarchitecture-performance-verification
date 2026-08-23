import React, { useState } from 'react';
import { Play, FileText, Activity, Sparkles } from 'lucide-react';

interface QuickComposerProps {
  value: string;
  onChange: (val: string) => void;
  onRunAnalysis: (cmd: string) => void;
  onPreset: (presetType: 'trace' | 'cache' | 'example') => void;
}

export const QuickComposer: React.FC<QuickComposerProps> = ({
  value,
  onChange,
  onRunAnalysis,
  onPreset,
}) => {
  const [isFocused, setIsFocused] = useState(false);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      onRunAnalysis(value);
    }
  };

  return (
    <div className={`bg-[#FFFDF8] border rounded-2xl p-4 shadow-sm transition-all ${
      isFocused ? 'border-[#B58B4A] ring-2 ring-[#B58B4A]/20' : 'border-[#D8D0C1]'
    }`}>
      {/* Editable Interactive Text Input Area */}
      <div className="flex items-center gap-3 bg-[#FCF9F2] border border-[#D8D0C1] rounded-xl px-4 py-3 text-xs font-mono">
        <span className="text-[#B58B4A] font-bold text-sm select-none">&gt;</span>
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          onKeyDown={handleKeyDown}
          placeholder="Enter a branch trace (e.g., T T T N), memory addresses (0x0000 0x0004), or pick a workload..."
          aria-label="Interactive Analysis Command Bar"
          className="bg-transparent border-none outline-none w-full text-[#10213A] placeholder-[#8A909A] font-mono text-xs font-medium"
        />
        {value && (
          <button
            onClick={() => onChange('')}
            className="text-[10px] text-[#5B6370] hover:text-[#10213A] px-1.5 py-0.5 rounded bg-[#F1EADF]"
            title="Clear text"
          >
            Clear
          </button>
        )}
      </div>

      {/* Control Buttons Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 mt-3 pt-2">
        {/* Left Quick Presets */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => onPreset('trace')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#F1EADF] hover:bg-[#E7DFC4] text-[#10213A] text-xs font-medium border border-[#D8D0C1] transition-colors"
          >
            <FileText className="w-3.5 h-3.5 text-[#B58B4A]" />
            <span>Load Trace</span>
          </button>

          <button
            type="button"
            onClick={() => onPreset('cache')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#F1EADF] hover:bg-[#E7DFC4] text-[#10213A] text-xs font-medium border border-[#D8D0C1] transition-colors"
          >
            <Activity className="w-3.5 h-3.5 text-[#B58B4A]" />
            <span>Choose Workload</span>
          </button>

          <button
            type="button"
            onClick={() => onPreset('example')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#F1EADF] hover:bg-[#E7DFC4] text-[#10213A] text-xs font-medium border border-[#D8D0C1] transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5 text-[#B58B4A]" />
            <span>Quick Examples</span>
          </button>
        </div>

        {/* Right Run Action */}
        <button
          type="button"
          onClick={() => onRunAnalysis(value)}
          className="inline-flex items-center justify-center gap-2 px-5 py-2 rounded-xl bg-[#112A4E] hover:bg-[#0A1A32] active:bg-[#071325] text-[#FFFDF8] text-xs font-bold shadow-xs transition-colors tracking-wide"
        >
          <Play className="w-3.5 h-3.5 fill-current text-[#B58B4A]" />
          <span>Run Analysis</span>
        </button>
      </div>
    </div>
  );
};
