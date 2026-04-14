import React, { useState, useEffect } from 'react';

export default function RunoffPanel({ runoffStations }) {
  const [activeCode, setActiveCode] = useState(null);

  // Initialize activeCode to the first available station with data
  useEffect(() => {
    if (runoffStations && Object.keys(runoffStations).length > 0) {
      if (!activeCode || !runoffStations[activeCode]) {
        setActiveCode(Object.keys(runoffStations)[0]);
      }
    }
  }, [runoffStations, activeCode]);

  if (!runoffStations || Object.keys(runoffStations).length === 0) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#666', fontSize: '13px' }}>
        等待径流监测数据接入...
      </div>
    );
  }

  const stations = Object.keys(runoffStations);
  const data = runoffStations[activeCode] || {};

  const metrics = [
    { label: '当前流速', value: data.flow_speed, unit: 'm/s', color: '#4ade80' },
    { label: '瞬时流量', value: data.flow_rate,  unit: 'm³/s', color: '#38bdf8' },
    { label: '含沙量',   value: data.sand_content, unit: 'kg/L', color: '#facc15' },
    { label: '水位',     value: data.water_level,  unit: 'm',     color: '#fff' },
    { label: '累计流量', value: data.total_flow,   unit: 'm³',    color: '#fff' },
    { label: '液位压力', value: data.liquid_pressure, unit: 'kPa', color: '#fff' },
  ];

  const formatValue = (v) => {
    if (v == null) return '0.00';
    const num = Number(v);
    return isNaN(num) ? '—' : num.toFixed(2);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', height: '100%', padding: '5px 0' }}>
      {/* Station Selector Tabs */}
      <div style={{ display: 'flex', gap: '4px', overflowX: 'auto', paddingBottom: '4px', marginBottom: '2px' }} className="no-scrollbar">
        {stations.map(code => (
          <div 
            key={code}
            onClick={() => setActiveCode(code)}
            style={{
              padding: '2px 8px',
              fontSize: '10px',
              borderRadius: '4px',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              background: activeCode === code ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255,255,255,0.05)',
              border: activeCode === code ? '1px solid #38bdf8' : '1px solid transparent',
              color: activeCode === code ? '#38bdf8' : '#888',
              transition: 'all 0.2s'
            }}
          >
            {code.slice(-4)}站
          </div>
        ))}
      </div>

      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(3, 1fr)', 
        gap: '6px',
        textAlign: 'center' 
      }}>
        {metrics.slice(0, 3).map(m => (
          <div key={m.label} style={{ background: 'rgba(255,255,255,0.05)', padding: '8px 4px', borderRadius: '6px' }}>
            <div style={{ fontSize: '10px', color: '#888', marginBottom: '2px' }}>{m.label}</div>
            <div style={{ fontSize: '15px', color: m.color, fontWeight: 'bold' }}>
              {formatValue(m.value)} <span style={{fontSize:'9px', fontWeight: 'normal'}}>{m.unit}</span>
            </div>
          </div>
        ))}
      </div>
      
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(3, 1fr)', 
        gap: '6px',
        textAlign: 'center' 
      }}>
        {metrics.slice(3).map(m => (
          <div key={m.label} style={{ background: 'rgba(255,255,255,0.05)', padding: '8px 4px', borderRadius: '6px' }}>
            <div style={{ fontSize: '10px', color: '#888', marginBottom: '2px' }}>{m.label}</div>
            <div style={{ fontSize: '14px', color: m.color, fontWeight: 'bold' }}>
              {formatValue(m.value)} <span style={{fontSize:'9px', fontWeight: 'normal'}}>{m.unit}</span>
            </div>
          </div>
        ))}
      </div>

      <div style={{ flex: 1, minHeight: '40px', marginTop: '6px', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '8px' }}>
          <div style={{ fontSize: '10px', color: '#666', marginBottom: '4px', display: 'flex', justifyContent: 'space-between' }}>
            <span>站点: {activeCode}</span>
            <span style={{ color: '#4ade80' }}>● 实时上报</span>
          </div>
          <div style={{ height: '30px', background: 'rgba(250,204,21,0.03)', borderRadius: '4px', position: 'relative', overflow: 'hidden' }}>
             <svg width="100%" height="100%" preserveAspectRatio="none">
               <path 
                d="M0,30 C50,20 100,25 150,12 C200,18 250,8 300,30 L300,30 L0,30 Z" 
                fill="rgba(250,204,21,0.2)" 
                stroke="rgba(250,204,21,0.4)"
                strokeWidth="1"
              />
             </svg>
          </div>
          <div style={{ fontSize: '9px', color: '#444', marginTop: '4px', textAlign: 'right' }}>
            数据更新: {data.updated_at ? data.updated_at.replace('T', ' ').slice(0, 19) : '—'}
          </div>
      </div>
    </div>
  );
}
