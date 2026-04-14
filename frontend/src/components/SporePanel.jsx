import React, { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import dayjs from 'dayjs'
import s from './SporePanel.module.css'

export default function SporePanel({ latest, trend }) {
  const rec = latest?.data || {}
  const td  = trend?.data || []
  
  const sporeItems = Object.entries(rec.spore_data || {})
    .sort((a,b) => b[1] - a[1])
    .slice(0, 3)
  const maxSpore = Math.max(...sporeItems.map(i => i[1]), 1)

  const chartOpt = useMemo(() => {
    const dates = td.map(d => d.date.split('-').slice(1).join('/'))
    const totals = td.map(d => d.total)

    return {
      backgroundColor: 'transparent',
      grid: { top: 20, bottom: 20, left: 30, right: 10 },
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(2, 6, 23, 0.9)', borderColor: 'rgba(217, 70, 239, 0.5)', textStyle: { color: '#e2e8f0', fontSize: 10 } },
      xAxis: {
        type: 'category', data: dates,
        axisLabel: { color: '#94a3b8', fontSize: 9 }, axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } }
      },
      yAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)', type:'dashed' } }, axisLabel: { color: '#d946ef', fontSize: 9 } },
      series: [
        { 
          name: '捕获量', type: 'line', smooth: true, showSymbol: false, symbolSize: 6,
          itemStyle: { color: '#d946ef' }, 
          lineStyle: { width: 2, shadowColor: 'rgba(217, 70, 239, 0.8)', shadowBlur: 10 },
          areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(217, 70, 239, 0.6)' }, { offset: 1, color: 'transparent' }] } },
          data: totals 
        }
      ]
    }
  }, [td])

  return (
    <div className={s.panelWrapper}>
      <div className={s.topRow}>
        <div className={s.totalCard}>
          <div className={s.label}>今日孢子捕获总量</div>
          <div className={s.value}>{rec.total_count ?? '--'} <span className={s.unit}>个/m³</span></div>
          <div className={s.time}>近次更新: {rec.collection_time ? dayjs(rec.collection_time).format('MM-DD HH:mm') : '--'}</div>
        </div>
        
        <div className={s.speciesBox}>
          <div className={s.label}>主要病害类群</div>
          <div className={s.speciesList}>
            {sporeItems.length > 0 ? sporeItems.map(([name, cnt]) => {
              const pct = (cnt / maxSpore) * 100
              return (
                <div key={name} className={s.speciesRow}>
                  <div className={s.speciesInfo}>
                    <span className={s.speciesName}>{name}</span>
                    <span className={s.speciesCnt}>{cnt}</span>
                  </div>
                  <div className={s.barTrack}>
                    <div className={s.barFill} style={{ width: `${pct}%` }}></div>
                  </div>
                </div>
              )
            }) : <div className={s.emptyMsg}>当前暂无分类数据</div>}
          </div>
        </div>
      </div>

      <div className={s.chartBox}>
         <div className={s.label}>近7日捕获趋势动态</div>
         {td.length > 0 ? (
           <ReactECharts option={chartOpt} style={{height: '100%', minHeight: '80px'}} />
         ) : (
           <div className={s.emptyChart}>无历史分析数据</div>
         )}
      </div>
    </div>
  )
}
