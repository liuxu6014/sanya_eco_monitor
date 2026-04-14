import ReactECharts from 'echarts-for-react'

function RingGauge({ value, label, color, sublabel }) {
  const opt = {
    backgroundColor: 'transparent',
    series: [{
      type: 'gauge',
      radius: '95%',
      startAngle: 210, endAngle: -30,
      min: 0, max: 100,
      progress: { show: true, width: 6, itemStyle: { color, shadowColor: color, shadowBlur: 4 } },
      axisLine: { lineStyle: { width: 6, color: [[1, 'rgba(255,255,255,0.05)']] } },
      axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false },
      pointer: { show: false },
      detail: {
        valueAnimation: true,
        formatter: `{value}`,
        color: '#e0f2fe', fontSize: 13, fontWeight: 900,
        offsetCenter: [0, '15%']
      },
      title: { offsetCenter: [0, '75%'], color: '#7dd3fc', fontSize: 8, fontWeight: 500 },
      data: [{ value: value ?? 0, name: label }],
    }],
  }
  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', flex: 1, minWidth: 0 }}>
      <ReactECharts option={opt} style={{ height: 60, width: '100%' }} opts={{ renderer: 'canvas' }} />
      <div style={{ fontSize: 8, color: '#4a7fa0', marginTop: -5, textAlign: 'center', fontWeight: 400 }}>{sublabel}</div>
    </div>
  )
}

function AlertBadge({ level, msg }) {
  const colors = {
    danger:  { bg: 'rgba(239, 68, 68, 0.1)',   border: 'rgba(239, 68, 68, 0.3)',  dot: '#ef4444', text: '#f87171' },
    warning: { bg: 'rgba(245, 158, 11, 0.08)',  border: 'rgba(245, 158, 11, 0.25)', dot: '#f59e0b', text: '#fbbf24' },
    info:    { bg: 'rgba(14, 165, 233, 0.08)',  border: 'rgba(14, 165, 233, 0.2)', dot: '#0ea5e9', text: '#7dd3fc' },
  }
  const c = colors[level] || colors.info
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      background: c.bg, border: `1px solid ${c.border}`,
      borderRadius: 4, padding: '4px 8px', width: '100%'
    }}>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: c.dot, boxShadow: `0 0 6px ${c.dot}`, flexShrink: 0 }} />
      <span style={{ fontSize: 10, color: c.text, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{msg}</span>
    </div>
  )
}

export default function NutrientPanel({ ecoIndex }) {
  const d = ecoIndex?.data

  if (!d) {
    return <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 12 }}>ANALYZING...</div>
  }

  const gauges = [
    { value: d.eco_health,          label: 'ECO HEALTH', color: '#10b981', sublabel: 'Overall' },
    { value: d.growth_suitability,  label: 'GROWTH',     color: '#0ea5e9', sublabel: 'Suitable' },
    { value: 100 - d.pest_risk,     label: 'PEST FRE',   color: '#8b5cf6', sublabel: 'Safety' },
    { value: 100 - d.irrigation_urgency, label: 'MOISTURE', color: '#f59e0b', sublabel: 'Supply' },
  ]

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
        {gauges.map(g => <RingGauge key={g.label} {...g} />)}
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 5, overflow: 'hidden', padding: '0 4px' }}>
        <div style={{ fontSize: 8, color: '#4a7fa0', fontWeight: 600, letterSpacing: 0.5 }}>INTELLIGENT ALERT MONITOR</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {(d.alerts || []).slice(0, 3).map((a, i) => (
            <AlertBadge key={i} level={a.level} msg={a.msg} />
          ))}
        </div>
        
        <div style={{ marginTop: 'auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
           <div style={{ fontSize: 8, color: '#315c7a' }}>ALERTS REFRESHED: {new Date().toLocaleDateString()}</div>
           <div style={{ fontSize: 8, color: '#0ea5e9', fontWeight: 700 }}>LIVE ANALYSIS</div>
        </div>
      </div>
    </div>
  )
}
