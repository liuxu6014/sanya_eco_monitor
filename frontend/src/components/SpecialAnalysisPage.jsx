import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import dayjs from 'dayjs'
import { usePolling } from '../hooks/usePolling.js'
import { api } from '../utils/api.js'
import { clearRequestCache, readRequestCache, writeRequestCache } from '../utils/requestCache.js'
import DeviceSeriesExplorer from './DeviceSeriesExplorer.jsx'
import DeviceMaintenancePanel from './DeviceMaintenancePanel.jsx'
import ImagePreviewModal from './ImagePreviewModal.jsx'
import s from './SpecialAnalysisPage.module.css'

const SECTIONS = [
  { key: 'insect', label: '虫情分析' },
  { key: 'spore', label: '孢子分析' },
  { key: 'rainfall', label: '雨情分析' },
  { key: 'runoff', label: '水土流失与径流' },
  { key: 'water', label: '面源水质污染' },
  { key: 'maintenance', label: '设备运维' },
]

const PERIODS = [
  { label: '近7天', value: 7 },
  { label: '近30天', value: 30 },
  { label: '近90天', value: 90 },
]

const PREFETCH_SECTIONS = {
  insect: ['spore', 'rainfall'],
  spore: ['insect'],
  rainfall: ['runoff', 'water'],
  runoff: ['rainfall', 'water'],
  water: ['runoff'],
}
const INITIAL_GALLERY_BATCH = 12
const GALLERY_BATCH_STEP = 12

const CHART_TEXT = { color: '#bfe8ff', fontSize: 11 }
const TOOLTIP = {
  backgroundColor: 'rgba(3, 17, 46, 0.95)',
  borderColor: 'rgba(56, 189, 248, 0.45)',
  borderWidth: 1,
  textStyle: { color: '#e0f2fe', fontSize: 12 },
  confine: true,
}

function formatTooltipMetric(value, unit = '') {
  if (value == null || value === '') return '—'
  return `${value}${unit ? ` ${unit}` : ''}`
}

function Empty({ label = '暂无数据' }) {
  return <div className={s.empty}>{label}</div>
}

function Card({ title, extra, children, className = '' }) {
  return (
    <section className={`${s.card} ${className}`.trim()}>
      <header className={s.cardHeader}>
        <div className={s.cardTitle}>{title}</div>
        {extra ? <div className={s.badge}>{extra}</div> : null}
      </header>
      <div className={s.cardBody}>{children}</div>
    </section>
  )
}

function Metric({ label, value, unit, tone = 'cyan' }) {
  return (
    <div className={`${s.metric} ${s[tone] || ''}`}>
      <div className={s.metricLabel}>{label}</div>
      <div className={s.metricValue}>
        {value ?? '—'}{unit ? <span>{unit}</span> : null}
      </div>
    </div>
  )
}

function SearchBox({ value, onChange, onSubmit, placeholder, onClear }) {
  return (
    <form className={s.search} onSubmit={(event) => { event.preventDefault(); onSubmit() }}>
      <input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
      <button type="submit">搜索</button>
      <button type="button" onClick={onClear}>整体</button>
    </form>
  )
}

function TrendChart({ data, name = '数量', unit = '', type = 'line' }) {
  const rows = data || []
  if (!rows.length) return <Empty />
  const option = {
    backgroundColor: 'transparent',
    animation: false,
    grid: { left: 42, right: 20, top: 36, bottom: 28, containLabel: true },
    tooltip: { ...TOOLTIP, trigger: 'axis', valueFormatter: (value) => `${value ?? 0}${unit}` },
    xAxis: {
      type: 'category',
      data: rows.map((item) => formatAxisLabel(item.date)),
      axisLabel: { ...CHART_TEXT, rotate: 20 },
      axisLine: { lineStyle: { color: 'rgba(125,211,252,0.35)' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLabel: CHART_TEXT,
      splitLine: { lineStyle: { color: 'rgba(125,211,252,0.1)', type: 'dashed' } },
    },
    series: [{
      name,
      type,
      smooth: true,
      barMaxWidth: 18,
      data: rows.map((item) => item.total ?? item.value ?? item.rainfall ?? item.runoff ?? 0),
      lineStyle: { color: '#38bdf8', width: 2 },
      itemStyle: { color: '#38bdf8', borderRadius: [4, 4, 0, 0] },
      areaStyle: type === 'line' ? { color: 'rgba(56,189,248,0.12)' } : undefined,
      showSymbol: false,
    }],
  }
  return <ReactECharts option={option} style={{ width: '100%', height: '100%' }} notMerge opts={{ renderer: 'canvas' }} />
}

function PieChart({ data, name = '构成' }) {
  const rows = (data || []).filter((item) => (item.value || 0) > 0).slice(0, 8)
  if (!rows.length) return <Empty />
  const option = {
    backgroundColor: 'transparent',
    animation: false,
    tooltip: { ...TOOLTIP, trigger: 'item' },
    legend: { type: 'scroll', bottom: 0, textStyle: CHART_TEXT, itemWidth: 8, itemHeight: 8 },
    series: [{
      name,
      type: 'pie',
      radius: ['46%', '72%'],
      center: ['50%', '43%'],
      avoidLabelOverlap: true,
      label: { color: '#dff6ff', formatter: '{b}\n{d}%' },
      labelLine: { lineStyle: { color: 'rgba(191,232,255,0.45)' } },
      data: rows,
    }],
  }
  return <ReactECharts option={option} style={{ width: '100%', height: '100%' }} notMerge opts={{ renderer: 'canvas' }} />
}

function MultiLineChart({ rows, series }) {
  const data = rows || []
  if (!data.length) return <Empty />
  const unitBySeriesName = Object.fromEntries((series || []).map((item) => [item.name, item.unit || '']))
  const option = {
    backgroundColor: 'transparent',
    animation: false,
    grid: { left: 44, right: 34, top: 48, bottom: 30, containLabel: true },
    tooltip: {
      ...TOOLTIP,
      trigger: 'axis',
      formatter: (params) => {
        const list = Array.isArray(params) ? params : [params]
        if (!list.length) return ''
        const axisLabel = list[0]?.axisValueLabel || list[0]?.axisValue || ''
        const lines = list.map((item) => `${item.marker}${item.seriesName}: ${formatTooltipMetric(item.value, unitBySeriesName[item.seriesName])}`)
        return [axisLabel, ...lines].join('<br/>')
      },
    },
    legend: { top: 4, textStyle: CHART_TEXT, icon: 'circle' },
    xAxis: {
      type: 'category',
      data: data.map((item) => String(item.date || '').slice(5)),
      axisLabel: { ...CHART_TEXT, rotate: 20 },
      axisLine: { lineStyle: { color: 'rgba(125,211,252,0.35)' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLabel: CHART_TEXT,
      splitLine: { lineStyle: { color: 'rgba(125,211,252,0.1)', type: 'dashed' } },
    },
    series: series.map((item) => ({
      name: item.name,
      type: item.type || 'line',
      smooth: true,
      barMaxWidth: 16,
      data: data.map((row) => row[item.key]),
      showSymbol: false,
      lineStyle: { color: item.color, width: 2 },
      itemStyle: { color: item.color, borderRadius: [4, 4, 0, 0] },
    })),
  }
  return <ReactECharts option={option} style={{ width: '100%', height: '100%' }} notMerge opts={{ renderer: 'canvas' }} />
}

function ImageGallery({ images, onPreview, progressive = false }) {
  const rows = images || []
  const [visibleCount, setVisibleCount] = useState(INITIAL_GALLERY_BATCH)
  const sentinelRef = useRef(null)

  useEffect(() => {
    setVisibleCount(INITIAL_GALLERY_BATCH)
  }, [rows])

  useEffect(() => {
    if (!progressive || rows.length <= visibleCount) return undefined
    if (typeof IntersectionObserver === 'undefined') return undefined
    const node = sentinelRef.current
    if (!node) return undefined
    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return
      setVisibleCount((count) => Math.min(rows.length, count + GALLERY_BATCH_STEP))
    }, { rootMargin: '240px 0px' })
    observer.observe(node)
    return () => observer.disconnect()
  }, [progressive, rows.length, visibleCount])

  if (!rows.length) return <Empty label="??????" />
  const visibleRows = progressive ? images.slice(0, visibleCount) : rows.slice(0, 18)
  return (
    <div className={s.gallery}>
      {visibleRows.map((item) => (
        <button key={item.id} type="button" className={s.thumb} onClick={() => onPreview(item)}>
          <img src={item.image_url} alt="????" loading="lazy" />
          <span>{formatTime(item.collection_time)}</span>
        </button>
      ))}
      {progressive && visibleCount < rows.length ? (
        <div ref={sentinelRef} data-batch-sentinel className={s.gallerySentinel}>
          ??????...
        </div>
      ) : null}
    </div>
  )
}

function FocusList({ rows, unit = '只' }) {
  if (!rows?.length) return <Empty label="暂无重点关注对象" />
  return (
    <div className={s.focusList}>
      {rows.slice(0, 6).map((item, index) => (
        <div key={item.name} className={s.focusItem}>
          <div className={s.rank}>{index + 1}</div>
          <div className={s.focusMain}>
            <div className={s.focusName}>{item.name}</div>
            <div className={s.progress}><span style={{ width: `${Math.min(item.attention_score || 0, 100)}%` }} /></div>
          </div>
          <div className={s.focusMeta}>
            <strong>{item.count}</strong>{unit}
            <small>评分 {item.harm_score ?? '—'}</small>
          </div>
        </div>
      ))}
    </div>
  )
}

function PestSection({ type, data, query, draft, setDraft, applySearch, clearSearch, onPreview }) {
  const isSpore = type === 'spore'
  const summary = data?.summary || {}
  const profile = data?.profile
  const stats = isSpore ? data?.spore_stats : data?.species_stats
  const focus = isSpore ? data?.focus_spores : data?.focus_species
  const unit = isSpore ? '个' : '只'

  return (
    <>
      <div className={s.toolbar}>
        <SearchBox
          value={draft}
          onChange={setDraft}
          onSubmit={applySearch}
          onClear={clearSearch}
          placeholder={isSpore ? '搜索某一类孢子' : '搜索某一类虫子'}
        />
        <div className={s.modeText}>{query ? `当前分析：${query}` : isSpore ? '当前展示：整体孢子捕捉情况' : '当前展示：整体虫情捕捉情况'}</div>
      </div>

      <div className={s.metricsGrid}>
        <Metric label="累计捕获" value={summary.total_count} unit={unit} />
        <Metric label="日均数量" value={summary.avg_daily} unit={unit} tone="green" />
        <Metric label="峰值日期" value={summary.peak_date ? dayjs(summary.peak_date).format('M月D日') : '—'} />
        <Metric label="活跃天数" value={summary.active_days} unit="天" tone="gold" />
      </div>

      <div className={s.grid}>
        <Card title={query ? '数量变化' : '捕获数量趋势'} className={s.wide}>
          <div className={s.trendPanel}>
            <div className={s.trendChartBody}>
              <TrendChart data={data?.trend} name={query || (isSpore ? '孢子数量' : '虫情数量')} unit={unit} />
            </div>
          </div>
        </Card>
        <Card title={query ? (isSpore ? '孢子介绍与风险' : '虫子介绍与风险') : (isSpore ? '孢子类型构成分析' : '虫种构成分析')} extra={query ? '专项' : '构成'}>
          {query && profile ? (
            <div className={s.profile}>
              <section className={s.profileBlock}>
                <h4>{isSpore ? '孢子介绍' : '虫子介绍'}</h4>
                <p>{profile.intro}</p>
              </section>
              <section className={s.profileBlock}>
                <h4>{isSpore ? '风险分析（评分）' : '危害分析（评分）'}</h4>
                <div className={s.scoreRow}>
                  <Metric label="危害评分" value={profile.harm_score} unit="分" tone="red" />
                  <Metric label="预警数量值" value={data?.warning?.threshold} unit={unit} tone="gold" />
                </div>
                <p>{profile.harm_analysis || data?.summary?.analysis}</p>
                {profile.risk_level_text ? <div className={s.riskPill}>综合等级：{profile.risk_level_text}</div> : null}
              </section>
              <section className={s.profileBlock}>
                <h4>{isSpore ? '防控策略' : '防治策略'}</h4>
                <p>{profile.strategy}</p>
                {profile.strategy_steps?.length ? (
                  <div className={s.strategyList}>
                    {profile.strategy_steps.map((item, index) => (
                      <div key={item} className={s.strategyItem}>
                        <span>{index + 1}</span>
                        <p>{item}</p>
                      </div>
                    ))}
                  </div>
                ) : null}
              </section>
              <div className={s.profileSummary}>
                {data?.summary?.analysis}
              </div>
            </div>
          ) : (
            <PieChart data={stats} name={isSpore ? '孢子类型' : '虫种'} />
          )}
        </Card>
        <Card title="实时图像显示" extra={data?.latest_image ? formatTime(data.latest_image.collection_time) : '实时'}>
          {data?.latest_image?.image_url ? (
            <button type="button" className={s.liveImage} onClick={() => onPreview(data.latest_image)}>
              <img src={data.latest_image.image_url} alt="实时捕捉图片" />
            </button>
          ) : <Empty label="暂无实时图像" />}
        </Card>
        <Card title="历史图像查询" extra="至少30分钟存储一张">
          <ImageGallery images={data?.images} onPreview={onPreview} />
        </Card>
        <Card title={isSpore ? '重点关注孢子类型' : '重点关注虫种'} extra="危害性 + 数量">
          <FocusList rows={focus} unit={unit} />
        </Card>
      </div>
    </>
  )
}

function SporeImageSection({ data, onPreview }) {
  const images = data?.images || []
  const latestRecordAt = data?.latest_record_time ? dayjs(data.latest_record_time) : null
  const latestImageAt = data?.latest_image_time ? dayjs(data.latest_image_time) : null
  const imageLagDays = latestRecordAt?.isValid() && latestImageAt?.isValid()
    ? latestRecordAt.startOf('day').diff(latestImageAt.startOf('day'), 'day')
    : 0
  return (
    <>
      {imageLagDays > 0 ? (
        <div className={s.sporeNotice}>
          最新孢子记录时间为 {formatTime(data.latest_record_time)}，最新有图记录停留在 {formatTime(data.latest_image_time)}，当前展示最近一张有图记录。
        </div>
      ) : null}
      <div className={s.grid}>
        <Card title="实时图像显示" extra={data?.latest_image ? formatTime(data.latest_image.collection_time) : '实时'}>
          {data?.latest_image?.image_url ? (
            <button type="button" className={s.liveImage} onClick={() => onPreview(data.latest_image)}>
              <img src={data.latest_image.image_url} alt="孢子实时捕捉图片" />
            </button>
          ) : <Empty label="暂无实时图像" />}
        </Card>
        <Card title="历史图像查询" extra={`${images.length} 张`} className={s.wide}>
          <ImageGallery images={images} onPreview={onPreview} progressive />
        </Card>
      </div>
    </>
  )
}

function AnalysisActionCard({ title, badge, analysis, facts = [], strategies = [] }) {
  return (
    <Card title={title} extra={badge} className={s.analysisActionCard}>
      <div className={s.analysisAction}>
        <div className={s.analysisMain}>
          {badge ? <div className={s.rainLevel}>{badge}</div> : null}
          <div className={s.analysisText}>{analysis || '暂无专项分析。'}</div>
          {facts.length ? (
            <div className={s.analysisFacts}>
              {facts.map((item) => <span key={item}>{item}</span>)}
            </div>
          ) : null}
        </div>
        <div className={s.actionList}>
          {strategies.map((item, index) => (
            <div key={item} className={s.actionItem}>
              <span>{index + 1}</span>
              <p>{item}</p>
            </div>
          ))}
        </div>
      </div>
    </Card>
  )
}

function RainfallSection({
  data,
  rainfallDaily,
  rainfallDailyByDevice,
  rainfallDailyAnomalySummary,
  overviewDeviceMeta,
}) {
  const summary = data?.summary || {}
  return (
    <>
      <div className={s.metricsGrid}>
        <Metric label="区域累计降雨" value={summary.total_rainfall} unit="mm" />
        <Metric label="雨日数量" value={summary.rainy_days} unit="天" tone="green" />
        <Metric label="单日峰值" value={summary.peak_rainfall} unit="mm" tone="gold" />
        <Metric label="风险等级" value={summary.level} tone="cyan" />
      </div>
      <div className={s.grid}>
        <Card title="雨量设备分站趋势" extra="分设备视图" className={s.fullRow}>
          <div className={s.deviceExplorerShell}>
            <DeviceSeriesExplorer
              rainfallOverview={rainfallDaily}
              rainfallByDevice={rainfallDailyByDevice}
              rainfallAnomalySummary={rainfallDailyAnomalySummary}
              deviceMeta={{ rain_gauges: overviewDeviceMeta?.rain_gauges }}
              allowedModes={['rainfall']}
              defaultMode="rainfall"
            />
          </div>
        </Card>
        <AnalysisActionCard
          title="雨情研判与处置建议"
          badge={summary.level || '常规监测'}
          analysis={summary.analysis}
          strategies={data?.strategy || []}
        />
      </div>
    </>
  )
}

function RunoffSection({ data, runoffDaily, runoffDailyByDevice, runoffDailyAnomalySummary, overviewDeviceMeta }) {
  const summary = data?.summary || {}

  return (
    <>
      <div className={s.metricsGrid}>
        <Metric label="累计径流" value={summary.total_runoff} unit="m³" />
        <Metric label="平均含沙量" value={summary.avg_sand} unit="kg/L" tone="gold" />
        <Metric label="风险评分" value={summary.risk_score} unit="分" tone="red" />
        <Metric label="趋势变化" value={summary.trend} />
      </div>
      <div className={s.grid}>
        <Card title="径流设备" className={s.fullRow}>
          <div className={s.deviceExplorerShell}>
            <DeviceSeriesExplorer
              runoffOverview={runoffDaily}
              runoffByDevice={runoffDailyByDevice}
              runoffAnomalySummary={runoffDailyAnomalySummary}
              deviceMeta={{ runoff_devices: overviewDeviceMeta?.runoff_devices }}
              allowedModes={['runoff']}
              defaultMode="runoff"
            />
          </div>
        </Card>
        <AnalysisActionCard
          title="专项分析结论与应对策略"
          badge={summary.risk_level || '常规监测'}
          analysis={summary.analysis}
          facts={[
            `峰值径流 ${summary.peak_runoff_date || '?'} / ${summary.peak_runoff ?? '?'} m³`,
            `含沙峰值 ${summary.peak_sand_date || '?'} / ${summary.peak_sand ?? '?'} kg/L`,
            `侵蚀代理 ${summary.peak_erosion_proxy ?? '?'}`,
          ]}
          strategies={data?.strategy || []}
        />
      </div>
    </>
  )
}

function WaterSection({ data }) {
  const summary = data?.summary || {}
  return (
    <>
      <div className={s.metricsGrid}>
        <Metric label="综合等级" value={summary.risk_level} />
        <Metric label="风险评分" value={summary.risk_score} unit="分" tone="red" />
        <Metric label="重点指标" value={summary.main_risk || '—'} tone="gold" />
        <Metric label="超标天数" value={summary.main_risk_exceed_days} unit="天" />
      </div>
      <div className={s.grid}>
        <Card title="水质指标趋势" extra="氮磷负荷" className={s.wide}>
          <MultiLineChart rows={data?.daily} series={[
            { key: 'permanganate', name: '高锰酸盐指数', color: '#38bdf8', type: 'bar', unit: 'mg/L' },
            { key: 'tn', name: '总氮', color: '#a78bfa', unit: 'mg/L' },
            { key: 'tp', name: '总磷', color: '#fb7185', unit: 'mg/L' },
            { key: 'nh4n', name: '氨氮', color: '#facc15', unit: 'mg/L' },
          ]} />
        </Card>
        <Card title="指标专项分析" extra="均值 + 阈值">
          <div className={s.table}>
            {(data?.metrics || []).map((item) => (
              <div key={item.key} className={s.tableRow}>
                <span>{item.label}</span>
                <strong>{item.avg ?? '—'} {item.unit}</strong>
                <em>阈值 {item.limit}</em>
                <small>{item.trend}</small>
              </div>
            ))}
          </div>
        </Card>
        <AnalysisActionCard
          title="污染风险结论与应对策略"
          badge={summary.risk_level || '常规监测'}
          analysis={summary.analysis}
          facts={[
            `重点指标 ${summary.main_risk || '—'}`,
            `超标天数 ${summary.main_risk_exceed_days ?? 0}天`,
            `风险评分 ${summary.risk_score ?? '—'}分`,
          ]}
          strategies={data?.strategy || []}
        />
      </div>
    </>
  )
}

function formatTime(value) {
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('YYYY年M月D日 HH:mm:ss') : '时间未知'
}

function formatAxisLabel(value) {
  const text = String(value || '')
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) return text.slice(5)
  if (/^\d{4}-\d{2}$/.test(text)) return text.slice(2)
  return text
}

function buildAnalysisCacheKey(section, days, query = '') {
  return `special-analysis:${section}:${days}:${query || '__all__'}`
}

async function fetchSectionData(section, days, query = '') {
  if (section === 'insect') return api.insectAnalysisDetail(query, days)
  if (section === 'spore') return api.sporeAnalysisDetail(query, days)
  if (section === 'rainfall') return api.rainfallAnalysis(days)
  if (section === 'runoff') return api.runoffAnalysis(days)
  if (section === 'water') return api.waterQualityAnalysis(days)
  return { data: null }
}

export default function SpecialAnalysisPage({ active = true }) {
  const [section, setSection] = useState('insect')
  const [days, setDays] = useState(30)
  const [customDays, setCustomDays] = useState('30')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  const [speciesDraft, setSpeciesDraft] = useState('')
  const [speciesQuery, setSpeciesQuery] = useState('')
  const [sporeDraft, setSporeDraft] = useState('')
  const [sporeQuery, setSporeQuery] = useState('')
  const [preview, setPreview] = useState(null)
  const cappedDays = useMemo(() => (section === 'rainfall' ? days : Math.min(days, 90)), [days, section])
  const rainfallExplorer = usePolling(
    useCallback(() => api.rainfallDaily(cappedDays), [cappedDays]),
    30_000,
    {
      cacheKey: `special-rainfall-explorer-${cappedDays}`,
      persist: false,
      staleMs: 30_000,
      enabled: active && section === 'rainfall',
    },
  )
  const runoffExplorer = usePolling(
    useCallback(() => api.runoffDaily(cappedDays), [cappedDays]),
    30_000,
    {
      cacheKey: `special-runoff-explorer-${cappedDays}`,
      persist: false,
      staleMs: 30_000,
      enabled: active && section === 'runoff',
    },
  )
  const overviewMetaRequest = usePolling(
    useCallback(() => api.overview(), []),
    30_000,
    {
      cacheKey: 'special-overview-device-meta',
      persist: false,
      staleMs: 30_000,
      enabled: active && (section === 'rainfall' || section === 'runoff'),
    },
  )
  const rainfallDaily = rainfallExplorer.data?.data || []
  const rainfallDailyByDevice = rainfallExplorer.data?.by_device || {}
  const rainfallDailyAnomalySummary = rainfallExplorer.data?.anomaly_summary || {}
  const runoffDaily = runoffExplorer.data?.data || []
  const runoffDailyByDevice = runoffExplorer.data?.by_device || {}
  const runoffDailyAnomalySummary = runoffExplorer.data?.anomaly_summary || {}
  const overviewDeviceMeta = overviewMetaRequest.data?.data?.device_meta

  const analysisQuery = useMemo(() => (
    section === 'insect'
      ? speciesQuery.trim()
      : section === 'spore'
        ? sporeQuery.trim()
        : ''
  ), [section, speciesQuery, sporeQuery])
  const analysisCacheKey = useMemo(() => buildAnalysisCacheKey(section, cappedDays, analysisQuery), [analysisQuery, cappedDays, section])

  const load = useCallback(async () => {
    if (!active) return
    if (section === 'maintenance') {
      // 设备运维板块自带数据获取，跳过通用 section 数据流。
      setData(null)
      setLoading(false)
      setError('')
      return
    }
    const cachedAnalysis = analysisCacheKey ? readRequestCache(analysisCacheKey, { persist: false }) : null
    if (cachedAnalysis) {
      setData(cachedAnalysis.data || null)
      setLoading(false)
    } else {
      setData(null)
      setLoading(true)
    }
    setError('')
    try {
      const result = await fetchSectionData(section, cappedDays, analysisQuery)
      const nextData = result?.data || null
      setData(nextData)
      if (analysisCacheKey) {
        writeRequestCache(analysisCacheKey, { data: nextData, persist: false })
      }
    } catch (err) {
      setError(err?.message || '专项分析数据加载失败')
      if (!cachedAnalysis) {
        setData(null)
      }
    } finally {
      setLoading(false)
    }
  }, [active, analysisCacheKey, analysisQuery, cappedDays, section])

  const prefetchSectionData = useCallback(async (targetSection) => {
    const targetQuery = ''
    const targetCacheKey = buildAnalysisCacheKey(targetSection, cappedDays, targetQuery)
    if (readRequestCache(targetCacheKey, { persist: false })) {
      return
    }
    try {
      const result = await fetchSectionData(targetSection, cappedDays, targetQuery)
      writeRequestCache(targetCacheKey, { data: result?.data || null, persist: false })
    } catch {
    }
  }, [cappedDays])

  const refreshSection = useCallback(() => {
    clearRequestCache(analysisCacheKey)
    setRefreshKey((value) => value + 1)
    rainfallExplorer.refetch().catch(() => {})
    runoffExplorer.refetch().catch(() => {})
    overviewMetaRequest.refetch().catch(() => {})
  }, [analysisCacheKey, overviewMetaRequest, rainfallExplorer, runoffExplorer])

  useEffect(() => {
    load()
  }, [load, refreshKey])

  useEffect(() => {
    if (!active) return undefined
    window.addEventListener('app:refresh-data', refreshSection)
    return () => window.removeEventListener('app:refresh-data', refreshSection)
  }, [active, refreshSection])

  useEffect(() => {
    if (!active) return undefined
    const timer = window.setInterval(refreshSection, 30_000)
    return () => window.clearInterval(timer)
  }, [active, refreshSection])

  useEffect(() => {
    if (!active) return undefined
    const prefetchTargets = PREFETCH_SECTIONS[section] || []
    if (!prefetchTargets.length) return undefined

    const schedule = typeof window !== 'undefined' && typeof window.requestIdleCallback === 'function'
      ? window.requestIdleCallback.bind(window)
      : (callback) => window.setTimeout(callback, 180)
    const cancel = typeof window !== 'undefined' && typeof window.cancelIdleCallback === 'function'
      ? window.cancelIdleCallback.bind(window)
      : window.clearTimeout.bind(window)

    const handle = schedule(() => {
      prefetchTargets.forEach((targetSection) => {
        prefetchSectionData(targetSection).catch(() => {})
      })
    })

    return () => cancel(handle)
  }, [active, cappedDays, prefetchSectionData, section])

  const content = () => {
    if (section === 'maintenance') {
      return <DeviceMaintenancePanel active={active && section === 'maintenance'} />
    }
    if (loading && !data) return <div className={s.state}>正在加载专项分析...</div>
    if (error) return <div className={s.state}>{error}</div>
    if (!data) return <div className={s.state}>暂无专项分析数据</div>
    if (section === 'insect') {
      return (
        <PestSection
          type="insect"
          data={data}
          query={speciesQuery}
          draft={speciesDraft}
          setDraft={setSpeciesDraft}
          applySearch={() => setSpeciesQuery(speciesDraft.trim())}
          clearSearch={() => { setSpeciesDraft(''); setSpeciesQuery('') }}
          onPreview={setPreview}
        />
      )
    }
    if (section === 'spore') {
      return <SporeImageSection data={data} onPreview={setPreview} />
    }
    if (section === 'rainfall') {
      return (
        <RainfallSection
          data={data}
          rainfallDaily={rainfallDaily}
          rainfallDailyByDevice={rainfallDailyByDevice}
          rainfallDailyAnomalySummary={rainfallDailyAnomalySummary}
          overviewDeviceMeta={overviewDeviceMeta}
        />
      )
    }
    if (section === 'runoff') {
      return (
        <RunoffSection
          data={data}
          runoffDaily={runoffDaily}
          runoffDailyByDevice={runoffDailyByDevice}
          runoffDailyAnomalySummary={runoffDailyAnomalySummary}
          overviewDeviceMeta={overviewDeviceMeta}
        />
      )
    }
    return <WaterSection data={data} />
  }

  return (
    <div className={s.page}>
      <div className={s.topbar}>
        <div className={s.tabs}>
          {SECTIONS.map((item) => (
            <button
              key={item.key}
              type="button"
              className={section === item.key ? s.activeTab : ''}
              onClick={() => setSection(item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>
        {section !== 'maintenance' && (
          <div className={s.filters}>
            {PERIODS.map((item) => (
              <button
                key={item.value}
                type="button"
                className={days === item.value ? s.activePeriod : ''}
                onClick={() => {
                  setDays(item.value)
                  setCustomDays(String(item.value))
                }}
              >
                {item.label}
              </button>
            ))}
            <label className={s.customDays}>
              <span>自定义</span>
              <input
                value={customDays}
                onChange={(event) => setCustomDays(event.target.value.replace(/\D/g, '').slice(0, 3))}
                onBlur={() => {
                  const next = Math.max(7, Math.min(Number(customDays) || 30, section === 'rainfall' ? 366 : 90))
                  setCustomDays(String(next))
                  setDays(next)
                }}
              />
              <span>天</span>
            </label>
          </div>
        )}
      </div>

      {content()}

      <ImagePreviewModal
        open={!!preview}
        src={preview?.image_url}
        alt="捕捉图片预览"
        capturedAt={preview?.collection_time}
        onClose={() => setPreview(null)}
      />
    </div>
  )
}
