import ReactECharts from 'echarts-for-react'

const COLORS = ['#ff7043','#ffaa00','#00d4ff','#00ff9d','#a855f7','#ff4757']
const TOOLTIP = { backgroundColor:'#03112e', borderColor:'rgba(0,180,255,0.35)', textStyle:{color:'#c8e0f4',fontSize:11} }

export default function InsectPanel({ latest, trend, species }) {
  const rec = latest?.data
  const td  = trend?.data  || []
  const sp  = species?.data || []

  const barOpt = {
    backgroundColor: 'transparent',
    grid: { top:14, bottom:22, left:42, right:8 },
    tooltip: { ...TOOLTIP, trigger:'axis' },
    xAxis: { type:'category', data:td.map(d=>d.date), axisLabel:{color:'#8fc8e8',fontSize:10,hideOverlap:true}, axisLine:{lineStyle:{color:'#1a3a55'}}, splitLine:{show:false} },
    yAxis: { type:'value', minInterval:1, splitNumber:4, axisLabel:{color:'#8fc8e8',fontSize:9,hideOverlap:true}, splitLine:{lineStyle:{color:'rgba(0,120,200,0.15)'}}, axisLine:{show:false} },
    series: [{
      type:'bar', data:td.map(d=>d.total), barMaxWidth:16,
      itemStyle: { color:{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{offset:0,color:'rgba(255,112,67,.95)'},{offset:1,color:'rgba(255,112,67,.2)'}]}, borderRadius:[3,3,0,0] },
    }],
  }

  const pieOpt = {
    backgroundColor: 'transparent',
    tooltip: { ...TOOLTIP, trigger:'item', formatter:'{b}: {c}只 ({d}%)' },
    series: [{
      type:'pie', radius:['42%','68%'], center:['50%','50%'],
      data: sp.slice(0,6).map((d,i) => ({ name:d.name, value:d.value, itemStyle:{color:COLORS[i]} })),
      label: { formatter:'{b}\n{c}', fontSize:10, color:'#7a9fb8' },
      labelLine: { lineStyle:{ color:'#2a4f6a' } },
      emphasis: { itemStyle:{ shadowBlur:10, shadowColor:'rgba(0,0,0,0.5)' } },
    }],
  }

  return (
    <div style={{ height:'100%', display:'flex', flexDirection:'column', gap:4 }}>

      {/* Latest capture image */}
      {rec?.image_url && (
        <div style={{ 
          flexShrink:0, 
          border:'1px solid var(--border)', 
          borderRadius: '8px',
          overflow:'hidden', 
          height:80,
          position: 'relative',
          background: 'rgba(0,0,0,0.3)'
        }}>
          <img 
            src={rec.image_url} 
            alt="Insect capture" 
            style={{ 
              width:'100%', 
              height:'100%', 
              objectFit:'cover', 
              display:'block',
              transition: 'transform 0.5s ease'
            }} 
            onMouseOver={e => e.currentTarget.style.transform = 'scale(1.05)'}
            onMouseOut={e => e.currentTarget.style.transform = 'scale(1)'}
            onError={e=>{e.target.style.display='none'}} 
          />
          <div style={{ 
            position: 'absolute', top: 4, right: 4, 
            background: 'rgba(0,0,0,0.6)', padding: '2px 6px', 
            borderRadius: 4, fontSize: 9, color: '#fff',
            backdropFilter: 'blur(4px)', border: '1px solid rgba(255,255,255,0.1)'
          }}>实时图像</div>
        </div>
      )}

      {/* 7-day bar */}
      <div style={{ flexShrink:0, height:85 }}>
        <div style={{ fontSize:10, color:'var(--text-muted)' }}>7日捕获趋势（只）</div>
        {td.length > 0
          ? <ReactECharts option={barOpt} style={{ height:76 }} opts={{ renderer:'canvas' }} />
          : <Empty h={76} />}
      </div>

      <div className="divider" />

      {/* Species pie */}
      <div style={{ flex:1, minHeight:0, display:'flex', flexDirection:'column' }}>
        <div style={{ fontSize:10, color:'var(--text-muted)', flexShrink:0 }}>虫种构成分析</div>
        {sp.length > 0
          ? <div style={{ flex: 1, position: 'relative' }}>
              <ReactECharts option={pieOpt} style={{ position:'absolute', top:0, left:0, width:'100%', height:'100%' }} opts={{ renderer:'canvas' }} />
            </div>
          : <Empty />}
      </div>
    </div>
  )
}

function Empty({ h }) {
  return <div style={{ height:h||'100%', display:'flex', alignItems:'center', justifyContent:'center', color:'var(--text-muted)', fontSize:11 }}>暂无数据</div>
}
