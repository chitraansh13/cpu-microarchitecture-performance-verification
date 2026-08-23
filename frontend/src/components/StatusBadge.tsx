import React from 'react';

interface StatusBadgeProps {
  status: string;
  type?: 'emerald' | 'cyan' | 'slate' | 'amber' | 'red';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, type = 'emerald' }) => {
  const colorMap = {
    emerald: 'bg-[#EAF2EC] text-[#315C3B] border-[#C3DCC8]',
    cyan: 'bg-[#EEF2F6] text-[#13294B] border-[#D4DDE8]',
    slate: 'bg-[#F2ECE0] text-[#5E6470] border-[#E0D5C3]',
    amber: 'bg-[#FDF8EE] text-[#B77A2B] border-[#F3E3C3]',
    red: 'bg-[#FDF2F2] text-[#9F3A38] border-[#E8C5C5]',
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-[11px] font-mono font-medium border ${colorMap[type]}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current mr-1.5 opacity-80" />
      {status}
    </span>
  );
};
