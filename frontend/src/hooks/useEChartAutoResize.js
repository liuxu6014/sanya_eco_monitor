import { useEffect, useRef } from 'react'

export function useEChartAutoResize(dependencies = []) {
  const chartRef = useRef(null)

  useEffect(() => {
    let frame = null

    const resize = () => {
      if (frame !== null) {
        cancelAnimationFrame(frame)
      }

      frame = requestAnimationFrame(() => {
        const instance = chartRef.current?.getEchartsInstance?.()
        instance?.resize()
      })
    }

    const chartElement = chartRef.current?.getEchartsInstance?.()?.getDom?.()
    const observedElement = chartElement?.parentElement || chartElement
    const observer = typeof ResizeObserver !== 'undefined' && observedElement
      ? new ResizeObserver(resize)
      : null

    if (observer) {
      observer.observe(observedElement)
      if (chartElement && chartElement !== observedElement) {
        observer.observe(chartElement)
      }
    }

    const timers = [0, 80, 260].map((delay) => window.setTimeout(resize, delay))
    window.addEventListener('resize', resize)

    return () => {
      if (frame !== null) {
        cancelAnimationFrame(frame)
      }
      timers.forEach((timer) => window.clearTimeout(timer))
      window.removeEventListener('resize', resize)
      observer?.disconnect()
    }
  }, dependencies)

  return chartRef
}
