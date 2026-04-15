import React, { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import dayjs from 'dayjs'
import s from './SporePanel.module.css'

export default function SporePanel({ latest, trend }) {
  const rec = latest?.data || {}
  const td  = trend?.data || []
  
  const sporeItems = Object.entries(rec.spore_data || {})
    .sort((a,b) => b[1] - a[1])
    .slice(0, 2) // Show fewer items to save space
  const maxSpore = Math.max(...sporeItems.map(i => i[1]), 1)

  const chartOpt = useMemo(() => {
    const dates = td.map(d => d.date.split('-').slice(1).join('/'))
    const totals = td.map(d => d.total)

    return {
      backgroundColor: 'transparent',
      grid: { top: 10, bottom: 20, left: 25, right: 5 },
      xAxis: {
        type: 'category', 
        data: dates,
        axisLabel: { color: '#64748b', fontSize: 8 }, 
        axisLine: { show: false }
      },
      yAxis: { 
        type: 'value', 
        minInterval: 1,
        interval: 1,
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.02)' } }, 
        axisLabel: { 
          color: '#d946ef', 
          fontSize: 8
        } 
      },
      series: [
        { 
          type: 'line', 
          smooth: true, 
          showSymbol: false,
          itemStyle: { color: '#d946ef' }, 
          lineStyle: { width: 2 },
          areaStyle: { 
            color: { 
              type: 'linear', x: 0, y: 0, x2: 0, y2: 1, 
              colorStops: [{ offset: 0, color: 'rgba(217, 70, 239, 0.2)' }, { offset: 1, color: 'transparent' }] 
            } 
          },
          data: totals 
        }
      ]
    }
  }, [td])

  return (
    <div className={s.panelWrapper}>
      <div className={s.mainRow}>
        <div className={s.metricCol}>
          <div className={s.totalCard}>
            <div>
              <div className={s.label}>今日总量</div>
              <div className={s.status}>
                 <span className={s.dot} /> 实时监测
              </div>
            </div>
            <div className={s.value}>{rec.total_count ?? '0'}</div>
          </div>
          
          {sporeItems.length > 0 && (
            <div className={s.listCard}>
              {sporeItems.map(([name, cnt]) => {
                const pct = (cnt / maxSpore) * 100
                return (
                  <div key={name} className={s.row}>
                    <div className={s.info}><span className={s.n}>{name}</span><span className={s.c}>{cnt}</span></div>
                    <div className={s.track}><div className={s.fill} style={{ width: `${pct}%` }} /></div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <div className={s.imageCard}>
           <div className={s.imgBox}>
             {rec.image_url ? (
               <img src={rec.image_url} alt="Spore" className={s.pImg} />
             ) : (
               <div className={s.pPlaceholder}>
                 <div className={s.scan} />
                 <span>影像极低延迟传输中...</span>
               </div>
             )}
           </div>
        </div>
      </div>

      <div className={s.chartBox}>
         <div className={s.chartHeader}>
           浓度趋势 (近7日动态)
         </div>
         <div className={s.chart}>
           {td.length > 0 ? (
             <ReactECharts option={chartOpt} style={{height: '100%'}} />
           ) : (
             <div className={s.emptyChart}>无趋势数据</div>
           )}
         </div>
      </div>
    </div>
  )
}
