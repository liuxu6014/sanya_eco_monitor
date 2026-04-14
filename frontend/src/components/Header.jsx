import { useEffect, useState } from 'react'
import dayjs from 'dayjs'
import s from './Header.module.css'

export default function Header({ onTriggerCollect, activeTab, onTabChange }) {
  const [time, setTime] = useState(dayjs())

  useEffect(() => {
    const timer = setInterval(() => setTime(dayjs()), 1000)
    return () => clearInterval(timer)
  }, [])

  const weekDay = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][time.day()]

  return (
    <header className={s.header}>
      <div className={s.scanLine} />

      <div className={s.side}>
        <div className={s.location}>
          <span className={s.locDot} />
          三亚市·天涯区
        </div>
        <div className={s.date}>
          {time.format('YYYY年M月D日')} {weekDay}
        </div>
      </div>

      <div className={s.center}>
        <div className={s.decoLeft}>
          <span className={s.arrowA} />
          <span className={s.arrowB} />
          <span className={s.hLine} />
        </div>
        <div className={s.titleBlock}>
          <div className={s.title}>三亚市天涯区橡胶林近自然化改造和农田提升监测平台</div>
          <div className={s.subtitle}>SANYA · TIANYA RUBBER FOREST & FARMLAND IMPROVEMENT MONITORING PLATFORM</div>
        </div>
        <div className={s.decoRight}>
          <span className={s.hLine} />
          <span className={s.arrowB} style={{ transform: 'scaleX(-1)' }} />
          <span className={s.arrowA} style={{ transform: 'scaleX(-1)' }} />
        </div>
      </div>

      <div className={s.side} style={{ alignItems: 'flex-end', gap: 6 }}>
        <div className={s.clock}>{time.format('HH:mm:ss')}</div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            className={s.btn}
            style={activeTab === 'overview' ? { background: 'rgba(0,212,255,0.25)', borderColor: 'rgba(0,212,255,0.7)' } : {}}
            onClick={() => onTabChange('overview')}
          >
            总览
          </button>
          <button
            className={s.btn}
            style={activeTab === 'analytics' ? { background: 'rgba(0,212,255,0.25)', borderColor: 'rgba(0,212,255,0.7)' } : {}}
            onClick={() => onTabChange('analytics')}
          >
            数据分析
          </button>
          <button
            className={s.btn}
            style={activeTab === 'reports' ? { background: 'rgba(0,212,255,0.25)', borderColor: 'rgba(0,212,255,0.7)' } : {}}
            onClick={() => onTabChange('reports')}
          >
            报告管理
          </button>
          <button className={s.btn} onClick={onTriggerCollect}>
            刷新
          </button>
        </div>
      </div>
    </header>
  )
}
