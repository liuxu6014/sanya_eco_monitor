import React from 'react'
import ReactECharts from 'echarts-for-react'

// Helper for rendering a small gauge/bar
function GaugeBar({ label, value, max, unit, color }) {
  const v = value != null ? Number(value) : 0;
  const pct = Math.min((v / max) * 100, 100);
  return (
    <div style={{ padding: '6px 10px', background: 'rgba(255,255,255,0.05)', borderRadius: '6px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
        <span style={{ fontSize: '12px', color: '#ccc' }}>{label}</span>
        <span style={{ fontSize: '13px', color: '#fff', fontWeight: 'bold' }}>
          {v.toFixed(1)} <span style={{ fontSize: '10px', color: '#888' }}>{unit}</span>
        </span>
      </div>
      <div style={{ height: '4px', background: 'rgba(0,0,0,0.3)', borderRadius: '2px', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: '2px', transition: 'width 1s ease' }} />
      </div>
    </div>
  )
}

export default function SoilPanel({ soil, trend }) {
  // If soil prop itself contains a .data (from direct API call), use that.
  // Otherwise use the prop itself (from overview API).
  const s = soil?.data || soil || {};

  // If real data doesn't provide these, it's better to show 0/missing or a clear null
  const n = s.n ?? 0; 
  const p = s.p ?? 0;
  const k = s.k ?? 0;
  const ph = s.ph ?? 0;
  const ec = s.ec ?? 0;
  
  const temp = s.temperature_10cm ?? 0;
  const moisture = s.moisture_10cm ?? 0;

  // Radar chart for N, P, K, pH, Moisture
  const radarOpt = {
    backgroundColor: 'transparent',
    radar: {
      indicator: [
        { name: '氮(N)', max: 100 },
        { name: '磷(P)', max: 50 },
        { name: '钾(K)', max: 100 },
        { name: '湿度(Moist)', max: 60 },
        { name: 'pH', max: 14 }
      ],
      center: ['50%', '50%'],
      radius: '65%',
      splitNumber: 4,
      name: { textStyle: { color: '#8fc8e8', fontSize: 10 } },
      splitLine: { lineStyle: { color: 'rgba(56, 189, 248, 0.2)' } },
      splitArea: { show: false },
      axisLine: { lineStyle: { color: 'rgba(56, 189, 248, 0.2)' } }
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: [n, p, k, moisture, ph],
            name: '当前肥力',
            areaStyle: { color: 'rgba(56,189,248,0.3)' },
            lineStyle: { color: '#38bdf8', width: 2 },
            itemStyle: { color: '#38bdf8' }
          }
        ]
      }
    ]
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '10px', paddingTop: '5px' }}>
      {/* Overview Top Area */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
        <div style={{ 
            background: 'rgba(255,255,255,0.05)', 
            padding: '10px', 
            borderRadius: '8px', 
            textAlign: 'center',
            borderBottom: '2px solid #00ff9d'
          }}>
          <div style={{ fontSize: '11px', color: '#aaa', marginBottom: '2px' }}>土壤温度</div>
          <div style={{ fontSize: '16px', color: '#fff', fontWeight: 'bold' }}>{temp.toFixed(1)} <span style={{fontSize:'12px', color:'#aaa'}}>°C</span></div>
        </div>
        <div style={{ 
            background: 'rgba(255,255,255,0.05)', 
            padding: '10px', 
            borderRadius: '8px', 
            textAlign: 'center',
            borderBottom: '2px solid #00d4ff'
          }}>
          <div style={{ fontSize: '11px', color: '#aaa', marginBottom: '2px' }}>土壤湿度</div>
          <div style={{ fontSize: '16px', color: '#fff', fontWeight: 'bold' }}>{moisture.toFixed(1)} <span style={{fontSize:'12px', color:'#aaa'}}>%</span></div>
        </div>
      </div>

      <div style={{ display: 'flex', flex: 1, gap: '10px' }}>
         <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px', justifyContent: 'center' }}>
            <GaugeBar label="氮离子 (N)" value={n} max={100} unit="mg/kg" color="#f472b6" />
            <GaugeBar label="磷离子 (P)" value={p} max={50} unit="mg/kg" color="#fbbf24" />
            <GaugeBar label="钾离子 (K)" value={k} max={100} unit="mg/kg" color="#a855f7" />
         </div>
         <div style={{ width: '45%', position: 'relative' }}>
            <ReactECharts option={radarOpt} style={{ width: '100%', height: '100%', position: 'absolute' }} opts={{renderer: 'canvas'}} />
         </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-around', alignItems: 'center', background: 'rgba(255,255,255,0.05)', padding: '10px', borderRadius: '8px' }}>
         <div>
            <div style={{ fontSize: '11px', color: '#aaa' }}>pH 值</div>
            <div style={{ fontSize: '16px', color: '#fff', fontWeight: 'bold' }}>{ph.toFixed(1)}</div>
         </div>
         <div style={{ width: '1px', height: '20px', background: 'rgba(255,255,255,0.1)' }}></div>
         <div>
            <div style={{ fontSize: '11px', color: '#aaa' }}>电导率 (EC)</div>
            <div style={{ fontSize: '16px', color: '#fff', fontWeight: 'bold' }}>{ec} <span style={{fontSize:'11px', color:'#888'}}>μS/cm</span></div>
         </div>
      </div>
    </div>
  )
}
