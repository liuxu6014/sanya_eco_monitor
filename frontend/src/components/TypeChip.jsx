import { TYPE_COLORS, TYPE_LABELS } from '../utils/deviceTypes.js'
import s from './maintenanceControls.module.css'

export default function TypeChip({ type }) {
  const color = TYPE_COLORS[type] || '#94a3b8'
  return (
    <span
      className={s.chip}
      style={{ color, borderColor: `${color}66`, background: `${color}1f` }}
    >
      {TYPE_LABELS[type] || type}
    </span>
  )
}
