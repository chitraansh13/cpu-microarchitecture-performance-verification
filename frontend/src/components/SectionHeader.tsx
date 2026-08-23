import React from 'react';

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  tag?: string;
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({ title, subtitle, tag }) => {
  return (
    <div className="mb-5 pb-3 border-b border-[#E5DED1]">
      <div className="flex items-center gap-2.5">
        {tag && (
          <span className="text-[10px] font-mono text-[#B8924A] font-bold tracking-wider px-2 py-0.5 bg-[#FAF5EA] border border-[#EADFCA] rounded">
            {tag}
          </span>
        )}
        <h2 className="text-xl font-serif-title font-bold text-[#0F1B33] tracking-tight">{title}</h2>
      </div>
      {subtitle && <p className="text-xs text-[#5E6470] mt-1 font-sans leading-relaxed">{subtitle}</p>}
    </div>
  );
};
