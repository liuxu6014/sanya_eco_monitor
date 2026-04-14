import React from 'react';

export default function WaterPanel({ water }) {
  const data = water || {
    ph: 7.2,
    ec: 320,
    cod: 15.4,
    nh4n: 0.8, // 氨氮
    do: 6.5,   // 溶解氧
    tp: 0.12,  // 总磷
    tn: 1.5,   // 总氮
    turbidity: 12.0
  };

  const getStatusColor = (val, thresholds) => {
      // thresholds: [good, warning]
      if (val <= thresholds[0]) return '#4ade80'; // green
      if (val <= thresholds[1]) return '#facc15'; // yellow
      return '#f87171'; // red
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', height: '100%', padding: '5px 0' }}>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '8px' }}>
          <div style={{ textAlign: 'center', flex: 1 }}>
             <div style={{ fontSize: '12px', color: '#aaa' }}>pH值</div>
             <div style={{ fontSize: '20px', color: getStatusColor(data.ph, [8.5, 9.0]), fontWeight: 'bold' }}>{data.ph}</div>
          </div>
          <div style={{ width: '1px', height: '30px', background: 'rgba(255,255,255,0.1)' }}></div>
          <div style={{ textAlign: 'center', flex: 1 }}>
             <div style={{ fontSize: '12px', color: '#aaa' }}>溶解氧</div>
             <div style={{ fontSize: '20px', color: '#38bdf8', fontWeight: 'bold' }}>{data.do} <span style={{fontSize:'12px'}}>mg/L</span></div>
          </div>
          <div style={{ width: '1px', height: '30px', background: 'rgba(255,255,255,0.1)' }}></div>
          <div style={{ textAlign: 'center', flex: 1 }}>
             <div style={{ fontSize: '12px', color: '#aaa' }}>COD</div>
             <div style={{ fontSize: '20px', color: getStatusColor(data.cod, [20, 40]), fontWeight: 'bold' }}>{data.cod} <span style={{fontSize:'12px'}}>mg/L</span></div>
          </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
          <div style={{ background: 'rgba(255,255,255,0.05)', padding: '10px', borderRadius: '8px', borderLeft: `3px solid ${getStatusColor(data.nh4n, [1.0, 2.0])}` }}>
              <div style={{ fontSize: '13px', color: '#ccc' }}>氨氮 (NH3-N)</div>
              <div style={{ fontSize: '18px', color: '#fff', marginTop: '4px' }}>{data.nh4n} <span style={{fontSize:'12px', color: '#888'}}>mg/L</span></div>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.05)', padding: '10px', borderRadius: '8px', borderLeft: `3px solid ${getStatusColor(data.tp, [0.2, 0.4])}` }}>
              <div style={{ fontSize: '13px', color: '#ccc' }}>总磷 (TP)</div>
              <div style={{ fontSize: '18px', color: '#fff', marginTop: '4px' }}>{data.tp} <span style={{fontSize:'12px', color: '#888'}}>mg/L</span></div>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.05)', padding: '10px', borderRadius: '8px', borderLeft: `3px solid ${getStatusColor(data.tn, [1.0, 2.0])}` }}>
              <div style={{ fontSize: '13px', color: '#ccc' }}>总氮 (TN)</div>
              <div style={{ fontSize: '18px', color: '#fff', marginTop: '4px' }}>{data.tn} <span style={{fontSize:'12px', color: '#888'}}>mg/L</span></div>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.05)', padding: '10px', borderRadius: '8px', borderLeft: `3px solid ${getStatusColor(data.turbidity, [20, 50])}` }}>
              <div style={{ fontSize: '13px', color: '#ccc' }}>浊度 (Turbidity)</div>
              <div style={{ fontSize: '18px', color: '#fff', marginTop: '4px' }}>{data.turbidity} <span style={{fontSize:'12px', color: '#888'}}>NTU</span></div>
          </div>
      </div>

    </div>
  );
}
