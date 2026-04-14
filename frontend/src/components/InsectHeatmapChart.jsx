import ReactECharts from 'echarts-for-react'

const TOOLTIP = { 
  backgroundColor: 'rgba(5, 10, 25, 0.95)', 
  borderColor: 'rgba(255, 112, 67, 0.6)', 
  borderWidth: 1,
  textStyle: { color: '#e0f0ff', fontSize: 13, textShadow: '0 0 2px rgba(255, 112, 67, 0.5)' },
  padding: [12, 16],
  backdropFilter: 'blur(8px)',
  shadowBlur: 20,
  shadowColor: 'rgba(255, 112, 67, 0.2)',
  borderRadius: 8
}

export default function InsectHeatmapChart({ data }) {
  const hm = data?.data
  if (!hm || !hm.dates?.length) return <Empty />

  const { dates, species, values } = hm
  const maxVal = Math.max(...values.map(v => v[2]), 1)

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      ...TOOLTIP,
      formatter: p => `<div style="font-family: monospace; font-size: 11px; color: #8fc8e8; margin-bottom: 6px; letter-spacing: 1px;">TARGET: [${dates[p.data[0]]}] // ${species[p.data[1]]}</div>
        <div style="font-size: 14px; font-weight: bold;">捕获量: <b style="color:#ff7043; font-size:18px; text-shadow: 0 0 8px rgba(255,112,67,1);">${p.data[2]}</b> 只</div>`,
    },
    grid: { top: 20, bottom: 50, left: 100, right: 20, containLabel: false },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { color: '#8fc8e8', fontSize: 10, fontFamily: 'monospace', interval: 'auto', rotate: 30 },
      axisLine: { lineStyle: { color: 'rgba(56,189,248,0.3)' }, width: 2 },
      axisTick: { show: true, lineStyle: { color: 'rgba(56,189,248,0.3)' } },
      splitLine: { show: true, lineStyle: { color: 'rgba(56,189,248,0.05)', type: 'dashed' } }
    },
    yAxis: {
      type: 'category',
      data: species,
      nameTextStyle: { color: '#8fc8e8', padding: [0, 40, 0, 0] },
      axisLabel: { color: '#b0d8f0', fontSize: 11, fontWeight: 'bold' },
      axisLine: { lineStyle: { color: 'rgba(56,189,248,0.3)' }, width: 2 },
      axisTick: { show: true, lineStyle: { color: 'rgba(56,189,248,0.3)' } },
      splitLine: { show: true, lineStyle: { color: 'rgba(56,189,248,0.05)', type: 'dashed' } }
    },
    visualMap: {
      show: true,
      min: 0, max: maxVal,
      calculable: true,
      orient: 'horizontal',
      bottom: 0, right: 30,
      itemWidth: 10, itemHeight: 140,
      textStyle: { color: '#8fc8e8', fontSize: 10, fontFamily: 'monospace' },
      inRange: { 
          color: ['rgba(56, 189, 248, 0.4)', '#4ade80', '#fbbf24', '#ff7043', '#f43f5e'] 
      },
      outOfRange: { color: ['rgba(255,255,255,0.02)'] }
    },
    series: [
      {
        name: 'BackgroundGrid',
        type: 'scatter',
        symbol: 'rect',
        symbolSize: [4, 4],
        itemStyle: { color: 'rgba(255,255,255,0.03)' },
        data: values.map(v => [v[0], v[1], 1]),
        silent: true,
        zlevel: 1
      },
      {
        type: 'scatter',
        data: values.filter(v => v[2] > 0),
        symbol: 'circle',
        symbolSize: val => Math.min(35, Math.max(8, Math.pow(val[2], 0.5) * 4)), // dynamic scale
        itemStyle: {
            shadowBlur: 15,
            shadowColor: 'auto', // Inherits visual map color
            opacity: 0.85,
            borderColor: '#fff',
            borderWidth: 1
        },
        emphasis: { 
            scale: true,
            itemStyle: { 
                shadowBlur: 25,
                borderColor: '#fff',
                borderWidth: 2,
                opacity: 1
            } 
        },
        zlevel: 2
      }
    ],
  }

  return <ReactECharts option={option} style={{ height: '100%' }} opts={{ renderer: 'canvas' }} />
}

function Empty() {
  return <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)', fontSize: 13, letterSpacing: 2 }}>[] NO DATA DETECTED</div>
}
