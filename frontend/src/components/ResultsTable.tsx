import React from 'react';
import { VERIFIED_BRANCH_RESULTS, VERIFIED_CACHE_RESULTS } from '../data/verifiedResults';

export const BranchResultsTable: React.FC = () => {
  return (
    <div className="overflow-x-auto border border-[#E5DED1] rounded-xl bg-[#FFFDF8]">
      <table className="w-full text-left text-xs font-sans">
        <thead className="bg-[#F4EFE6] text-[10px] font-mono uppercase text-[#5E6470] border-b border-[#E5DED1]">
          <tr>
            <th className="py-2.5 px-3">Workload Pattern</th>
            <th className="py-2.5 px-3 text-right">1-Bit Accuracy</th>
            <th className="py-2.5 px-3 text-right">2-Bit Accuracy</th>
            <th className="py-2.5 px-3 text-right">Δ (2-bit vs 1-bit)</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#E5DED1]/60">
          {VERIFIED_BRANCH_RESULTS.map((row) => {
            const delta = row.twoBit - row.oneBit;
            return (
              <tr key={row.workload} className="hover:bg-[#FAF7F0] transition-colors">
                <td className="py-2.5 px-3 font-medium text-[#0F1B33]">{row.workload}</td>
                <td className="py-2.5 px-3 text-right font-mono text-[#5E6470]">{row.oneBit.toFixed(2)}%</td>
                <td className="py-2.5 px-3 text-right font-mono text-[#13294B] font-bold">{row.twoBit.toFixed(2)}%</td>
                <td className={`py-2.5 px-3 text-right font-mono text-[11px] font-bold ${delta >= 0 ? 'text-[#315C3B]' : 'text-[#5E6470]'}`}>
                  {delta >= 0 ? `+${delta.toFixed(2)} pp` : `${delta.toFixed(2)} pp`}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export const CacheResultsTable: React.FC = () => {
  return (
    <div className="overflow-x-auto border border-[#E5DED1] rounded-xl bg-[#FFFDF8]">
      <table className="w-full text-left text-xs font-sans">
        <thead className="bg-[#F4EFE6] text-[10px] font-mono uppercase text-[#5E6470] border-b border-[#E5DED1]">
          <tr>
            <th className="py-2.5 px-3">Memory Pattern</th>
            <th className="py-2.5 px-3 text-right">Hits</th>
            <th className="py-2.5 px-3 text-right">Misses</th>
            <th className="py-2.5 px-3 text-right">Hit Rate</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#E5DED1]/60">
          {VERIFIED_CACHE_RESULTS.map((row) => (
            <tr key={row.workload} className="hover:bg-[#FAF7F0] transition-colors">
              <td className="py-2.5 px-3 font-medium text-[#0F1B33]">{row.workload}</td>
              <td className="py-2.5 px-3 text-right font-mono text-[#0F1B33]">{row.hits}</td>
              <td className="py-2.5 px-3 text-right font-mono text-[#5E6470]">{row.misses}</td>
              <td className="py-2.5 px-3 text-right font-mono text-[#13294B] font-bold">{row.hitRate.toFixed(2)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
