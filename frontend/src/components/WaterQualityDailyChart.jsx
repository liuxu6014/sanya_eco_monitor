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

export default function WaterQualityDailyChart({ data }) {
  const td = data?.data || []
  if (td.length === 0) return <Empty />

  const legendSelected = {
    高锰酸盐: true,
    总氮: true,
    氨氮: true,
    总磷: true,
  }

  const option = {
    backgroundColor: 'transparent',
    animation: false,
    grid: { top: 48, bottom: 26, left: 40, right: 66, containLabel: true },
    tooltip: { ...TOOLTIP, trigger: 'axis' },
    legend: {
      top: 0,
      left: 'center',
      textStyle: { color: '#b0d8f0', fontSize: 11 },
      icon: 'circle',
      itemGap: 12,
      selected: legendSelected,
    },
    xAxis: {
      type: 'category',
      data: td.map((d) => d.date.slice(5)),
      axisLabel: { ...AXIS_LABEL, interval: 'auto', rotate: 20 },
      axisLine: { lineStyle: { color: 'rgba(56, 189, 248, 0.4)' } },
      axisTick: { show: false },
      splitLine: { show: false },
      boundaryGap: true,
    },
    yAxis: [
      {
        type: 'value',
        position: 'left',
        scale: true,
        name: '高锰酸盐 / 总氮 (mg/L)',
        nameLocation: 'end',
        nameGap: 10,
        nameRotate: 0,
        nameTextStyle: { color: '#38bdf8', fontSize: 10, align: 'left' },
        axisLine: { show: true, lineStyle: { color: '#38bdf8' } },
        axisTick: { show: true },
        axisLabel: { ...AXIS_LABEL, color: '#38bdf8', margin: 8 },
        splitLine: SPLIT_LINE,
      },
      {
        type: 'value',
        position: 'right',
        offset: 0,
        scale: true,
        name: '氨氮 / 总磷 (mg/L)',
        nameLocation: 'end',
        nameGap: 10,
        nameRotate: 0,
        nameTextStyle: { color: '#fbbf24', fontSize: 10, align: 'right' },
        axisLine: { show: true, lineStyle: { color: '#fbbf24' } },
        axisTick: { show: true },
        axisLabel: { ...AXIS_LABEL, color: '#fbbf24', margin: 10 },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '高锰酸盐',
        type: 'bar',
        barWidth: '32%',
        yAxisIndex: 0,
        data: td.map((d) => d.permanganate),
        itemStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: '#38bdf8' },
              { offset: 1, color: 'rgba(56, 189, 248, 0.08)' },
            ],
          },
          borderRadius: [4, 4, 0, 0],
        },
        tooltip: { valueFormatter: (v) => (v != null ? `${v} mg/L` : '—') },
      },
      {
        name: '总氮',
        type: 'line',
        smooth: true,
        yAxisIndex: 0,
        data: td.map((d) => d.tn),
        lineStyle: { color: '#a855f7', width: 2 },
        itemStyle: { color: '#a855f7' },
        showSymbol: false,
        tooltip: { valueFormatter: (v) => (v != null ? `${v} mg/L` : '—') },
      },
      {
        name: '氨氮',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: td.map((d) => d.nh4n),
        lineStyle: { color: '#fbbf24', width: 2 },
        itemStyle: { color: '#fbbf24' },
        showSymbol: false,
        tooltip: { valueFormatter: (v) => (v != null ? `${v} mg/L` : '—') },
      },
      {
        name: '总磷',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: td.map((d) => d.tp),
        lineStyle: { color: '#f87171', width: 2, type: 'dashed' },
        itemStyle: { color: '#f87171' },
        showSymbol: false,
        tooltip: { valueFormatter: (v) => (v != null ? `${v} mg/L` : '—') },
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
