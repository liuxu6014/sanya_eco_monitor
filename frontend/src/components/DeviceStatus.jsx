import dayjs from 'dayjs'
import ReactECharts from 'echarts-for-react'

const STATUS_MAP = {
  online:  { label:'在线', cls:'dot-green',  color:'var(--green)' },
  timeout: { label:'超时', cls:'dot-yellow', color:'var(--gold)' },
  offline: { label:'离线', cls:'dot-red',    color:'var(--red)' },
  pending: { label:'接入中', cls:'dot-gray', color:'var(--text-muted)' },
}

export default function DeviceStatus({ devices, logs }) {
  const list = devices?.data || []
  const online  = list.filter(d => d.status === 'online').length
  const pending = list.filter(d => d.status === 'pending').length
  const total   = list.length

  const donutOpt = {
    backgroundColor: 'transparent',
    series: [{
      type: 'pie', radius: ['55%','80%'], center: ['50%','50%'],
      data: [
        { name:'在线', value: online,        itemStyle:{ color:'var(--green)' } },
        { name:'接入中', value: pending,     itemStyle:{ color:'var(--text-muted)' } },
        { name:'其他', value: total - online - pending, itemStyle:{ color:'var(--red)' } },
      ],
      label: { show: false },
      emphasis: { scale: false },
    }],
    graphic: [{
      type: 'text', left: 'center', top: 'center',
      style: { text: `${online}/${total}`, fill: '#c8e0f4', fontSize: 13, fontWeight: 700, textAlign: 'center' },
    }],
  }

  return (
    <div style={{ height:'100%', display:'flex', flexDirection:'column', gap:4 }}>
      {/* Donut summary */}
      <div style={{ display:'flex', alignItems:'center', gap:8, flexShrink:0 }}>
        <ReactECharts option={donutOpt} style={{ width:80, height:80, flexShrink:0 }} opts={{ renderer:'canvas' }} />
        <div style={{ flex:1 }}>
          {[
            { label:'在线', count: online, color:'var(--green)' },
            { label:'接入中', count: pending, color:'var(--text-muted)' },
            { label:'总计', count: total, color:'var(--text-dim)' },
          ].map(it => (
            <div key={it.label} style={{ display:'flex', justifyContent:'space-between', padding:'2px 0' }}>
              <span style={{ fontSize:11, color:'var(--text-dim)' }}>{it.label}</span>
              <span style={{ fontSize:13, fontWeight:700, color:it.color }}>{it.count}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="divider" />

      {/* Device list */}
      <div style={{ flex:1, overflowY:'auto', minHeight:0 }}>
        {list.map(d => {
          const st = STATUS_MAP[d.status] || STATUS_MAP.offline
          return (
            <div key={d.code} style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'4px 0', borderBottom:'1px solid rgba(0,100,180,0.1)' }}>
              <div style={{ display:'flex', alignItems:'center', gap:7 }}>
                <span className={`dot ${st.cls}`} />
                <span style={{ fontSize:11, color:'var(--text)' }}>{d.name}</span>
              </div>
              <div style={{ textAlign:'right' }}>
                <div style={{ fontSize:11, fontWeight:600, color:st.color }}>{st.label}</div>
                {d.last_data && (
                  <div style={{ fontSize:9, color:'var(--text-muted)' }}>{dayjs(d.last_data).format('HH:mm')}</div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
