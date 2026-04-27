import { useEffect, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import s from './DeepInsightPanel.module.css'

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function numericDisplay(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '--'
  }

  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

function metricScore(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return 0
  }

  return clamp(Math.abs(value), 0, 100)
}

function metricProgress(value, mode = 'risk') {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return 0
  }

  if (mode === 'improvement') {
    return clamp(value, 0, 100)
  }

  return metricScore(value)
}

function metricDisplay(value, suffix = '') {
  const base = numericDisplay(value)
  return base === '--' ? base : `${base}${suffix}`
}

function metricBadge(mode, numericValue, theme) {
  if (mode === 'improvement') {
    return {
      label: '\u4f30\u7b97',
      critical: numericValue !== null && numericValue < 0,
    }
  }

  const critical = numericValue !== null && (numericValue > 70 || (theme === '#f472b6' && numericValue > 50))
  return {
    label: critical ? '\u9884\u8b66' : '\u76d1\u6d4b',
    critical,
  }
}

function valueText(value, suffix = '') {
  if (value === null || value === undefined || value === '') {
    return '--'
  }

  return `${value}${suffix}`
}

function shortDate(value) {
  return typeof value === 'string' && value.length >= 10 ? value.slice(5) : '--'
}

function rangeText(start, end) {
  if (!start || !end) {
    return '--'
  }

  return `${shortDate(start)} - ${shortDate(end)}`
}

export default function DeepInsightPanel({ ecoIndex, guidelineMetrics }) {
  const d = ecoIndex?.data || {}
  const gm = guidelineMetrics?.data || guidelineMetrics || {}
  const runoff = gm.runoff_erosion || {}
  const water = gm.water_quality || {}
  const pest = gm.pest_management || {}
  const weather = gm.weather_support || {}
  const [showInsights, setShowInsights] = useState(false)

  useEffect(() => {
    setShowInsights(false)
    const timer = setTimeout(() => setShowInsights(true), 320)
    return () => clearTimeout(timer)
  }, [d.eco_health])

  const ecoHealth = typeof d.eco_health === 'number' ? d.eco_health : null

  const sensorMetrics = [
    {
      label: '水土流失风险',
      value: d.erosion_risk,
      theme: '#38bdf8',
      note: '实时风险值',
    },
    {
      label: '水环境污染负荷',
      value: d.pollution_load,
      theme: '#fbbf24',
      note: '综合负荷值',
    },
    {
      label: '病虫爆发预警',
      value: d.pest_risk,
      theme: '#f472b6',
      note: '风险预警值',
    },
    {
      label: '生物活跃指数',
      value: d.bio_activity,
      theme: '#4ade80',
      note: '群落活跃度',
    },
    {
      label: '\u4f30\u7b97\u51cf\u8680\u7387',
      value: runoff.estimated_reduction_rate,
      theme: '#38bdf8',
      note: '\u76f8\u5bf9\u6b21\u751f\u6797\u53c2\u7167\u7ad9',
      suffix: '%',
      mode: 'improvement',
    },
    {
      label: '\u6c61\u67d3\u524a\u51cf\u7efc\u5408\u7387',
      value: water.composite_reduction_rate,
      theme: '#fbbf24',
      note: '\u76f8\u5bf9\u7edf\u4e00\u57fa\u51c6\u671f',
      suffix: '%',
      mode: 'improvement',
    },
  ]

  const radarOption = {
    backgroundColor: 'transparent',
    animation: false,
    radar: {
      indicator: [
        { name: '流失控制', max: 100 },
        { name: '生物活跃', max: 100 },
        { name: '植保防控', max: 100 },
        { name: '面源环境', max: 100 },
        { name: '水文健康', max: 100 },
      ],
      shape: 'polygon',
      radius: '68%',
      splitNumber: 6,
      axisName: { color: '#a5b4fc', fontSize: 11, fontWeight: 'bold' },
      splitLine: {
        lineStyle: {
          color: [
            'rgba(99, 102, 241, 0.1)',
            'rgba(99, 102, 241, 0.2)',
            'rgba(99, 102, 241, 0.35)',
            'rgba(99, 102, 241, 0.5)',
            'rgba(99, 102, 241, 0.7)',
            'rgba(99, 102, 241, 0.9)',
          ],
        },
      },
      splitArea: {
        show: true,
        areaStyle: { color: ['rgba(0,0,0,0)', 'rgba(99, 102, 241, 0.05)'] },
      },
      axisLine: { lineStyle: { color: 'rgba(99, 102, 241, 0.35)', type: 'dashed' } },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: [
              clamp(100 - (d.erosion_risk || 0), 0, 100),
              d.bio_activity || 0,
              clamp(100 - (d.pest_risk || 0), 0, 100),
              clamp(100 - (d.pollution_load || 0), 0, 100),
              d.hydrology_health || 0,
            ],
            name: 'Realtime Data',
            symbol: 'circle',
            symbolSize: 6,
            itemStyle: {
              color: '#818cf8',
              borderColor: '#fff',
              borderWidth: 2,
              shadowColor: '#818cf8',
              shadowBlur: 10,
            },
            areaStyle: {
              color: {
                type: 'radial',
                x: 0.5,
                y: 0.5,
                r: 0.5,
                colorStops: [
                  { offset: 0, color: 'rgba(99, 102, 241, 0.55)' },
                  { offset: 1, color: 'rgba(168, 85, 247, 0.18)' },
                ],
              },
            },
            lineStyle: { width: 3, color: '#818cf8', shadowBlur: 15, shadowColor: '#818cf8' },
          },
          {
            value: [90, 85, 95, 88, 92],
            name: 'Ideal State',
            symbol: 'none',
            lineStyle: { width: 2, type: 'dotted', color: 'rgba(56, 189, 248, 0.8)' },
            areaStyle: { color: 'rgba(56, 189, 248, 0)' },
          },
        ],
      },
    ],
  }

  const headline = ecoHealth !== null && ecoHealth > 80
    ? '生态综合评估：全区生态状态稳定，多源监测协同良好。'
    : '生态综合评估：存在局部环境扰动风险。'

  const runoffText = runoff.estimated_reduction_rate != null
    ? '水土分析：径流对照结果已形成有效参照，当前减蚀表现整体稳定。'
    : d.erosion_risk > 50
      ? '水土分析：局部水土流失扰动有抬升迹象，建议加强坡面与汇流通道巡查。'
      : '水土状态：24小时内未见异常侵蚀现象，地表径流形态平稳。'

  const waterText = water.composite_reduction_rate != null
    ? '水质分析：统一基准期口径下整体波动可控，建议持续关注氮磷及高锰酸盐变化。'
    : '水质分析：当前仅形成阶段性监测观察值，建议继续补充稳定序列。'

  const pestText = pest.risk_level === '高'
    ? '病虫研判：当前病虫风险较高，建议维持联动巡检并同步开展田间复核。'
    : pest.risk_level
      ? '病虫研判：当前病虫风险总体可控，建议保持连续监测。'
      : '病虫研判：暂未形成稳定风险等级，建议保持连续监测。'

  const focusFacts = [
    {
      label: '参照样地',
      value: runoff.reference_station?.name || '次生林径流点',
      meta: '径流对照口径',
    },
    {
      label: '系统基准期',
      value: valueText(water.baseline_period?.days, '天'),
      meta: '不足30天按已有天数',
    },
    {
      label: '优势虫种',
      value: pest.top_species?.name || '--',
      meta: `风险等级 ${valueText(pest.risk_level)}`,
    },
    {
      label: '近7天降水',
      value: valueText(weather.history_summary?.total_precip, ' mm'),
      meta: rangeText(weather.history_range?.start, weather.history_range?.end),
    },
  ]

  return (
    <div className={s.wrap}>
      <section className={s.radarCard}>
        <div className={s.sectionEyebrow}>生态画像</div>

        <div className={s.radarShell}>
          <div className={s.radarHaloOuter} />
          <div className={s.radarHaloInner} />
          <ReactECharts option={radarOption} style={{ width: '100%', height: '100%' }} />
        </div>

        <div className={s.scorePanel}>
          <div className={s.scoreLabel}>生态健康指数</div>
          <div className={s.scoreValue}>
            {ecoHealth ?? '--'}
            <span>/100</span>
          </div>
        </div>
      </section>

      <div className={s.main}>
        <div className={s.metricsGrid}>
          {sensorMetrics.map((item) => (
            <SensorHudCard
              key={item.label}
              label={item.label}
              value={item.value}
              theme={item.theme}
              note={item.note}
              suffix={item.suffix}
              mode={item.mode}
            />
          ))}
        </div>

        <section className={`${s.insightCard} ${showInsights ? s.insightVisible : ''}`}>
          <div className={s.insightHead}>
            <div className={s.insightCopy}>
              <div className={s.sectionEyebrow}>综合判断</div>
              <div className={s.insightTitle}>{headline}</div>
            </div>

            <div className={s.aiBadge}>AI CORE</div>
          </div>

          <div className={s.insightBody}>
            <div className={s.insightList}>
              <InsightRow color="#38bdf8" text={runoffText} />
              <InsightRow color="#4ade80" text={waterText} />
              <InsightRow color="#f472b6" text={pestText} />
            </div>

            <div className={s.factGrid}>
              {focusFacts.map((item) => (
                <div key={item.label} className={s.factCard}>
                  <div className={s.factLabel}>{item.label}</div>
                  <div className={s.factValue}>{item.value}</div>
                  <div className={s.factMeta}>{item.meta}</div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

function InsightRow({ color, text }) {
  return (
    <div className={s.insightRow}>
      <div
        className={s.insightBar}
        style={{ '--accent': color }}
      />
      <div className={s.insightText}>{text}</div>
    </div>
  )
}

function SensorHudCard({ label, value, theme, note, suffix = '', mode = 'risk' }) {
  const numericValue = typeof value === 'number' && !Number.isNaN(value) ? value : null
  const displayValue = metricDisplay(value, suffix)
  const safeValue = metricProgress(numericValue, mode)
  const badge = metricBadge(mode, numericValue, theme)
  const isCritical = badge.critical

  return (
    <div
      className={`${s.metricCard} ${isCritical ? s.metricCardCritical : ''}`}
      style={{ '--accent': theme }}
    >
      <div className={s.metricTop}>
        <div className={s.metricCopy}>
          <div className={s.metricLabel}>{label}</div>
          <div className={s.metricNote}>{note || '实时监测'}</div>
        </div>

        <div className={`${s.metricBadge} ${isCritical ? s.metricBadgeCritical : ''}`}>
          {badge.label}
        </div>
      </div>

      <div className={s.metricBottom}>
        <div className={s.metricValue}>{displayValue}</div>
        <div className={s.metricTrack}>
          <div className={s.metricTrackBar} style={{ width: `${safeValue}%` }} />
        </div>
      </div>
    </div>
  )
}
