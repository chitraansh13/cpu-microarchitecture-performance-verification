import React from 'react';
import { VerificationCampaign } from '../data/verifiedResults';
import { StatusBadge } from './StatusBadge';
import { ShieldAlert, ShieldCheck } from 'lucide-react';

interface VerificationCardProps {
  campaign: VerificationCampaign;
}

export const VerificationCard: React.FC<VerificationCardProps> = ({ campaign }) => {
  const isFault = campaign.isFaultInjection;

  return (
    <div className={`border rounded-xl p-5 flex flex-col justify-between transition-all ${
      isFault
        ? 'border-[#F3E3C3] bg-[#FDF8EE] text-[#0F1B33]'
        : 'border-[#E5DED1] bg-[#FFFDF8] text-[#0F1B33] hover:border-[#D5CBB9]'
    }`}>
      <div>
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-2">
            {isFault ? (
              <ShieldAlert className="w-4 h-4 text-[#B77A2B] flex-shrink-0" />
            ) : (
              <ShieldCheck className="w-4 h-4 text-[#13294B] flex-shrink-0" />
            )}
            <h3 className="text-sm font-serif-title font-bold text-[#0F1B33]">{campaign.title}</h3>
          </div>
          <StatusBadge status={campaign.status} type={campaign.badgeType} />
        </div>
        <p className="text-xs text-[#5E6470] leading-relaxed mb-4 font-sans">{campaign.description}</p>
      </div>

      <div className="grid grid-cols-2 gap-2 pt-3 border-t border-[#E5DED1]/70 font-mono text-[11px]">
        {campaign.metrics.map((m) => (
          <div
            key={m.label}
            className={`p-2 rounded-lg border ${
              isFault
                ? 'bg-[#F9EED9] border-[#EBD6B0]'
                : 'bg-[#F8F5EE] border-[#E5DED1]'
            }`}
          >
            <div className="text-[9px] text-[#5E6470] uppercase tracking-wide font-semibold">{m.label}</div>
            <div className="font-bold text-[#0F1B33] mt-0.5">{m.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
};
