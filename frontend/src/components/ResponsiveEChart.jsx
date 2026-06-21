import { useEffect, useRef, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import { useEChartAutoResize } from '../hooks/useEChartAutoResize.js'

export default function ResponsiveEChart({ resizeDeps = [], style, ...props }) {
  const hostRef = useRef(null)
  const [ready, setReady] = useState(false)
  const chartRef = useEChartAutoResize([ready, ...resizeDeps])

  useEffect(() => {
    let frame = null

    const measure = () => {
      if (frame !== null) {
        cancelAnimationFrame(frame)
      }

      frame = requestAnimationFrame(() => {
        const host = hostRef.current
        const nextReady = Boolean(host && host.clientWidth > 0 && host.clientHeight > 0)
        setReady((current) => (current === nextReady ? current : nextReady))
      })
    }

    measure()

    const observer = typeof ResizeObserver !== 'undefined' && hostRef.current
      ? new ResizeObserver(measure)
      : null

    if (observer && hostRef.current) {
      observer.observe(hostRef.current)
    }

    const timers = [0, 80, 260].map((delay) => window.setTimeout(measure, delay))
    window.addEventListener('resize', measure)

    return () => {
      if (frame !== null) {
        cancelAnimationFrame(frame)
      }
      timers.forEach((timer) => window.clearTimeout(timer))
      window.removeEventListener('resize', measure)
      observer?.disconnect()
    }
  }, [])

  return (
    <div ref={hostRef} style={{ width: '100%', height: '100%', ...style }}>
      {ready ? (
        <ReactECharts
          ref={chartRef}
          {...props}
          style={{ width: '100%', height: '100%' }}
        />
      ) : null}
    </div>
  )
}
