import { useCallback, useEffect } from 'react'
import { usePolling } from '../hooks/usePolling.js'
import { api } from '../utils/api.js'
import { clearRequestCache } from '../utils/requestCache.js'
import InsectHeatmapChart from './InsectHeatmapChart.jsx'
import CombinedTrendChart from './CombinedTrendChart.jsx'
import WaterQualityDailyChart from './WaterQualityDailyChart.jsx'
import RunoffDailyChart from './RunoffDailyChart.jsx'
import DeepInsightPanel from './DeepInsightPanel.jsx'
import AnalyticsSummaryBoard from './AnalyticsSummaryBoard.jsx'
import WeatherSupportPanel from './WeatherSupportPanel.jsx'
import s from './AnalyticsPage.module.css'

const IconDeep = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.29 7 12 12 20.71 7" /><line x1="12" y1="22" x2="12" y2="12" /></svg>
const IconRunoff = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 8v6a5 5 0 0 1-5 5H8a5 5 0 0 1-5-5V8" /><path d="M3 13l4-4 4 4 4-4 6 6" /></svg>
const IconWater = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#facc15" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-7.5c-.5 3.5-2 5.9-4 7.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z" /><path d="M9 15a3 3 0 0 0 3 3" /></svg>
const IconInsect = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2A4 4 0 0 0 8 6v2h8V6a4 4 0 0 0-4-4z" /><path d="M6 10h12v7a6 6 0 0 1-12 0v-7z" /><path d="M4 14l3-3" /><path d="M20 14l-3-3" /><path d="M4 18l3-3" /><path d="M20 18l-3-3" /><path d="M22 6l-3 3" /><path d="M2 6l3 3" /><path d="M12 22v-5" /></svg>
const IconHeat = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f97316" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" /></svg>

const POLL = 30_000

function ChartCard({ title, icon, extra, children, className = '', bodyClassName = '' }) {
  return (
    <section className={`${s.card} ${className}`.trim()}>
      <span className="panel-tr" />
      <span className="panel-bl" />

      <header className={s.cardHeader}>
        <div className={s.cardHeading}>
          {icon ? <span className={s.iconShell}>{icon}</span> : null}
          <div className={s.cardCopy}>
            <div className={s.cardTitle}>{title}</div>
          </div>
        </div>

        {extra ? <div className={s.cardBadge}>{extra}</div> : null}
      </header>

      <div className={`${s.cardBody} ${bodyClassName}`.trim()}>{children}</div>
    </section>
  )
}

function wrapData(data) {
  return { data }
}

const ECO_INDEX_CACHE_KEY = 'analytics-eco-index'
const GUIDELINE_CACHE_KEY = 'analytics-guideline-metrics'
const WQ_DAILY_CACHE_KEY = 'analytics-water-quality-daily'
const RUNOFF_DAILY_CACHE_KEY = 'analytics-runoff-daily'
const COMBINED_TREND_CACHE_KEY = 'analytics-combined-trend'
const HEATMAP_CACHE_KEY = 'analytics-insect-heatmap'

export default function AnalyticsPage({ active = true }) {
  const ecoIndexRequest = usePolling(
    useCallback(() => api.ecoIndex(), []),
    POLL,
    {
      cacheKey: ECO_INDEX_CACHE_KEY,
      persist: false,
      staleMs: POLL,
      enabled: active,
    },
  )

  const guidelineMetricsRequest = usePolling(
    useCallback(() => api.guidelineMetrics(), []),
    POLL,
    {
      cacheKey: GUIDELINE_CACHE_KEY,
      persist: false,
      staleMs: POLL,
      enabled: active,
    },
  )

  const waterQualityDailyRequest = usePolling(
    useCallback(() => api.waterQualityDaily(30), []),
    POLL,
    {
      cacheKey: WQ_DAILY_CACHE_KEY,
      persist: false,
      staleMs: POLL,
      enabled: active,
    },
  )

  const runoffDailyRequest = usePolling(
    useCallback(() => api.runoffDaily(30), []),
    POLL,
    {
      cacheKey: RUNOFF_DAILY_CACHE_KEY,
      persist: false,
      staleMs: POLL,
      enabled: active,
    },
  )

  const combinedTrendRequest = usePolling(
    useCallback(() => api.insectCombinedTrend(30), []),
    POLL,
    {
      cacheKey: COMBINED_TREND_CACHE_KEY,
      persist: false,
      staleMs: POLL,
      enabled: active,
    },
  )

  const insectHeatmapRequest = usePolling(
    useCallback(() => api.insectHeatmap(14), []),
    POLL,
    {
      cacheKey: HEATMAP_CACHE_KEY,
      persist: false,
      staleMs: POLL,
      enabled: active,
    },
  )

  const dashboardRequests = [
    ecoIndexRequest,
    guidelineMetricsRequest,
    waterQualityDailyRequest,
    runoffDailyRequest,
    combinedTrendRequest,
    insectHeatmapRequest,
  ]

  useEffect(() => {
    clearRequestCache('analysis-dashboard-runtime')
    clearRequestCache('analysis-dashboard')
  }, [])

  useEffect(() => {
    if (!active) {
      return undefined
    }

    const handleRefresh = () => {
      dashboardRequests.forEach((request) => {
        request.refetch().catch(() => {})
      })
    }

    window.addEventListener('app:refresh-data', handleRefresh)
    return () => window.removeEventListener('app:refresh-data', handleRefresh)
  }, [active, dashboardRequests])

  const ecoIndex = wrapData(ecoIndexRequest.data?.data || {})
  const guidelineMetrics = wrapData(guidelineMetricsRequest.data?.data || {})
  const wqDaily = wrapData(waterQualityDailyRequest.data?.data || [])
  const runoffDaily = wrapData(runoffDailyRequest.data?.data || [])
  const combinedTrend = wrapData(combinedTrendRequest.data?.data || [])
  const insectHeatmap = wrapData(insectHeatmapRequest.data?.data || {})

  return (
    <div className={s.page}>
      <div className={s.topGrid}>
        <ChartCard
          title="生态综合评估与趋势研判"
          icon={<IconDeep />}
          extra="综合判断"
          className={s.cardStrategic}
        >
          <DeepInsightPanel ecoIndex={ecoIndex} guidelineMetrics={guidelineMetrics} />
        </ChartCard>

        <ChartCard
          title="气象与水文支撑（外部接口）"
          icon={<IconWater />}
          extra="近30天历史气象"
          className={s.cardWeather}
        >
          <WeatherSupportPanel data={guidelineMetrics} />
        </ChartCard>
      </div>

      <div className={s.summaryGrid}>
        <ChartCard
          title="关键指标总览"
          icon={<IconDeep />}
          extra="统一口径"
          className={s.cardSummary}
        >
          <AnalyticsSummaryBoard ecoIndex={ecoIndex} guidelineMetrics={guidelineMetrics} />
        </ChartCard>
      </div>

      <div className={s.chartGrid}>
        <ChartCard
          title="近30天水质指标变化"
          icon={<IconWater />}
          extra="30天趋势"
          className={s.cardHalf}
          bodyClassName={s.chartBody}
        >
          <WaterQualityDailyChart data={wqDaily} />
        </ChartCard>

        <ChartCard
          title="近30天地表径流变化"
          icon={<IconRunoff />}
          extra="30天趋势"
          className={s.cardHalf}
          bodyClassName={s.chartBody}
        >
          <RunoffDailyChart data={runoffDaily} />
        </ChartCard>

        <ChartCard
          title="虫情趋势"
          icon={<IconInsect />}
          extra="30天趋势"
          className={s.cardHalf}
          bodyClassName={s.chartBody}
        >
          <CombinedTrendChart data={combinedTrend} />
        </ChartCard>

        <ChartCard
          title="虫种热度分布分析"
          icon={<IconHeat />}
          extra="14天热度"
          className={s.cardHalf}
          bodyClassName={s.chartBody}
        >
          <InsectHeatmapChart data={insectHeatmap} />
        </ChartCard>
      </div>
    </div>
  )
}
