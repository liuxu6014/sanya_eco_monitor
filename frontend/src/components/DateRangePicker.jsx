import { useEffect, useMemo, useRef, useState } from 'react'
import dayjs from 'dayjs'
import s from './maintenanceControls.module.css'

const WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日']
const PRESETS = [
  { label: '近7天', days: 7 },
  { label: '近30天', days: 30 },
  { label: '近90天', days: 90 },
]

export default function DateRangePicker({ start, end, onChange }) {
  const [open, setOpen] = useState(false)
  const [view, setView] = useState(() => dayjs(end || undefined).startOf('month'))
  const [anchor, setAnchor] = useState(null)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    const onDocClick = (e) => { if (ref.current && !ref.current.contains(e.target)) close() }
    const onEsc = (e) => { if (e.key === 'Escape') close() }
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onEsc)
    return () => {
      document.removeEventListener('mousedown', onDocClick)
      document.removeEventListener('keydown', onEsc)
    }
  }, [open])

  const close = () => { setOpen(false); setAnchor(null) }

  const cells = useMemo(() => {
    const monthStart = view.startOf('month')
    const lead = (monthStart.day() + 6) % 7 // 周一为一周起点
    const gridStart = monthStart.subtract(lead, 'day')
    return Array.from({ length: 42 }, (_, i) => gridStart.add(i, 'day'))
  }, [view])

  const startD = start ? dayjs(start) : null
  const endD = end ? dayjs(end) : null
  const today = dayjs()

  const applyPreset = (days) => {
    const e = dayjs()
    const sdt = e.subtract(days - 1, 'day')
    onChange?.(sdt.format('YYYY-MM-DD'), e.format('YYYY-MM-DD'))
    close()
  }

  const onDayClick = (day) => {
    if (!anchor) {
      setAnchor(day)
      return
    }
    let a = anchor
    let b = day
    if (b.isBefore(a, 'day')) [a, b] = [b, a]
    onChange?.(a.format('YYYY-MM-DD'), b.format('YYYY-MM-DD'))
    close()
  }

  const dayClass = (day) => {
    const classes = [s.day]
    if (day.month() !== view.month()) classes.push(s.dayOutside)
    if (day.isSame(today, 'day')) classes.push(s.dayToday)
    if (anchor && day.isSame(anchor, 'day')) classes.push(s.dayEndpoint)
    if (!anchor && startD && endD) {
      const inRange = !day.isBefore(startD, 'day') && !day.isAfter(endD, 'day')
      if (inRange) classes.push(s.dayInRange)
      if (day.isSame(startD, 'day') || day.isSame(endD, 'day')) classes.push(s.dayEndpoint)
    }
    return classes.join(' ')
  }

  const label = start && end ? `${start} ~ ${end}` : '选择日期范围'

  return (
    <div className={s.control} ref={ref}>
      <button type="button" className={`${s.trigger} ${open ? s.triggerOpen : ''}`} onClick={() => setOpen((v) => !v)}>
        <span className={s.calIcon}>🗓</span>
        <span className={s.triggerText}>{label}</span>
        <span className={`${s.caret} ${open ? s.caretUp : ''}`}>▾</span>
      </button>

      {open ? (
        <div className={s.calPop}>
          <div className={s.presets}>
            {PRESETS.map((p) => (
              <button key={p.days} type="button" className={s.preset} onClick={() => applyPreset(p.days)}>
                {p.label}
              </button>
            ))}
            <button
              type="button"
              className={s.preset}
              onClick={() => {
                const e = dayjs()
                onChange?.(e.startOf('month').format('YYYY-MM-DD'), e.format('YYYY-MM-DD'))
                close()
              }}
            >
              本月
            </button>
          </div>

          <div className={s.calHead}>
            <button type="button" className={s.navBtn} onClick={() => setView(view.subtract(1, 'month'))}>‹</button>
            <span className={s.calTitle}>{view.format('YYYY年M月')}</span>
            <button type="button" className={s.navBtn} onClick={() => setView(view.add(1, 'month'))}>›</button>
          </div>

          <div className={s.weekRow}>
            {WEEKDAYS.map((w) => <span key={w} className={s.weekday}>{w}</span>)}
          </div>

          <div className={s.grid}>
            {cells.map((day) => (
              <button
                key={day.format('YYYY-MM-DD')}
                type="button"
                className={dayClass(day)}
                onClick={() => onDayClick(day)}
              >
                {day.date()}
              </button>
            ))}
          </div>

          <div className={s.calFoot}>
            <span className={s.hint}>{anchor ? '请选择结束日期' : '点击选择起止日期'}</span>
            <button type="button" className={s.todayBtn} onClick={() => setView(dayjs().startOf('month'))}>回到本月</button>
          </div>
        </div>
      ) : null}
    </div>
  )
}
