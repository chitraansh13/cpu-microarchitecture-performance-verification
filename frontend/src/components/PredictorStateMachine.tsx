import React from 'react';

interface PredictorStateMachineProps {
  currentTrace?: number[];
}

export const PredictorStateMachine: React.FC<PredictorStateMachineProps> = ({ currentTrace }) => {
  let state = 2; // Default starting state: Weakly Taken (10 = 2)
  if (currentTrace && currentTrace.length > 0) {
    for (const outcome of currentTrace) {
      if (outcome === 1) {
        state = Math.min(3, state + 1);
      } else {
        state = Math.max(0, state - 1);
      }
    }
  }

  const states = [
    { code: 0, bin: '00', name: 'Strongly NT', predict: 'N' },
    { code: 1, bin: '01', name: 'Weakly NT', predict: 'N' },
    { code: 2, bin: '10', name: 'Weakly T', predict: 'T' },
    { code: 3, bin: '11', name: 'Strongly T', predict: 'T' },
  ];

  return (
    <div className="bg-[#FFFDF8] border border-[#E5DED1] rounded-xl p-4 shadow-xs space-y-3 font-mono text-xs">
      <div className="flex items-center justify-between border-b border-[#E5DED1] pb-2">
        <span className="text-[10px] uppercase font-bold text-[#5E6470] tracking-wider">2-Bit Counter State Machine</span>
        <span className="text-[10px] text-[#13294B] bg-[#FAF5EA] px-2 py-0.5 rounded border border-[#EADFCA] font-semibold">
          Final State: {states[state].name} ({states[state].bin})
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {states.map((s) => {
          const isActive = s.code === state;
          return (
            <div
              key={s.code}
              className={`p-2.5 rounded-lg border text-center transition-all ${
                isActive
                  ? 'bg-[#FAF5EA] border-[#B8924A] text-[#0F1B33] font-bold shadow-xs'
                  : 'bg-[#F8F5EE] border-[#E5DED1] text-[#5E6470]'
              }`}
            >
              <div className="text-[10px] text-[#8C8273] font-semibold">{s.bin}</div>
              <div className="text-xs mt-0.5">{s.name}</div>
              <div className={`text-[10px] mt-1 font-bold ${s.predict === 'T' ? 'text-[#315C3B]' : 'text-[#5E6470]'}`}>
                Pred: {s.predict}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
