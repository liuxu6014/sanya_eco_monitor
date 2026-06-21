import { useEffect, useRef, useState } from 'react'
import TypeChip from './TypeChip.jsx'
import { deviceLabel } from '../utils/deviceTypes.js'
import s from './maintenanceControls.module.css'

export default function DeviceSelect({ devices = [], value = '', onChange }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    const onDocClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    const onEsc = (e) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onEsc)
    return () => {
      document.removeEventListener('mousedown', onDocClick)
      document.removeEventListener('keydown', onEsc)
    }
  }, [open])

  const current = devices.find((d) => d.key === value)

  const pick = (key) => {
    onChange?.(key)
    setOpen(false)
  }

  return (
    <div className={s.control} ref={ref}>
      <button type="button" className={`${s.trigger} ${open ? s.triggerOpen : ''}`} onClick={() => setOpen((v) => !v)}>
        <span className={s.triggerContent}>
          {current ? <TypeChip type={current.type} /> : null}
          <span className={s.triggerText}>{current ? current.name : '全部设备'}</span>
        </span>
        <span className={`${s.caret} ${open ? s.caretUp : ''}`}>▾</span>
      </button>

      {open ? (
        <div className={s.popover} role="listbox">
          <button
            type="button"
            className={`${s.option} ${value === '' ? s.optionActive : ''}`}
            onClick={() => pick('')}
          >
            <span className={s.allDot} />
            <span>全部设备</span>
          </button>
          {devices.map((d) => (
            <button
              key={d.key}
              type="button"
              className={`${s.option} ${value === d.key ? s.optionActive : ''}`}
              onClick={() => pick(d.key)}
            >
              <TypeChip type={d.type} />
              <span>{d.name}</span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}

export { deviceLabel }
