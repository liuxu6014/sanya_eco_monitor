import ReactECharts from 'echarts-for-react'

export default function WeatherDailyChart({ data }) {
  const td = data?.data || []
  if (td.length === 0) return <Empty />

  const option = {
    backgroundColor: 'transparent',
    grid: { top: 80, bottom: 40, left: 50, right: 60 },
    tooltip: { 
      trigger: 'axis', 
      backgroundColor: 'rgba(3, 17, 46, 0.95)', 
      borderColor: '#60a5fa', 
      textStyle: { color: '#fff', fontSize: 12 },
      axisPointer: { type: 'line', lineStyle: { color: 'rgba(255, 255, 255, 0.1)', width: 1 } }
    },
    legend: {
      top: 15,
      textStyle: { color: '#8fc8e8', fontSize: 11 },
      icon: 'path://M0 5 L10 5 L10 5.5 L0 5.5 Z',
      itemWidth: 20,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: td.map(d => d.date.slice(5)),
      axisLabel: { color: '#64748b', fontSize: 10, interval: Math.floor(td.length / 10) },
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
      splitLine: { show: false },
    },
    yAxis: [
      {
        type: 'value',
        name: 'TEMPERATURE FIELDS (°C)',
        nameTextStyle: { color: '#64748b', fontSize: 9, align: 'right', padding: [0, 0, 15, 0] },
        axisLabel: { color: '#94a3b8', fontSize: 11 },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.03)', type: 'dashed' } },
        axisLine: { show: false },
      },
      {
        type: 'value',
        name: 'PRECIPITATION (mm)',
        nameTextStyle: { color: '#64748b', fontSize: 9, align: 'left', padding: [0, 0, 15, 0] },
        axisLabel: { color: '#60a5fa', fontSize: 11 },
        splitLine: { show: false },
        axisLine: { show: false },
      },
    ],
    series: [
      {
        name: '温度变化带', type: 'line',
        data: td.map(d => d.max_temp),
        lineStyle: { opacity: 0 },
        stack: 'confidence-band',
        symbol: 'none'
      },
      {
        name: '温度变化带', type: 'line',
        data: td.map(d => d.min_temp ? d.max_temp - d.min_temp : 0),
        lineStyle: { opacity: 0 },
        stack: 'confidence-band',
        symbol: 'none',
        areaStyle: { color: 'rgba(251, 146, 60, 0.15)' }
      },
      {
        name: '平均气温', type: 'line', smooth: 0.4,
        data: td.map(d => d.avg_temp),
        symbol: 'circle', symbolSize: 0,
        lineStyle: { 
            width: 3, 
            color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: '#facc15' }, { offset: 1, color: '#fb923c' }] },
            shadowBlur: 10, shadowColor: 'rgba(251, 146, 60, 0.7)'
        },
        emphasis: { lineStyle: { width: 5 } }
      },
      {
        name: '湿度场', type: 'line', smooth: true,
        data: td.map(d => d.avg_humidity),
        symbolSize: 0,
        lineStyle: { width: 1, color: 'rgba(56, 189, 248, 0.4)', type: 'dashed' },
        areaStyle: { color: 'rgba(56, 189, 248, 0.05)' }
      },
      {
        name: '降雨通量', type: 'bar', yAxisIndex: 1,
        data: td.map(d => d.total_rainfall),
        barWidth: '40%',
        itemStyle: {
          color: { 
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1, 
            colorStops: [{ offset: 0, color: '#60a5fa' }, { offset: 0.5, color: 'rgba(96, 165, 250, 0.2)' }, { offset: 1, color: 'transparent' }] 
          },
          borderRadius: [10, 10, 0, 0]
        },
        label: {
            show: true, position: 'top', color: '#60a5fa', fontSize: 9,
            formatter: params => params.value > 0 ? params.value : ''
        }
      },
      {
          name: '高危降雨点', type: 'effectScatter', yAxisIndex: 1,
          data: td.map(d => d.total_rainfall > 10 ? d.total_rainfall : null),
          symbolSize: 8,
          rippleEffect: { brushType: 'stroke', scale: 4, color: '#fb7185' },
          itemStyle: { color: '#fb7185', shadowBlur: 10 }
      }
    ],
  }

  return <ReactECharts option={option} style={{ height: '100%' }} opts={{ renderer: 'canvas' }} />
}

function Empty() {
  return <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#475569', fontSize: 12 }}>暂无数据</div>
}
