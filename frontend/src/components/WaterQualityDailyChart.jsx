import ReactECharts from 'echarts-for-react'

const TOOLTIP = { 
  backgroundColor: 'rgba(3, 17, 46, 0.95)', 
  borderColor: 'rgba(56, 189, 248, 0.5)', 
  borderWidth: 1,
  textStyle: { color: '#e0f0ff', fontSize: 11 },
  padding: [6, 8],
  backdropFilter: 'blur(8px)',
  confine: true
}
const AXIS_LABEL = { color: '#8fc8e8', fontSize: 11, fontFamily: 'monospace' }
const SPLIT_LINE = { lineStyle: { color: 'rgba(56, 189, 248, 0.1)', type: 'dotted' } }

export default function WaterQualityDailyChart({ data }) {
  const td = data?.data || []
  if (td.length === 0) return <Empty />

  const option = {
    backgroundColor: 'transparent',
    grid: { top: 60, bottom: 40, left: 45, right: 45, containLabel: true },
    tooltip: { ...TOOLTIP, trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(56,189,248,0.05)' } } },
    legend: {
      top: 0,
      textStyle: { color: '#b0d8f0', fontSize: 12 },
      icon: 'circle',
      itemGap: 24,
    },
    xAxis: {
      type: 'category',
      data: td.map(d => d.date.slice(5)),
      axisLabel: { ...AXIS_LABEL, interval: 'auto', rotate: 20 },
      axisLine: { lineStyle: { color: 'rgba(56, 189, 248, 0.4)' }, width: 2 },
      axisTick: { show: false },
      splitLine: { show: false },
    },
    yAxis: [
      {
        type: 'value',
        name: '浓度 (mg/L)',
        nameTextStyle: { color: '#38bdf8', fontSize: 11, padding: [0, 20, 0, 0] },
        axisLabel: { ...AXIS_LABEL, color: '#38bdf8' },
        splitLine: SPLIT_LINE,
      },
      {
        type: 'value',
        name: 'pH / 温度 / 溶解氧',
        nameTextStyle: { color: '#fbbf24', fontSize: 11, padding: [0, 0, 0, 20] },
        axisLabel: AXIS_LABEL,
        splitLine: { show: false },
      }
    ],
    series: [
      {
        name: 'COD', type: 'bar', barWidth: '35%',
        data: td.map(d => d.cod),
        itemStyle: { 
            color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#38bdf8' }, { offset: 1, color: 'rgba(56, 189, 248, 0.05)' }] },
            borderRadius: [4, 4, 0, 0],
        },
        tooltip: { valueFormatter: (v) => v != null ? `${v} mg/L` : '—' }
      },
      {
        name: '总氮', type: 'line', smooth: true,
        data: td.map(d => d.tn),
        lineStyle: { color: '#a855f7', width: 2 },
        itemStyle: { color: '#a855f7' },
        tooltip: { valueFormatter: (v) => v != null ? `${v} mg/L` : '—' }
      },
      {
        name: '氨氮', type: 'line', smooth: true,
        data: td.map(d => d.nh4n),
        lineStyle: { color: '#fbbf24', width: 2 },
        itemStyle: { color: '#fbbf24' },
        tooltip: { valueFormatter: (v) => v != null ? `${v} mg/L` : '—' }
      },
      {
        name: '总磷', type: 'line', smooth: true,
        data: td.map(d => d.tp),
        lineStyle: { color: '#f87171', width: 2, type: 'dashed' },
        itemStyle: { color: '#f87171' },
        tooltip: { valueFormatter: (v) => v != null ? `${v} mg/L` : '—' }
      },
      {
        name: 'pH值', type: 'line', smooth: true, yAxisIndex: 1,
        data: td.map(d => d.ph),
        lineStyle: { color: '#4ade80', width: 2 },
        itemStyle: { color: '#4ade80' },
        tooltip: { valueFormatter: (v) => v ?? '—' }
      },
      {
        name: '溶解氧', type: 'line', smooth: true, yAxisIndex: 1,
        data: td.map(d => d.do),
        lineStyle: { color: '#60a5fa', width: 2, type: 'dotted' },
        itemStyle: { color: '#60a5fa' },
        tooltip: { valueFormatter: (v) => v != null ? `${v} mg/L` : '—' }
      },
      {
        name: '水温', type: 'line', smooth: true, yAxisIndex: 1,
        data: td.map(d => d.water_temp),
        lineStyle: { color: '#fb923c', width: 2 },
        itemStyle: { color: '#fb923c' },
        tooltip: { valueFormatter: (v) => v != null ? `${v} °C` : '—' }
      },
      {
        name: '电导率', type: 'line', smooth: true,
        data: td.map(d => d.ec),
        lineStyle: { color: '#94a3b8', width: 1 },
        itemStyle: { color: '#94a3b8' },
        tooltip: { valueFormatter: (v) => v != null ? `${v} μS/cm` : '—' },
        showSymbol: false
      },
      {
        name: '浊度', type: 'line', smooth: true,
        data: td.map(d => d.turbidity),
        lineStyle: { color: '#d1d5db', width: 1 },
        itemStyle: { color: '#d1d5db' },
        tooltip: { valueFormatter: (v) => v != null ? `${v} NTU` : '—' },
        showSymbol: false
      },
    ],
  }

  return <ReactECharts option={option} style={{ height: '100%' }} opts={{ renderer: 'canvas' }} />
}

function Empty() {
  return <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)', fontSize: 13, letterSpacing: 2 }}>[] NO DATA DETECTED</div>
}
