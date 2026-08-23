import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { VERIFIED_CACHE_RESULTS } from '../data/verifiedResults';

export const CacheChart: React.FC = () => {
  return (
    <div className="w-full h-56 font-sans text-xs">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={VERIFIED_CACHE_RESULTS} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
          <XAxis dataKey="workload" stroke="#9E8C76" tick={{ fill: '#5E6470', fontSize: 10, fontFamily: 'sans-serif' }} />
          <YAxis stroke="#9E8C76" tick={{ fill: '#5E6470', fontSize: 10, fontFamily: 'monospace' }} unit="%" domain={[0, 100]} />
          <Tooltip 
            contentStyle={{ backgroundColor: '#0F1B33', borderColor: '#B8924A', borderRadius: '6px', color: '#F8F5EE', fontSize: '11px', fontFamily: 'monospace' }}
            formatter={(value: number) => [`${value.toFixed(2)}%`, 'Hit Rate']}
          />
          <Bar dataKey="hitRate" name="Hit Rate" fill="#13294B" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
