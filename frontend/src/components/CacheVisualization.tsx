import React from 'react';
import { CacheEvent } from '../lib/api';

interface CacheVisualizationProps {
  events?: CacheEvent[];
}

export const CacheVisualization: React.FC<CacheVisualizationProps> = ({ events }) => {
  const lines = [
    { index: 0, valid: false, tag: null as number | null, accesses: 0 },
    { index: 1, valid: false, tag: null as number | null, accesses: 0 },
    { index: 2, valid: false, tag: null as number | null, accesses: 0 },
    { index: 3, valid: false, tag: null as number | null, accesses: 0 },
  ];

  if (events && events.length > 0) {
    for (const evt of events) {
      const idx = evt.index % 4;
      lines[idx].valid = true;
      lines[idx].tag = evt.tag;
      lines[idx].accesses += 1;
    }
  }

  return (
    <div className="bg-[#FFFDF8] border border-[#E5DED1] rounded-xl p-5 shadow-xs space-y-4 font-mono text-xs">
      <div className="flex items-center justify-between border-b border-[#E5DED1] pb-3">
        <div>
          <span className="text-[10px] font-bold text-[#5E6470] uppercase tracking-wider">Direct-Mapped Cache Contents (4 Lines)</span>
          <p className="text-[11px] text-[#5E6470] font-sans mt-0.5">Line Index = Address[3:2] &middot; Block Size = 4B &middot; 16-bit Space</p>
        </div>
        <span className="text-xs font-bold text-[#13294B] bg-[#FAF5EA] px-2.5 py-1 rounded border border-[#EADFCA]">
          4 Lines &middot; 4B Blocks
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {lines.map((line) => (
          <div
            key={line.index}
            className={`p-3 rounded-lg border flex flex-col justify-between space-y-2 transition-all ${
              line.valid
                ? 'bg-[#FAF5EA] border-[#B8924A]/60 text-[#0F1B33] shadow-2xs'
                : 'bg-[#F8F5EE] border-[#E5DED1] text-[#8C8273]'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-[#0F1B33]">LINE {line.index}</span>
              <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                line.valid ? 'bg-[#EAF2EC] text-[#315C3B] border border-[#C3DCC8]' : 'bg-[#EFE8DB] text-[#8C8273]'
              }`}>
                {line.valid ? 'VALID' : 'EMPTY'}
              </span>
            </div>

            <div>
              <div className="text-[10px] text-[#5E6470] uppercase">Tag Value</div>
              <div className="font-bold text-[#0F1B33] text-sm">
                {line.valid && line.tag !== null ? `0x${line.tag.toString(16).padStart(3, '0').toUpperCase()}` : '—'}
              </div>
            </div>

            <div className="pt-2 border-t border-[#E5DED1] flex justify-between items-center text-[10px] text-[#5E6470]">
              <span>Hits / Accesses:</span>
              <span className="font-bold text-[#0F1B33]">{line.accesses}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
