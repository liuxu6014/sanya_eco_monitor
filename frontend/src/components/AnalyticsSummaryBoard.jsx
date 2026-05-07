import { useEffect, useState } from 'react'
import s from './AnalyticsSummaryBoard.module.css'

function toneClass(levelCode = 'normal') {
  if (levelCode === 'critical') return s.critical
  if (levelCode === 'high') return s.high
  if (levelCode === 'severe') return s.severe
  if (levelCode === 'attention') return s.attention
  return s.normal
}

function clampScore(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) {
    return 0
  }
  return Math.max(0, Math.min(100, numeric))
}

function splitRuleText(value) {
  if (typeof value !== 'string') {
    return []
  }

  return value
    .split(/[;；。]/)
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 4)
}

function WarningEyebrow({ text }) {
  const normalizedText = typeof text === 'string' ? text : ''

  return (
    <span className={s.warningCardEyebrow} aria-label={normalizedText}>
      {[...normalizedText].map((char, index) => (
        <span className={s.warningCardEyebrowGlyph} key={`${normalizedText}-${index}`}>
          {char}
        </span>
      ))}
    </span>
  )
}

export default function AnalyticsSummaryBoard({ guidelineMetrics }) {
  const payload = guidelineMetrics?.data || guidelineMetrics || {}
  const warningAnalysis = payload.warning_analysis || {}
  const warningsByKey = new Map((warningAnalysis.indicator_warnings || []).map((item) => [item.key, item]))
  const warnings = [
    warningsByKey.get('insect_peak') || createMissingWarning('insect_peak', '虫情单日峰值'),
    warningsByKey.get('sand_content') || createMissingWarning('sand_content', '含沙监测风险'),
    warningsByKey.get('rainfall_peak') || createMissingWarning('rainfall_peak', '单日降水强度'),
  ]
  const warningKeySignature = warnings.map((item) => item.key).join('|')

  const [activeWarningIndex, setActiveWarningIndex] = useState(0)

  useEffect(() => {
    setActiveWarningIndex(0)
  }, [warningKeySignature])

  useEffect(() => {
    if (warnings.length <= 1) {
      return undefined
    }

    const timer = window.setInterval(() => {
      setActiveWarningIndex((current) => (current + 1) % warnings.length)
    }, 5200)

    return () => window.clearInterval(timer)
  }, [warnings.length])

  return (
    <div className={s.wrap}>
      {warnings.length ? (
        <section className={s.warningStage}>
          <div className={s.warningCardGrid}>
            {warnings.map((item, index) => {
              const score = clampScore(item.score)
              const isActive = index === activeWarningIndex
              const ruleCount = splitRuleText(item.rule_text).length

              return (
                <button
                  key={item.key || `${item.title}-${index}`}
                  type="button"
                  className={`${s.warningCard} ${toneClass(item.level_code)} ${isActive ? s.warningCardActive : ''}`}
                  onClick={() => setActiveWarningIndex(index)}
                >
                  <span className={s.warningCardGlow} />

                  <div className={s.warningCardHead}>
                    <div className={s.warningCardMarkerWrap}>
                      <span className={s.warningCardMarker} />
                      <WarningEyebrow text={isActive ? '\u5f53\u524d\u91cd\u70b9' : '\u5206\u7ea7\u9884\u8b66'} />
                    </div>

                    <span className={s.warningCardLevel}>{item.level}</span>
                  </div>

                  <div className={s.warningCardTitle}>{item.title}</div>
                  <div className={s.warningCardMetric}>{item.metric_label}</div>

                  <div className={s.warningCardValueRow}>
                    <span className={s.warningCardValue}>{item.display_value}</span>
                    <span className={s.warningCardScore}>{score}%</span>
                  </div>

                  <div className={s.warningCardBand}>
                    {`\u5224\u5b9a\u533a\u95f4\uff1a${item.band || '--'} \u00b7 ${ruleCount || '--'}\u6863\u5206\u5c42`}
                  </div>

                  <div className={s.warningCardTrack}>
                    <span className={s.warningCardTrackBar} style={{ width: `${score}%` }} />
                  </div>

                  <div className={s.warningCardMetaGrid}>
                    <div className={s.warningCardMeta}>
                      <span className={s.warningMetaLabel}>{'\u76d1\u6d4b\u6458\u8981'}</span>
                      <span className={s.warningMetaText}>{item.summary || '\u6682\u65e0\u6458\u8981'}</span>
                    </div>

                    <div className={s.warningCardMeta}>
                      <span className={s.warningMetaLabel}>{'\u5efa\u8bae\u52a8\u4f5c'}</span>
                      <span className={s.warningMetaText}>{item.action || '\u6682\u65e0\u5efa\u8bae'}</span>
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        </section>
      ) : null}
    </div>
  )
}

function createMissingWarning(key, title) {
  return {
    key,
    title,
    metric_label: '暂无有效监测数据',
    level: '暂无数据',
    level_code: 'unavailable',
    score: 0,
    display_value: '--',
    band: '--',
    rule_text: '',
    summary: `${title}当前缺少有效数据。`,
    action: '继续补齐监测数据后再开展同口径判定。',
  }
}
