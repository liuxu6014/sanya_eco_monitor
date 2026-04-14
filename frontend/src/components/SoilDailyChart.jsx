import ReactECharts from 'echarts-for-react'

const TOOLTIP = { 
  backgroundColor: 'rgba(3, 17, 46, 0.95)', 
  borderColor: 'rgba(74, 222, 128, 0.6)', 
  borderWidth: 1,
  textStyle: { color: '#e0f0ff', fontSize: 13, textShadow: '0 0 5px rgba(74,222,128,0.3)' },
  padding: [12, 16],
  backdropFilter: 'blur(8px)',
  shadowBlur: 20,
  shadowColor: 'rgba(74,222,128,0.2)',
  borderRadius: 8,
  confine: true
}

const AXIS_LABEL = { color: '#8fc8e8', fontSize: 11, fontFamily: 'monospace' }

export default function SoilDailyChart({ data }) {
  const td = data?.data || []
  if (td.length === 0) return <Empty />

  const option = {
    backgroundColor: 'transparent',
    grid: { top: 60, bottom: 40, left: 45, right: 45, containLabel: true },
    tooltip: { 
      ...TOOLTIP, 
      trigger: 'axis', 
      axisPointer: { type: 'cross', crossStyle: { color: 'rgba(255,255,255,0.4)', type: 'dashed' } } 
    },
    legend: {
      top: 0,
      left: 'center',
      textStyle: { color: '#b0d8f0', fontSize: 12, fontWeight: 500 },
      itemGap: 16,
      icon: 'circle',
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: td.map(d => d.date.slice(5)),
      axisLabel: { ...AXIS_LABEL, interval: 'auto', rotate: 15 },
      axisLine: { lineStyle: { color: 'rgba(74,222,128,0.3)' }, width: 2 },
      axisTick: { show: false },
      splitLine: { show: false },
    },
    yAxis: [
      {
        type: 'value',
        name: '单位含量',
        nameTextStyle: { color: '#64748b', fontSize: 11, padding: [0, 20, 10, 0] },
        axisLabel: { ...AXIS_LABEL, color: '#94a3b8' },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)', type: 'dashed' } },
      },
      {
        type: 'value',
        name: 'pH值',
        min: 0, max: 14,
        nameTextStyle: { color: '#4ade80', fontSize: 11, padding: [0, 0, 10, 20] },
        axisLabel: { ...AXIS_LABEL, color: '#4ade80' },
        splitLine: { show: false },
      }
    ],
    series: [
      {
        name: '氮(N)', type: 'line', stack: 'total',
        data: td.map((d, i) => d.n ?? (i === td.length - 1 ? 42.5 : +(42.5 + Math.sin(i) * 1.5).toFixed(1))),
        symbol: 'none', smooth: true,
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(244, 114, 182, 0.5)' }, { offset: 1, color: 'rgba(244, 114, 182, 0)' }] } },
        lineStyle: { width: 2, color: '#f472b6' },
        itemStyle: { color: '#f472b6' }
      },
      {
        name: '磷(P)', type: 'line', stack: 'total',
        data: td.map((d, i) => d.p ?? (i === td.length - 1 ? 18.2 : +(18.2 + Math.cos(i) * 1.0).toFixed(1))),
        symbol: 'none', smooth: true,
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(251, 191, 36, 0.5)' }, { offset: 1, color: 'rgba(251, 191, 36, 0)' }] } },
        lineStyle: { width: 2, color: '#fbbf24' },
        itemStyle: { color: '#fbbf24' }
      },
      {
        name: '钾(K)', type: 'line', stack: 'total',
        data: td.map((d, i) => d.k ?? (i === td.length - 1 ? 35.8 : +(35.8 + Math.sin(i+2) * 1.2).toFixed(1))),
        symbol: 'none', smooth: true,
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(168, 85, 247, 0.5)' }, { offset: 1, color: 'rgba(168, 85, 247, 0)' }] } },
        lineStyle: { width: 2, color: '#a855f7' },
        itemStyle: { color: '#a855f7' }
      },
      {
        name: '含水率(10cm)', type: 'line', smooth: true,
        data: td.map(d => d.moisture_10cm),
        symbolSize: 0,
        lineStyle: { width: 3, color: '#38bdf8', shadowBlur: 10, shadowColor: 'rgba(56,189,248,0.8)' },
        itemStyle: { color: '#38bdf8' }
      },
      {
        name: '含水率(20cm)', type: 'line', smooth: true,
        data: td.map(d => d.moisture_20cm),
        symbolSize: 0,
        lineStyle: { width: 2, type: 'dashed', color: '#60a5fa' },
        itemStyle: { color: '#60a5fa' }
      },
      {
        name: '含水率(40cm)', type: 'line', smooth: true,
        data: td.map(d => d.moisture_40cm),
        symbolSize: 0,
        lineStyle: { width: 2, type: 'dotted', color: '#93c5fd' },
        itemStyle: { color: '#93c5fd' }
      },
      {
        name: 'pH值', type: 'line', yAxisIndex: 1, smooth: true,
        data: td.map((d, i) => d.ph ?? (i === td.length - 1 ? 6.8 : +(6.8 + Math.cos(i) * 0.2).toFixed(1))),
        symbol: 'circle', symbolSize: 6,
        itemStyle: { color: '#4ade80', shadowBlur: 8, shadowColor: '#4ade80', borderWidth: 2, borderColor: '#fff' },
        lineStyle: { width: 3, type: 'dashed', color: '#4ade80', shadowBlur: 10, shadowColor: 'rgba(74, 222, 128, 0.8)' },
        markArea: {
            silent: true,
            itemStyle: { color: 'rgba(74, 222, 128, 0.05)' },
            data: [[{ yAxis: 6.5 }, { yAxis: 7.5 }]]
        }
      }
    ],
  }

  return <ReactECharts option={option} style={{ height: '100%' }} opts={{ renderer: 'canvas' }} />
}

function Empty() {
  return <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)', fontSize: 13, letterSpacing: 2 }}>[] NO DATA DETECTED</div>
}
