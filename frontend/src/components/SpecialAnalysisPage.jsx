import { useCallback, useEffect, useMemo, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import dayjs from 'dayjs'
import { api } from '../utils/api.js'
import ImagePreviewModal from './ImagePreviewModal.jsx'
import s from './SpecialAnalysisPage.module.css'

const SECTIONS = [
  { key: 'insect', label: '虫情分析' },
  { key: 'spore', label: '孢子分析' },
  { key: 'rainfall', label: '雨情分析' },
  { key: 'runoff', label: '水土流失与径流' },
  { key: 'water', label: '面源水质污染' },
]

const PERIODS = [
  { label: '近7天', value: 7 },
  { label: '近30天', value: 30 },
  { label: '近90天', value: 90 },
]

const GRANULARITIES = [
  { label: '按天', value: 'day' },
  { label: '按周', value: 'week' },
  { label: '按月', value: 'month' },
]

const CHART_TEXT = { color: '#bfe8ff', fontSize: 11 }
const TOOLTIP = {
  backgroundColor: 'rgba(3, 17, 46, 0.95)',
  borderColor: 'rgba(56, 189, 248, 0.45)',
  borderWidth: 1,
  textStyle: { color: '#e0f2fe', fontSize: 12 },
  confine: true,
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

function aggregateTrend(rows, granularity) {
  if (granularity === 'day') return rows || []
  const buckets = new Map()
  ;(rows || []).forEach((item) => {
    const parsed = dayjs(item.date)
    const dayOfYear = parsed.diff(parsed.startOf('year'), 'day') + 1
    const key = granularity === 'month'
      ? parsed.format('YYYY-MM')
      : `${parsed.year()}年第${Math.ceil(dayOfYear / 7)}周`
    buckets.set(key, (buckets.get(key) || 0) + (item.total || 0))
  })
  return Array.from(buckets.entries()).map(([date, total]) => ({ date, total }))
}

function MultiLineChart({ rows, series }) {
  const data = rows || []
  if (!data.length) return <Empty />
  const option = {
    backgroundColor: 'transparent',
    animation: false,
    grid: { left: 44, right: 34, top: 48, bottom: 30, containLabel: true },
    tooltip: { ...TOOLTIP, trigger: 'axis' },
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

function ImageGallery({ images, onPreview }) {
  const rows = images || []
  if (!rows.length) return <Empty label="暂无捕捉图片" />
  return (
    <div className={s.gallery}>
      {rows.slice(0, 18).map((item) => (
        <button key={item.id} type="button" className={s.thumb} onClick={() => onPreview(item)}>
          <img src={item.image_url} alt="捕捉图片" loading="lazy" />
          <span>{formatTime(item.collection_time)}</span>
        </button>
      ))}
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

function PestSection({ type, data, query, draft, setDraft, applySearch, clearSearch, granularity, setGranularity, onPreview }) {
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
        <div className={s.granularity}>
          {GRANULARITIES.map((item) => (
            <button
              key={item.value}
              type="button"
              className={granularity === item.value ? s.activePeriod : ''}
              onClick={() => setGranularity(item.value)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className={s.modeText}>{query ? `当前分析：${query}` : isSpore ? '当前展示：整体孢子捕捉情况' : '当前展示：整体虫情捕捉情况'}</div>
      </div>

      <div className={s.metricsGrid}>
        <Metric label="累计捕获" value={summary.total_count} unit={unit} />
        <Metric label="日均数量" value={summary.avg_daily} unit={unit} tone="green" />
        <Metric label="峰值日期" value={summary.peak_date ? dayjs(summary.peak_date).format('M月D日') : '—'} />
        <Metric label="活跃天数" value={summary.active_days} unit="天" tone="gold" />
      </div>

      <div className={s.grid}>
        <Card title={query ? '数量变化' : '捕获数量趋势'} extra={GRANULARITIES.find((item) => item.value === granularity)?.label} className={s.wide}>
          <TrendChart data={aggregateTrend(data?.trend, granularity)} name={query || (isSpore ? '孢子数量' : '虫情数量')} unit={unit} />
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
          <ImageGallery images={images} onPreview={onPreview} />
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

function RainfallSection({ data }) {
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
        <Card title="雨量统计" extra="日统计" className={s.wide}>
          <TrendChart data={data?.daily} name="日降雨量" unit="mm" type="bar" />
        </Card>
        <Card title="雨量统计" extra="月统计">
          <TrendChart data={data?.monthly} name="月累计降雨" unit="mm" type="bar" />
        </Card>
        <AnalysisActionCard
          title="雨情研判与处置建议"
          badge={summary.level || '常规监测'}
          analysis={summary.analysis}
          facts={[
            `趋势 ${summary.trend || '—'}`,
            `最大小时雨量 ${summary.max_hourly ?? '—'}mm`,
            `站点峰值 ${summary.station_peak ?? '—'}mm`,
          ]}
          strategies={data?.strategy || []}
        />
      </div>
    </>
  )
}

function RunoffSection({ data }) {
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
        <Card title="水土流失与径流趋势" extra="径流 + 含沙" className={s.wide}>
          <MultiLineChart rows={data?.daily} series={[
            { key: 'runoff', name: '当日径流量', color: '#38bdf8', type: 'bar' },
            { key: 'sand', name: '平均含沙量', color: '#facc15' },
            { key: 'flow', name: '平均流量', color: '#4ade80' },
          ]} />
        </Card>
        <Card title="侵蚀代理指标" extra="径流量 × 含沙量">
          <TrendChart data={data?.erosion_series} name="侵蚀代理指标" type="bar" />
        </Card>
        <AnalysisActionCard
          title="专项分析结论与应对策略"
          badge={summary.risk_level || '常规监测'}
          analysis={summary.analysis}
          facts={[
            `峰值径流 ${summary.peak_runoff_date || '—'} / ${summary.peak_runoff ?? '—'}m³`,
            `含沙峰值 ${summary.peak_sand_date || '—'} / ${summary.peak_sand ?? '—'}kg/L`,
            `侵蚀代理 ${summary.peak_erosion_proxy ?? '—'}`,
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
            { key: 'permanganate', name: '高锰酸盐指数', color: '#38bdf8', type: 'bar' },
            { key: 'tn', name: '总氮', color: '#a78bfa' },
            { key: 'tp', name: '总磷', color: '#fb7185' },
            { key: 'nh4n', name: '氨氮', color: '#facc15' },
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

export default function SpecialAnalysisPage({ active = true }) {
  const [section, setSection] = useState('insect')
  const [days, setDays] = useState(30)
  const [customDays, setCustomDays] = useState('30')
  const [granularity, setGranularity] = useState('day')
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

  const load = useCallback(async () => {
    if (!active) return
    setLoading(true)
    setError('')
    try {
      let result
      if (section === 'insect') result = await api.insectAnalysisDetail(speciesQuery.trim(), cappedDays)
      if (section === 'spore') result = await api.sporeAnalysisDetail(sporeQuery.trim(), cappedDays)
      if (section === 'rainfall') result = await api.rainfallAnalysis(cappedDays)
      if (section === 'runoff') result = await api.runoffAnalysis(cappedDays)
      if (section === 'water') result = await api.waterQualityAnalysis(cappedDays)
      setData(result?.data || null)
    } catch (err) {
      setError(err?.message || '专项分析数据加载失败')
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [active, cappedDays, section, speciesQuery, sporeQuery])

  useEffect(() => {
    load()
  }, [load, refreshKey])

  useEffect(() => {
    if (!active) return undefined
    const handleRefresh = () => setRefreshKey((value) => value + 1)
    window.addEventListener('app:refresh-data', handleRefresh)
    return () => window.removeEventListener('app:refresh-data', handleRefresh)
  }, [active])

  const content = () => {
    if (loading) return <div className={s.state}>正在加载专项分析...</div>
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
          granularity={granularity}
          setGranularity={setGranularity}
          onPreview={setPreview}
        />
      )
    }
    if (section === 'spore') {
      return <SporeImageSection data={data} onPreview={setPreview} />
    }
    if (section === 'rainfall') return <RainfallSection data={data} />
    if (section === 'runoff') return <RunoffSection data={data} />
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
