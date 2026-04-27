import React from 'react'

export default function WaterPanel({ water }) {
  if (!water) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#64748b', fontSize: '13px', gap: '8px' }}>
        <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#64748b' }} />
        面源监测设备离线或暂无数据
      </div>
    )
  }

  const fmt = (val) => (val != null ? val : '—')

  const getStatusColor = (val, thresholds) => {
    if (val == null) return '#8fc8e8'
    if (val <= thresholds[0]) return '#4ade80'
    if (val <= thresholds[1]) return '#facc15'
    return '#f87171'
  }

  const card = (label, val, unit, color) => (
    <div
      style={{
        background: 'rgba(255,255,255,0.05)',
        padding: '10px 12px',
        borderRadius: '8px',
        borderLeft: `3px solid ${color}`,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
      }}
    >
      <div style={{ fontSize: 11, color: '#ccc', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 18, color: '#fff', fontWeight: 600 }}>
        {fmt(val)}
        {val != null && <span style={{ fontSize: 11, color: '#888', marginLeft: 3 }}>{unit}</span>}
      </div>
    </div>
  )

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gridTemplateRows: '1fr 1fr', gap: '8px', height: '100%', padding: '4px 0' }}>
      {card('氨氮', water.nh4n, 'mg/L', getStatusColor(water.nh4n, [1.0, 2.0]))}
      {card('总磷', water.tp, 'mg/L', getStatusColor(water.tp, [0.2, 0.4]))}
      {card('高猛酸盐', water.permanganate, 'mg/L', getStatusColor(water.permanganate, [6.0, 15.0]))}
      {card('总氮', water.tn, 'mg/L', getStatusColor(water.tn, [1.0, 2.0]))}
    </div>
  )
}
