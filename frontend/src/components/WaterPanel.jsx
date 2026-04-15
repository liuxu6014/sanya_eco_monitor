import React from 'react';

export default function WaterPanel({ water }) {
  if (!water) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#64748b', fontSize: '13px', gap: '8px' }}>
        <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#64748b' }} />
        面源监测设备离线或暂无数据
      </div>
    )
  }

  const data = water;

  const fmt = (val) => val != null ? val : '—';

  const getStatusColor = (val, thresholds) => {
    if (val == null) return '#8fc8e8';
    if (val <= thresholds[0]) return '#4ade80';
    if (val <= thresholds[1]) return '#facc15';
    return '#f87171';
  };

  const card = (label, val, unit, color) => (
    <div style={{
      background: 'rgba(255,255,255,0.05)',
      padding: '8px 10px',
      borderRadius: '8px',
      borderLeft: `3px solid ${color}`,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
    }}>
      <div style={{ fontSize: 11, color: '#ccc', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 17, color: '#fff', fontWeight: 600 }}>
        {fmt(val)}{val != null && <span style={{ fontSize: 11, color: '#888', marginLeft: 3 }}>{unit}</span>}
      </div>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', height: '100%', padding: '4px 0' }}>

      {/* Top metrics row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.05)', padding: '10px', borderRadius: '8px', flexShrink: 0 }}>
        <div style={{ textAlign: 'center', flex: 1 }}>
          <div style={{ fontSize: '11px', color: '#aaa' }}>pH值</div>
          <div style={{ fontSize: '20px', color: getStatusColor(data.ph, [8.5, 9.0]), fontWeight: 'bold' }}>{fmt(data.ph)}</div>
        </div>
        <div style={{ width: '1px', height: '30px', background: 'rgba(255,255,255,0.1)' }}></div>
        <div style={{ textAlign: 'center', flex: 1 }}>
          <div style={{ fontSize: '11px', color: '#aaa' }}>溶解氧</div>
          <div style={{ fontSize: '20px', color: '#38bdf8', fontWeight: 'bold' }}>{fmt(data.do)}{data.do != null && <span style={{ fontSize: '11px' }}> mg/L</span>}</div>
        </div>
        <div style={{ width: '1px', height: '30px', background: 'rgba(255,255,255,0.1)' }}></div>
        <div style={{ textAlign: 'center', flex: 1 }}>
          <div style={{ fontSize: '11px', color: '#aaa' }}>COD</div>
          <div style={{ fontSize: '20px', color: getStatusColor(data.cod, [20, 40]), fontWeight: 'bold' }}>{fmt(data.cod)}{data.cod != null && <span style={{ fontSize: '11px' }}> mg/L</span>}</div>
        </div>
      </div>

      {/* 6-cell grid filling remaining space - 3 cols × 2 rows */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gridTemplateRows: 'repeat(2, 1fr)', gap: '8px', minHeight: 0 }}>
        {card('氨氮 (NH3-N)', data.nh4n, 'mg/L', getStatusColor(data.nh4n, [1.0, 2.0]))}
        {card('总磷 (TP)', data.tp, 'mg/L', getStatusColor(data.tp, [0.2, 0.4]))}
        {card('总氮 (TN)', data.tn, 'mg/L', getStatusColor(data.tn, [1.0, 2.0]))}
        {card('浊度 (Turbidity)', data.turbidity, 'NTU', getStatusColor(data.turbidity, [20, 50]))}
        {card('电导率 (EC)', data.ec, 'μS/cm', getStatusColor(data.ec, [1000, 2000]))}
        {card('水温', data.water_temp, '°C', '#38bdf8')}
      </div>

    </div>
  );
}
