import React from 'react';

interface MetricCardProps {
  label: string;
  value: string;
  subtext: string;
  status?: 'pass' | 'complete' | 'detected' | 'info' | 'emphasis';
  size?: 'lg' | 'md';
}

export const MetricCard: React.FC<MetricCardProps> = ({ label, value, subtext, status = 'info', size = 'md' }) => {
  const accentStyle = {
    emphasis: 'border-l-blue-600 bg-blue-50/30',
    pass: 'border-l-emerald-600 bg-emerald-50/20',
    complete: 'border-l-blue-600 bg-blue-50/20',
    detected: 'border-l-amber-600 bg-amber-50/20',
    info: 'border-l-slate-400 bg-white',
  }[status];

  return (
    <div className={`border border-slate-200 border-l-4 ${accentStyle} rounded-lg ${
      size === 'lg' ? 'p-5' : 'p-4'
    } shadow-xs transition-colors bg-white`}>
      <div className="text-[10px] text-slate-500 uppercase tracking-wider font-mono font-semibold">{label}</div>
      <div className={`${size === 'lg' ? 'text-2xl sm:text-3xl' : 'text-xl'} font-bold text-slate-900 font-mono tracking-tight mt-1`}>
        {value}
      </div>
      <div className="text-[11px] text-slate-500 font-mono mt-1 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
        <span>{subtext}</span>
      </div>
    </div>
  );
};
