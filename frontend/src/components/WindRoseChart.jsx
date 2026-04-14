import ReactECharts from 'echarts-for-react'

export default function WindRoseChart({ data }) {
  const rows = data?.data || []
  if (rows.length === 0) return <Empty />

  const dirs = rows.map(r => r.direction)
  const freqs = rows.map(r => r.frequency)
  const speeds = rows.map(r => r.avg_speed)

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(3, 17, 46, 0.9)',
      borderColor: '#38bdf8',
      textStyle: { color: '#fff' },
      formatter: params => {
        const idx = params[0].dataIndex
        return `<div style="padding:4px">
            <b style="color:#38bdf8">${dirs[idx]}风向</b><br/>
            频率: <span style="float:right;margin-left:15px">${freqs[idx]}%</span><br/>
            平均风速: <span style="float:right;margin-left:15px">${speeds[idx]} m/s</span>
        </div>`
      }
    },
    angleAxis: {
      type: 'category',
      data: dirs,
      boundaryGap: false,
      axisLabel: { color: '#64748b', fontSize: 11, fontWeight: 'bold' },
      axisLine: { lineStyle: { color: 'rgba(99, 102, 241, 0.2)' } },
      splitLine: { lineStyle: { color: 'rgba(99, 102, 241, 0.1)' } }
    },
    radiusAxis: {
      axisLabel: { show: false },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'rgba(99, 102, 241, 0.1)', type: 'dashed' } }
    },
    polar: { radius: '75%' },
    series: [
      {
        type: 'bar',
        data: freqs,
        coordinateSystem: 'polar',
        name: '出现频率',
        stack: 'a',
        itemStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [{ offset: 0, color: '#38bdf8' }, { offset: 1, color: '#818cf8' }]
          },
          shadowBlur: 10, shadowColor: 'rgba(56, 189, 248, 0.3)'
        }
      },
      {
        type: 'bar',
        data: speeds.map(s => s * 2), // Scale for visualization
        coordinateSystem: 'polar',
        name: '平均风速风力表现',
        stack: 'a',
        itemStyle: { color: 'rgba(255, 255, 255, 0.05)', borderColor: 'rgba(255, 255, 255, 0.1)', borderWidth: 1 }
      }
    ]
  }

  return <ReactECharts option={option} style={{ height: '100%' }} opts={{ renderer: 'canvas' }} />
}

function Empty() {
  return <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#475569', fontSize: 12 }}>暂无数据</div>
}
