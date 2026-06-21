import ResponsiveEChart from './ResponsiveEChart.jsx'

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

const CHART_FONT_FAMILY = 'Microsoft YaHei, PingFang SC, Noto Sans CJK SC, Source Han Sans SC, Arial, sans-serif'
const AXIS_LABEL = { color: '#8fc8e8', fontSize: 11, fontFamily: CHART_FONT_FAMILY, hideOverlap: true }

export default function CombinedTrendChart({ data }) {
  const td = data?.data || []
  if (td.length === 0) return <Empty />

  const xData = td.map(d => d.date.slice(5))
  const insectData = td.map(d => d.insect)

  const option = {
    backgroundColor: 'transparent',
    grid: { top: 42, bottom: 35, left: 55, right: 28, containLabel: true },
    tooltip: { 
      ...TOOLTIP, 
      trigger: 'axis', 
      axisPointer: { type: 'cross', crossStyle: { color: 'rgba(255,255,255,0.4)', type: 'dashed' } } 
    },
    legend: {
      data: ['虫情'],
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
    yAxis: {
      type: 'value', name: '虫情数量 (只)',
      nameTextStyle: { color: '#ff7043', fontSize: 11, fontFamily: CHART_FONT_FAMILY, padding: [0, 20, 10, 0] },
      axisLabel: { ...AXIS_LABEL, color: '#ff9a80' },
      splitLine: { lineStyle: { color: 'rgba(255, 112, 67, 0.1)', type: 'dashed' } },
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 }
    ],
    series: [
      {
        name: '虫情', 
        type: 'bar', 
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
        tooltip: { show: false },
        zlevel: 3,
      },
    ],
  }

  return <ResponsiveEChart option={option} resizeDeps={[td.length]} opts={{ renderer: 'canvas' }} />
}

function Empty() {
  return <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)', fontSize: 13, letterSpacing: 2 }}>[] NO DATA DETECTED</div>
}
