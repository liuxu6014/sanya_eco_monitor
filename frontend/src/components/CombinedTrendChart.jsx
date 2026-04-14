import ReactECharts from 'echarts-for-react'

const TOOLTIP = { 
  backgroundColor: 'rgba(3, 17, 46, 0.95)', 
  borderColor: 'rgba(56, 189, 248, 0.5)', 
  borderWidth: 1,
  textStyle: { color: '#e0f0ff', fontSize: 13, textShadow: '0 0 5px rgba(56,189,248,0.3)' },
  padding: [12, 16],
  backdropFilter: 'blur(8px)',
  shadowBlur: 20,
  shadowColor: 'rgba(56,189,248,0.2)',
  borderRadius: 8
}

const AXIS_LABEL = { color: '#8fc8e8', fontSize: 11, fontFamily: 'monospace' }

export default function CombinedTrendChart({ data }) {
  const td = data?.data || []
  if (td.length === 0) return <Empty />

  const xData = td.map(d => d.date.slice(5))
  const insectData = td.map(d => d.insect)
  const sporeData = td.map(d => d.spore)

  const option = {
    backgroundColor: 'transparent',
    grid: { top: 50, bottom: 35, left: 45, right: 45, containLabel: true },
    tooltip: { 
      ...TOOLTIP, 
      trigger: 'axis', 
      axisPointer: { type: 'cross', crossStyle: { color: 'rgba(255,255,255,0.4)', type: 'dashed' } } 
    },
    legend: {
      data: ['虫情', '孢子'],
      top: 0, left: 'center',
      textStyle: { color: '#b0d8f0', fontSize: 12, fontWeight: 500 },
      itemGap: 24,
      icon: 'circle',
    },
    xAxis: {
      type: 'category',
      data: xData,
      axisLabel: { ...AXIS_LABEL, interval: 'auto', rotate: 15 },
      axisLine: { lineStyle: { color: 'rgba(0,180,255,0.3)' }, width: 2 },
      axisTick: { show: false },
      splitLine: { show: false },
    },
    yAxis: [
      {
        type: 'value', name: '虫情数量 (只)',
        nameTextStyle: { color: '#ff7043', fontSize: 11, padding: [0, 20, 10, 0] },
        axisLabel: { ...AXIS_LABEL, color: '#ff9a80' },
        splitLine: { lineStyle: { color: 'rgba(255, 112, 67, 0.1)', type: 'dashed' } },
      },
      {
        type: 'value', name: '孢子量 (个)',
        nameTextStyle: { color: '#d500f9', fontSize: 11, padding: [0, 0, 10, 20] },
        axisLabel: { ...AXIS_LABEL, color: '#ea80fc' },
        splitLine: { show: false },
      },
    ],
    dataZoom: [
      { type: 'inside', start: 0, end: 100 }
    ],
    series: [
      {
        name: '虫情', 
        type: 'bar', 
        yAxisIndex: 0,
        data: insectData,
        barMaxWidth: 16,
        itemStyle: {
          color: { 
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1, 
            colorStops: [{ offset: 0, color: 'rgba(255, 112, 67, 0.9)' }, { offset: 1, color: 'rgba(255, 112, 67, 0.1)' }] 
          },
          borderRadius: [4, 4, 0, 0],
          borderWidth: 1,
          borderColor: 'rgba(255, 112, 67, 0.8)',
          shadowBlur: 10,
          shadowColor: 'rgba(255, 112, 67, 0.5)',
        },
        zlevel: 2,
      },
      // Pictorial bar for glowing top cap on the bar
      {
        name: '虫情高光',
        type: 'pictorialBar',
        symbol: 'rect',
        itemStyle: { color: '#fff', shadowBlur: 10, shadowColor: '#fff' },
        symbolRepeat: false,
        symbolSize: ['100%', 3],
        symbolPosition: 'end',
        symbolOffset: [0, -2],
        data: insectData,
        yAxisIndex: 0,
        tooltip: { show: false },
        zlevel: 3,
      },
      {
        name: '孢子', 
        type: 'line', 
        yAxisIndex: 1, 
        smooth: true,
        data: sporeData,
        symbol: 'circle',
        symbolSize: 8,
        showSymbol: false,
        lineStyle: { 
          color: '#00e5ff', 
          width: 3,
          shadowBlur: 15,
          shadowColor: '#00e5ff',
          shadowOffsetY: 0
        },
        areaStyle: { 
          color: { 
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1, 
            colorStops: [{ offset: 0, color: 'rgba(0, 229, 255, 0.4)' }, { offset: 1, color: 'rgba(0, 229, 255, 0)' }] 
          } 
        },
        itemStyle: {
          color: '#fff',
          borderColor: '#00e5ff',
          borderWidth: 2,
          shadowColor: '#00e5ff',
          shadowBlur: 10
        },
        markPoint: {
          data: [
            { type: 'max', name: '最高孢子量', symbolSize: 45, itemStyle: { color: 'rgba(0, 229, 255, 0.8)', shadowBlur: 10, shadowColor: '#00e5ff' } }
          ],
          label: { color: '#fff', fontSize: 10, fontWeight: 'bold' }
        },
        zlevel: 4,
      },
    ],
  }

  return <ReactECharts option={option} style={{ height: '100%' }} opts={{ renderer: 'canvas' }} />
}

function Empty() {
  return <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)', fontSize: 13, letterSpacing: 2 }}>[] NO DATA DETECTED</div>
}
