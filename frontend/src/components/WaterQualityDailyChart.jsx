import ReactECharts from 'echarts-for-react'

const TOOLTIP = { 
  backgroundColor: 'rgba(3, 17, 46, 0.9)', 
  borderColor: 'rgba(56, 189, 248, 0.6)', 
  borderWidth: 1,
  textStyle: { color: '#e0f0ff', fontSize: 13, textShadow: '0 0 2px rgba(56,189,248,0.5)' },
  padding: [12, 16],
  backdropFilter: 'blur(5px)',
  shadowBlur: 15,
  shadowColor: 'rgba(56,189,248,0.2)',
}
const AXIS_LABEL = { color: '#8fc8e8', fontSize: 11, fontFamily: 'monospace' }
const SPLIT_LINE = { lineStyle: { color: 'rgba(56, 189, 248, 0.1)', type: 'dotted' } }

export default function WaterQualityDailyChart({ data }) {
  const td = data?.data || []
  if (td.length === 0) return <Empty />

  const option = {
    backgroundColor: 'transparent',
    grid: { top: 50, bottom: 40, left: 10, right: 10, containLabel: true },
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
        name: 'COD (mg/L)',
        nameTextStyle: { color: '#38bdf8', fontSize: 11, padding: [0, 20, 0, 0] },
        axisLabel: { ...AXIS_LABEL, color: '#38bdf8' },
        splitLine: SPLIT_LINE,
      },
      {
        type: 'value',
        name: '氨氮/总磷 (mg/L)',
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
            borderRadius: [8, 8, 0, 0],
            shadowBlur: 12,
            shadowColor: 'rgba(56, 189, 248, 0.5)'
        },
        animationDelay: (idx) => idx * 10
      },
      {
        name: '氨氮', type: 'line', smooth: true, yAxisIndex: 1,
        data: td.map(d => d.nh4n),
        lineStyle: { 
          color: '#fbbf24', width: 3,
          shadowBlur: 10, shadowColor: 'rgba(251, 191, 36, 0.8)', shadowOffsetY: 3
        },
        symbol: 'emptyCircle',
        symbolSize: 6,
        showSymbol: false,
        itemStyle: { color: '#fbbf24', borderWidth: 2 }
      },
      {
        name: '总磷', type: 'line', smooth: true, yAxisIndex: 1,
        data: td.map(d => d.tp),
        lineStyle: { 
          color: '#f87171', width: 3,
          type: 'dashed',
          shadowBlur: 10, shadowColor: 'rgba(248, 113, 113, 0.8)', shadowOffsetY: 3
        },
        symbol: 'emptyCircle',
        symbolSize: 6,
        showSymbol: false,
        itemStyle: { color: '#f87171', borderWidth: 2 }
      }
    ],
  }

  return <ReactECharts option={option} style={{ height: '100%' }} opts={{ renderer: 'canvas' }} />
}

function Empty() {
  return <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)', fontSize: 13, letterSpacing: 2 }}>[] NO DATA DETECTED</div>
}
