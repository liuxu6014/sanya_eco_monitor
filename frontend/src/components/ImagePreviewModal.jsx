import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import s from './ImagePreviewModal.module.css'

export default function ImagePreviewModal({ open, src, alt, onClose }) {
  useEffect(() => {
    if (!open) return undefined

    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        onClose?.()
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

  if (!open || !src) return null

  return createPortal(
    <div className={s.overlay} onClick={onClose}>
      <div className={s.dialog} onClick={(event) => event.stopPropagation()}>
        <button type="button" className={s.close} onClick={onClose} aria-label="关闭预览">
          ×
        </button>
        <img src={src} alt={alt || 'preview'} className={s.image} />
      </div>
    </div>,
    document.body
  )
}
