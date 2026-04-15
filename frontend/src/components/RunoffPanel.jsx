import React, { useState, useEffect, useRef } from 'react';

const DEVICE_NAMES = {
  '16132920': '杧果林1监测点',
  '16132921': '橡胶林1监测点',
  '16132922': '次生林监测点',
  '16132923': '杧果林2监测点',
  '16132924': '橡胶林2监测点',
  '16132925': '槟榔林监测点',
};

const ALL_CODES = ['16132920', '16132921', '16132922', '16132923', '16132924', '16132925'];

export default function RunoffPanel({ runoffStations }) {
  const [activeCode, setActiveCode] = useState(ALL_CODES[0]);
  const [isAutoPlay, setIsAutoPlay] = useState(true);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!isAutoPlay) return;

    timerRef.current = setInterval(() => {
      setActiveCode(current => {
        const idx = ALL_CODES.indexOf(current);
        const nextIdx = (idx + 1) % ALL_CODES.length;
        return ALL_CODES[nextIdx];
      });
    }, 5000); // 5 seconds per station

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    }
  }, [isAutoPlay]);

  const handleManualSelect = (code) => {
    setActiveCode(code);
    setIsAutoPlay(false); // Stop auto-play on manual click
    
    // Resume auto-play after 30 seconds of inactivity
    if (timerRef.current) clearInterval(timerRef.current);
    setTimeout(() => setIsAutoPlay(true), 30000);
  };

  const data = runoffStations?.[activeCode] || null;

  const fmt = (v) => {
    if (v == null) return '—';
    const n = Number(v);
    return isNaN(n) ? '—' : n.toFixed(2);
  };

  const metrics = [
    { label: '当前流速',   key: 'flow_speed',      unit: 'm/s',   color: '#4ade80' },
    { label: '瞬时流量',   key: 'flow_rate',        unit: 'm³/s',  color: '#38bdf8' },
    { label: '累计流量',   key: 'total_flow',       unit: 'm³',    color: '#38bdf8' },
    { label: '水位',       key: 'water_level',      unit: 'm',     color: '#facc15' },
    { label: '含沙量',     key: 'sand_content',     unit: 'kg/L',  color: '#fb923c' },
    { label: '液位压力',   key: 'liquid_pressure',  unit: 'kPa',   color: '#c084fc' },
    { label: '径流量',     key: 'runoff',           unit: 'm³',    color: '#4ade80' },
    { label: '降雨量',     key: 'rainfall',         unit: 'mm',    color: '#60a5fa' },
  ];

  return (
    <div 
      style={{ display: 'flex', flexDirection: 'column', gap: '6px', height: '100%', padding: '4px 0' }}
      onMouseEnter={() => setIsAutoPlay(false)}
      onMouseLeave={() => setIsAutoPlay(true)}
    >

      {/* Station Selector Tabs */}
      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
        {ALL_CODES.map(code => (
          <div
            key={code}
            onClick={() => handleManualSelect(code)}
            style={{
              padding: '2px 8px',
              fontSize: '10px',
              borderRadius: '4px',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              background: activeCode === code ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255,255,255,0.05)',
              border: activeCode === code ? '1px solid #38bdf8' : '1px solid rgba(255,255,255,0.1)',
              color: activeCode === code ? '#38bdf8' : '#888',
              transition: 'all 0.2s',
              position: 'relative',
              overflow: 'hidden'
            }}
          >
            {DEVICE_NAMES[code] || code}
            {activeCode === code && isAutoPlay && (
               <div style={{
                 position: 'absolute', bottom: 0, left: 0, height: '2px', background: '#38bdf8',
                 animation: 'runoffProgress 5s linear forwards'
               }} />
            )}
          </div>
        ))}
      </div>

      <style>{`
        @keyframes runoffProgress {
          from { width: 0% }
          to { width: 100% }
        }
      `}</style>

      {/* Grid */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gridTemplateRows: 'repeat(2, 1fr)', gap: '5px', minHeight: 0 }}>
        {metrics.map(m => {
          const val = data ? data[m.key] : null;
          const hasData = val != null;
          return (
            <div key={m.label} style={{
              background: 'rgba(255,255,255,0.05)',
              padding: '6px 4px',
              borderRadius: '6px',
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              borderLeft: `2px solid ${hasData ? m.color : 'rgba(255,255,255,0.1)'}`,
            }}>
              <div style={{ fontSize: '9px', color: '#888', marginBottom: '3px' }}>{m.label}</div>
              <div style={{ fontSize: '13px', color: hasData ? m.color : '#444', fontWeight: 'bold', lineHeight: 1.2 }}>
                {fmt(val)}
                {hasData && <span style={{ fontSize: '8px', color: '#666', marginLeft: '2px', fontWeight: 'normal' }}>{m.unit}</span>}
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div style={{ fontSize: '9px', color: '#444', display: 'flex', justifyContent: 'space-between', flexShrink: 0 }}>
        <span>{DEVICE_NAMES[activeCode] || activeCode}  ·  {activeCode}</span>
        <span style={{ color: data?.status === 'online' ? '#4ade80' : '#475569' }}>
          {data?.status === 'online' ? '● 实时' : (data ? '● 离线' : '● 无数据')}  
          <span style={{ marginLeft: 4 }}>
            {data?.updated_at ? data.updated_at.replace('T', ' ').slice(11, 16) : '--:--'}
          </span>
        </span>
      </div>
    </div>
  );
}
