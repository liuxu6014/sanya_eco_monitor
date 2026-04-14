import ReactECharts from 'echarts-for-react'

/**
 * Center panel: key metrics + radar chart overview.
 * (Full GIS map requires a map tile license; this provides
 *  a data-dense radar/summary view as a placeholder.)
 */
export default function CenterMap({ overview }) {
  const d = overview?.data || {}
  const weather = d.weather || {}
  const soil = d.soil || {}
  const insect = d.insect || {}
  const spore = d.spore || {}

  // Radar chart for multi-dimensional eco health
  const radarOption = {
    backgroundColor: 'transparent',
    radar: {
      indicator: [
        { name: '温度适宜度', max: 100 },
        { name: '土壤墒情', max: 100 },
        { name: '虫害风险', max: 100 },
        { name: '孢子压力', max: 100 },
        { name: '降雨充足度', max: 100 },
      ],
      shape: 'polygon',
      splitNumber: 4,
      axisName: { color: 'var(--text-secondary)', fontSize: 11 },
      splitLine: { lineStyle: { color: 'rgba(0,180,255,0.15)' } },
      splitArea: { areaStyle: { color: ['rgba(0,30,80,0.3)', 'rgba(0,20,60,0.3)'] } },
      axisLine: { lineStyle: { color: 'rgba(0,180,255,0.2)' } },
    },
    series: [{
      type: 'radar',
      data: [{
        value: [
          normalizeTemp(weather.temperature),
          soil.moisture_10cm != null ? Math.min(soil.moisture_10cm, 100) : 50,
          insect.latest_count ? Math.min(insect.latest_count / 2, 100) : 0,
          spore.latest_count ? Math.min(spore.latest_count * 5, 100) : 0,
          normalizeRain(weather.rainfall),
        ],
        name: '生态指标',
        itemStyle: { color: '#00d4ff' },
        lineStyle: { color: '#00d4ff', width: 2 },
        areaStyle: { color: 'rgba(0,212,255,0.15)' },
      }],
    }],
    tooltip: { trigger: 'item', backgroundColor: '#0a1a3a', borderColor: 'var(--border-glow)', textStyle: { color: '#e8f4ff', fontSize: 11 } },
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 8 }}>
      {/* Big KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 6 }}>
        <KpiCard label="今日虫情" value={insect.total_today ?? 0} unit="只" color="#ff7043" icon="🦟" />
        <KpiCard label="最新孢子" value={spore.latest_count ?? 0} unit="个" color="#7c4dff" icon="🍄" />
        <KpiCard label="当前温度" value={weather.temperature != null ? `${weather.temperature}°C` : '—'} color="#ff9800" icon="🌡️" />
        <KpiCard label="土壤湿度" value={soil.moisture_10cm != null ? `${soil.moisture_10cm.toFixed(1)}%` : '—'} color="#00ff9d" icon="💧" />
      </div>

      {/* Radar */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2 }}>生态健康雷达</div>
        <ReactECharts option={radarOption} style={{ flex: 1 }} opts={{ renderer: 'canvas' }} />
      </div>

      {/* Top insect species */}
      {insect.top_species && insect.top_species.length > 0 && (
        <div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>主要虫种（最新批次）</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {insect.top_species.map(([name, cnt]) => (
              <span key={name} className="tag tag-yellow">{name}: {cnt}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function KpiCard({ label, value, unit, color, icon }) {
  return (
    <div style={{
      background: `rgba(${hexToRgb(color) || '0,180,255'}, 0.08)`,
      border: `1px solid rgba(${hexToRgb(color) || '0,180,255'}, 0.25)`,
      borderRadius: 4, padding: '8px 10px', display: 'flex', alignItems: 'center', gap: 8,
    }}>
      <span style={{ fontSize: 18 }}>{icon}</span>
      <div>
        <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{label}</div>
        <div style={{ fontSize: 18, fontWeight: 700, color, lineHeight: 1.2 }}>
          {value}{unit && <span style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 2 }}>{unit}</span>}
        </div>
      </div>
    </div>
  )
}

function normalizeTemp(t) {
  if (t == null) return 50
  // 20-28°C is ideal (100), too hot or cold reduces
  const ideal = 24
  const dist = Math.abs(t - ideal)
  return Math.max(0, 100 - dist * 4)
}

function normalizeRain(r) {
  if (r == null) return 50
  if (r < 0.5) return 20  // drought
  if (r < 5) return 70
  if (r < 25) return 90
  return 60  // too much rain
}

function hexToRgb(hex) {
  const colors = {
    '#ff7043': '255,112,67', '#7c4dff': '124,77,255',
    '#ff9800': '255,152,0', '#00ff9d': '0,255,157',
    '#00d4ff': '0,212,255',
  }
  return colors[hex]
}
