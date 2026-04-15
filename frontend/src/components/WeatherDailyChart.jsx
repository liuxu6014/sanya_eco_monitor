import ReactECharts from 'echarts-for-react'

export default function WeatherDailyChart({ data }) {
  const td = data?.data || []
  if (td.length === 0) return <Empty />

  // Smart interval: show at most ~8 labels regardless of data length
  const xInterval = td.length <= 8 ? 0 : Math.ceil(td.length / 8) - 1

  const option = {
    backgroundColor: 'transparent',
    grid: { top: 60, bottom: 40, left: 55, right: 60, containLabel: true },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(3, 17, 46, 0.95)',
      borderColor: '#60a5fa',
      textStyle: { color: '#fff', fontSize: 11 },
      axisPointer: { type: 'line', lineStyle: { color: 'rgba(255, 255, 255, 0.1)', width: 1 } }
    },
    legend: {
      top: 8,
      textStyle: { color: '#8fc8e8', fontSize: 10 },
      icon: 'path://M0 5 L10 5 L10 5.5 L0 5.5 Z',
      itemWidth: 16,
      itemGap: 12,
    },
    xAxis: {
      type: 'category',
      boundaryGap: true,
      data: td.map(d => d.date.slice(5)),
      axisLabel: {
        color: '#64748b',
        fontSize: 10,
        interval: xInterval,
        hideOverlap: true,
        rotate: td.length > 15 ? 30 : 0,
      },
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
      splitLine: { show: false },
    },
    yAxis: [
      {
        // Left: Temperature (°C) only — no humidity here
        type: 'value',
        name: '°C',
        nameTextStyle: { color: '#64748b', fontSize: 9 },
        axisLabel: { color: '#94a3b8', fontSize: 10, hideOverlap: true },
        splitNumber: 4,
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.03)', type: 'dashed' } },
        axisLine: { show: false },
      },
      {
        // Right: Precipitation (mm) + Humidity (%)
        type: 'value',
        name: 'mm / %',
        nameTextStyle: { color: '#64748b', fontSize: 9, align: 'left' },
        axisLabel: { color: '#60a5fa', fontSize: 10, hideOverlap: true },
        splitNumber: 4,
        splitLine: { show: false },
        axisLine: { show: false },
      },
    ],
    series: [
      // Temperature band (background fill between min-max)
      {
        name: '温度变化带', type: 'line',
        data: td.map(d => d.max_temp),
        lineStyle: { opacity: 0 },
        stack: 'temp-band',
        symbol: 'none',
        yAxisIndex: 0,
      },
      {
        name: '温度变化带', type: 'line',
        data: td.map(d => (d.min_temp != null && d.max_temp != null) ? d.max_temp - d.min_temp : 0),
        lineStyle: { opacity: 0 },
        stack: 'temp-band',
        symbol: 'none',
        areaStyle: { color: 'rgba(251, 146, 60, 0.15)' },
        yAxisIndex: 0,
      },
      // Average temperature
      {
        name: '平均气温', type: 'line', smooth: 0.4,
        data: td.map(d => d.avg_temp),
        symbol: 'circle', symbolSize: 0,
        yAxisIndex: 0,
        lineStyle: {
          width: 3,
          color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: '#facc15' }, { offset: 1, color: '#fb923c' }] },
          shadowBlur: 10, shadowColor: 'rgba(251, 146, 60, 0.7)'
        },
        emphasis: { lineStyle: { width: 5 } }
      },
      // Humidity — moved to RIGHT axis (yAxisIndex: 1) to not distort temperature scale
      {
        name: '湿度场', type: 'line', smooth: true,
        data: td.map(d => d.avg_humidity),
        symbolSize: 0,
        yAxisIndex: 1,
        lineStyle: { width: 1, color: 'rgba(56, 189, 248, 0.4)', type: 'dashed' },
        areaStyle: { color: 'rgba(56, 189, 248, 0.04)' }
      },
      // Rainfall bars
      {
        name: '降雨通量', type: 'bar', yAxisIndex: 1,
        data: td.map(d => d.total_rainfall),
        barMaxWidth: 20,
        barMinHeight: 2,
        itemStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [{ offset: 0, color: '#60a5fa' }, { offset: 1, color: 'rgba(96, 165, 250, 0.1)' }]
          },
          borderRadius: [4, 4, 0, 0]
        },
        label: {
          show: true, position: 'top', color: '#60a5fa', fontSize: 9,
          formatter: params => params.value > 0 ? params.value : ''
        }
      },
      // High-risk rainfall scatter
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
