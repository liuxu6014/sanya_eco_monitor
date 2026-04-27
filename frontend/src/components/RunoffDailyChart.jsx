import ReactECharts from 'echarts-for-react'

const TOOLTIP = {
  backgroundColor: 'rgba(3, 17, 46, 0.95)',
  borderColor: 'rgba(56, 189, 248, 0.5)',
  borderWidth: 1,
  textStyle: { color: '#e0f0ff', fontSize: 11 },
  padding: [6, 8],
  confine: true,
}

const AXIS_LABEL = { color: '#8fc8e8', fontSize: 11, fontFamily: 'monospace' }
const SPLIT_LINE = {
  lineStyle: { color: 'rgba(56, 189, 248, 0.1)', type: 'dotted' },
}

export default function RunoffDailyChart({ data }) {
  const td = data?.data || []
  if (td.length === 0) return <Empty />

  const legendSelected = {
    当日降雨量: true,
    当日径流量: true,
    平均流量: true,
    瞬时流速: true,
    累计流量: true,
    平均含沙量: true,
    水位监测: true,
    液位压力: true,
  }

  const option = {
    backgroundColor: 'transparent',
    animation: false,
    grid: { top: 62, bottom: 28, left: 48, right: 48, containLabel: true },
    tooltip: {
      ...TOOLTIP,
      trigger: 'axis',
      axisPointer: {
        type: 'line',
        lineStyle: {
          color: 'rgba(56, 189, 248, 0.5)',
          width: 2,
          type: 'dashed',
        },
      },
    },
    legend: {
      top: 0,
      left: 'center',
      textStyle: { color: '#b0d8f0', fontSize: 10 },
      icon: 'circle',
      itemGap: 10,
      selected: legendSelected,
    },
    xAxis: {
      type: 'category',
      data: td.map((d) => d.date.slice(5)),
      axisLabel: { ...AXIS_LABEL, interval: 'auto', rotate: 20 },
      axisLine: { lineStyle: { color: 'rgba(56, 189, 248, 0.4)' } },
      axisTick: { show: false },
      splitLine: { show: false },
      boundaryGap: false,
    },
    yAxis: [
      {
        type: 'value',
        name: '流速 / 流量 / 径流 (m/s, m³/s, m³)',
        nameLocation: 'end',
        nameGap: 10,
        nameRotate: 0,
        nameTextStyle: { color: '#4ade80', fontSize: 10, align: 'left' },
        axisLine: { show: true, lineStyle: { color: '#4ade80' } },
        axisLabel: { ...AXIS_LABEL, color: '#4ade80' },
        splitLine: SPLIT_LINE,
      },
      {
        type: 'value',
        name: '水位 / 压力 / 含沙量 (m, kPa, kg/L)',
        nameLocation: 'end',
        nameGap: 10,
        nameRotate: 0,
        nameTextStyle: { color: '#facc15', fontSize: 10, align: 'right' },
        axisLine: { show: true, lineStyle: { color: '#facc15' } },
        axisLabel: { ...AXIS_LABEL, color: '#facc15' },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '当日降雨量',
        type: 'bar',
        yAxisIndex: 1,
        z: 2,
        data: td.map((d) => d.rainfall),
        barMaxWidth: 15,
        itemStyle: {
          color: 'rgba(56, 189, 248, 0.3)',
          borderColor: 'rgba(56, 189, 248, 0.75)',
          borderWidth: 1,
          borderRadius: [4, 4, 0, 0],
        },
        tooltip: { valueFormatter: (v) => (v != null ? `${v} mm` : '—') },
      },
      {
        name: '当日径流量',
        type: 'bar',
        yAxisIndex: 0,
        z: 2,
        data: td.map((d) => d.runoff),
        barMaxWidth: 15,
        itemStyle: {
          color: 'rgba(74, 222, 128, 0.34)',
          borderColor: 'rgba(74, 222, 128, 0.8)',
          borderWidth: 1,
          borderRadius: [4, 4, 0, 0],
        },
        tooltip: { valueFormatter: (v) => (v != null ? `${v} m³` : '—') },
      },
      {
        name: '平均流量',
        type: 'line',
        smooth: true,
        yAxisIndex: 0,
        data: td.map((d) => d.flow),
        lineStyle: { color: '#4ade80', width: 2 },
        itemStyle: { color: '#4ade80' },
        showSymbol: false,
        tooltip: { valueFormatter: (v) => (v != null ? `${v} m³/s` : '—') },
      },
      {
        name: '瞬时流速',
        type: 'line',
        smooth: true,
        yAxisIndex: 0,
        data: td.map((d) => d.flow_speed),
        lineStyle: { color: '#2dd4bf', width: 1.5, type: 'dashed' },
        itemStyle: { color: '#2dd4bf' },
        showSymbol: false,
        tooltip: { valueFormatter: (v) => (v != null ? `${v} m/s` : '—') },
      },
      {
        name: '累计流量',
        type: 'line',
        smooth: true,
        yAxisIndex: 0,
        data: td.map((d) => d.total_flow),
        lineStyle: { color: '#38bdf8', width: 2 },
        itemStyle: { color: '#38bdf8' },
        showSymbol: false,
        tooltip: { valueFormatter: (v) => (v != null ? `${v} m³` : '—') },
      },
      {
        name: '平均含沙量',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: td.map((d) => d.sand),
        lineStyle: { color: '#facc15', width: 2 },
        itemStyle: { color: '#facc15' },
        showSymbol: false,
        tooltip: { valueFormatter: (v) => (v != null ? `${v} kg/L` : '—') },
      },
      {
        name: '水位监测',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: td.map((d) => d.water_level),
        lineStyle: { color: '#fb923c', width: 2 },
        itemStyle: { color: '#fb923c' },
        showSymbol: false,
        tooltip: { valueFormatter: (v) => (v != null ? `${v} m` : '—') },
      },
      {
        name: '液位压力',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: td.map((d) => d.liquid_pressure),
        lineStyle: { color: '#f87171', width: 1.5, type: 'dotted' },
        itemStyle: { color: '#f87171' },
        showSymbol: false,
        tooltip: { valueFormatter: (v) => (v != null ? `${v} kPa` : '—') },
      },
    ],
  }

  return (
    <ReactECharts
      option={option}
      style={{ width: '100%', height: '100%' }}
      notMerge
      opts={{ renderer: 'canvas' }}
    />
  )
}

function Empty() {
  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'rgba(255,255,255,0.3)',
        fontSize: 13,
        letterSpacing: 2,
      }}
    >
      暂无数据
    </div>
  )
}
