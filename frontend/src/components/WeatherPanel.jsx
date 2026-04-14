import ReactECharts from 'echarts-for-react'
import dayjs from 'dayjs'

const TOOLTIP = { backgroundColor: '#03112e', borderColor: 'rgba(0,180,255,0.35)', textStyle: { color: '#c8e0f4', fontSize: 11 } }
const AXIS_LABEL = { color: '#8fc8e8', fontSize: 10 }
const SPLIT_LINE = { lineStyle: { color: 'rgba(0,120,200,0.1)' } }

function GaugeMini({ value, max, color, label }) {
  return (
    <ReactECharts
      style={{ height: 65, width: '100%' }}
      opts={{ renderer: 'canvas' }}
      option={{
        backgroundColor: 'transparent',
        series: [{
          type: 'gauge', radius: '98%',
          startAngle: 210, endAngle: -30, min: 0, max,
          progress: { show: true, width: 4, itemStyle: { color } },
          axisLine: { lineStyle: { width: 4, color: [[1, 'rgba(255,255,255,0.05)']] } },
          axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false },
          pointer: { show: false },
          detail: { valueAnimation: true, formatter: value != null ? `{value}` : '—', color: '#e0f2fe', fontSize: 13, fontWeight: 800, offsetCenter: [0, '15%'] },
          title: { offsetCenter: [0, '75%'], color: '#7dd3fc', fontSize: 9, fontWeight: 500 },
          data: [{ value: value ?? 0, name: label }],
        }],
      }}
    />
  )
}

export default function WeatherPanel({ weather, trend }) {
  const w = weather?.data
  const td = trend?.data || []

  const trendOpt = {
    backgroundColor: 'transparent',
    grid: { top: 12, bottom: 22, left: 35, right: 35 },
    tooltip: { ...TOOLTIP, trigger: 'axis' },
    xAxis: { type: 'category', data: td.map(d => dayjs(d.time).format('HH:mm')), axisLabel: { ...AXIS_LABEL, hideOverlap: true, interval: 'auto' }, axisLine: { lineStyle: { color: 'rgba(56, 189, 248, 0.2)' } }, splitLine: { show: false } },
    yAxis: [
      { type: 'value', scale: true, splitNumber: 3, axisLabel: { color: '#ff7043', fontSize: 9, formatter: '{value}°', hideOverlap: true }, splitLine: SPLIT_LINE, axisLine: { show: false } },
      { type: 'value', scale: true, splitNumber: 3, axisLabel: { color: '#00d4ff', fontSize: 9, formatter: '{value}%', hideOverlap: true }, splitLine: { show: false }, axisLine: { show: false } },
    ],
    series: [
      { name: '温度°C', type: 'line', smooth: true, yAxisIndex: 0, data: td.map(d => d.temperature), showSymbol: false,
        itemStyle: { color: '#ff7043' },
        lineStyle: { color: '#ff7043', width: 2, shadowColor: 'rgba(255,112,67,0.4)', shadowBlur: 8 },
        areaStyle: { color: { type:'linear',x:0,y:0,x2:0,y2:1, colorStops:[{offset:0,color:'rgba(255,112,67,0.25)'},{offset:1,color:'rgba(255,112,67,0)'}] } } },
      { name: '湿度%', type: 'line', smooth: true, yAxisIndex: 1, data: td.map(d => d.humidity), showSymbol: false,
        itemStyle: { color: '#00d4ff' },
        lineStyle: { color: '#00d4ff', width: 2, shadowColor: 'rgba(0,212,255,0.4)', shadowBlur: 8 },
        areaStyle: { color: { type:'linear',x:0,y:0,x2:0,y2:1, colorStops:[{offset:0,color:'rgba(0,212,255,0.15)'},{offset:1,color:'rgba(0,212,255,0)'}] } } },
    ],
  }

  return (
    <div style={{ height:'100%', display:'flex', flexDirection:'column', gap: 2 }}>
      {/* Top 3 gauges */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', flexShrink: 0, gap: 4 }}>
        <GaugeMini value={w?.temperature} max={50}  color="#ff7043" label="温度°C" />
        <GaugeMini value={w?.humidity}    max={100} color="#00d4ff" label="湿度%" />
        <GaugeMini value={w?.wind_speed}  max={30}  color="#00ff9d" label="风速" />
      </div>

      {/* 4 compact metrics */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', flexShrink:0, columnGap: 12, rowGap: 2, padding: '2px 0' }}>
        {[
          { label:'风向', value: w?.wind_direction || '—', color: 'var(--text-dim)' },
          { label:'降雨', value: w?.rainfall ?? '0', unit:'mm', color: 'var(--text-dim)' },
          { label:'气压', value: w?.pressure ? Math.round(w.pressure) : '—', unit:'hPa', color: 'var(--text-dim)' },
          { label:'光照', value: w?.light ? Math.round(w.light) : '—', unit:'lux', color: 'var(--text-dim)' },
        ].map(e => (
          <div key={e.label} style={{ display:'flex', justifyContent:'space-between', alignItems:'baseline', padding:'2px 0', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
            <span style={{ fontSize:10, color:'#5a8ea8' }}>{e.label}</span>
            <span style={{ fontSize:11, fontWeight:700, color:'#b0d8f0' }}>{e.value}<span style={{ fontSize:9, fontWeight:400, marginLeft:2, color:'#4a7fa0' }}>{e.unit}</span></span>
          </div>
        ))}
      </div>

      <div style={{ flex: 1, display:'flex', flexDirection:'column', minHeight: 0, marginTop: 4 }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', flexShrink: 0, marginBottom: 4 }}>
          <div style={{ fontSize:9, color:'#4a7fa0', fontWeight: 600, letterSpacing: 0.5 }}>24H TREND ANALYTICS</div>
          <div style={{ display:'flex', gap: 10, fontSize: 8 }}>
             <span style={{ display:'flex', alignItems:'center', gap: 3, color: '#ff7043' }}><span style={{width:5,height:5,borderRadius:'50%',backgroundColor:'#ff7043',boxShadow:'0 0 5px #ff7043'}}></span>TEMP</span>
             <span style={{ display:'flex', alignItems:'center', gap: 3, color: '#00d4ff' }}><span style={{width:5,height:5,borderRadius:'50%',backgroundColor:'#00d4ff',boxShadow:'0 0 5px #00d4ff'}}></span>HUM</span>
          </div>
        </div>
        {td.length > 0
          ? <div style={{ flex: 1, position: 'relative' }}>
              <ReactECharts option={trendOpt} style={{ position:'absolute', top:0, left:0, width:'100%', height:'100%' }} opts={{ renderer:'canvas' }} />
            </div>
          : <Empty />}
      </div>
    </div>
  )
}

function Empty() {
  return <div style={{ flex:1, display:'flex', alignItems:'center', justifyContent:'center', color:'var(--text-muted)', fontSize:11 }}>暂无数据</div>
}
