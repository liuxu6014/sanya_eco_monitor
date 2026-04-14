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

export default function RunoffDailyChart({ data }) {
  const td = data?.data || []
  if (td.length === 0) return <Empty />

  const option = {
    backgroundColor: 'transparent',
    grid: { top: 50, bottom: 40, left: 10, right: 10, containLabel: true },
    tooltip: { ...TOOLTIP, trigger: 'axis', axisPointer: { type: 'line', lineStyle: { color: 'rgba(56, 189, 248, 0.5)', width: 2, type: 'dashed' } } },
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
      boundaryGap: false,
    },
    yAxis: [
      {
        type: 'value',
        name: '流速 (m/s)',
        nameTextStyle: { color: '#4ade80', fontSize: 11, padding: [0, 20, 0, 0] },
        axisLabel: { ...AXIS_LABEL, color: '#4ade80' },
        splitLine: SPLIT_LINE,
      },
      {
        type: 'value',
        name: '含沙量 (kg/L)',
        nameTextStyle: { color: '#facc15', fontSize: 11, padding: [0, 0, 0, 20] },
        axisLabel: { ...AXIS_LABEL, color: '#facc15' },
        splitLine: { show: false },
      }
    ],
    series: [
      {
        name: '平均流速', type: 'line', smooth: true,
        data: td.map(d => d.flow),
        lineStyle: { 
          color: '#4ade80', width: 3,
          shadowBlur: 10, shadowColor: 'rgba(74, 222, 128, 0.8)', shadowOffsetY: 3
        },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(74, 222, 128, 0.3)' }, { offset: 1, color: 'rgba(74, 222, 128, 0)' }] } },
        symbol: 'circle',
        symbolSize: 6,
        showSymbol: false,
        itemStyle: { color: '#4ade80', borderWidth: 2, shadowColor: '#4ade80', shadowBlur: 10 },
      },
      {
        name: '平均含沙量', type: 'line', smooth: true, yAxisIndex: 1,
        data: td.map(d => d.sand),
        lineStyle: { 
          color: '#facc15', width: 3, type: 'dashed',
          shadowBlur: 10, shadowColor: 'rgba(250, 204, 21, 0.8)', shadowOffsetY: 3
        },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(250, 204, 21, 0.3)' }, { offset: 1, color: 'rgba(250, 204, 21, 0)' }] } },
        symbol: 'circle',
        symbolSize: 6,
        showSymbol: false,
        itemStyle: { color: '#facc15', borderWidth: 2, shadowColor: '#facc15', shadowBlur: 10 },
      }
    ],
  }

  return <ReactECharts option={option} style={{ height: '100%' }} opts={{ renderer: 'canvas' }} />
}

function Empty() {
  return <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)', fontSize: 13, letterSpacing: 2 }}>[] NO DATA DETECTED</div>
}
