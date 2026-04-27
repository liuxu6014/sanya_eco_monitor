import ReactECharts from 'echarts-for-react'
import s from './GuidelineMetricsPanel.module.css'

function valueText(value, suffix = '') {
  if (value === null || value === undefined || value === '') return '—'
  return `${value}${suffix}`
}

function statusTone(status) {
  if (['可做', '可展示', '已有', '已具备', '已补充'].includes(status)) return s.ok
  if (['可加工展示', '部分可做', '部分具备', '部分已有', '部分补充', '补强后可升级'].includes(status)) return s.warn
  return s.neutral
}

function StatusTag({ status }) {
  if (!status) return null
  return <span className={`${s.status} ${statusTone(status)}`}>{status}</span>
}

function EmptyBlock({ label }) {
  return <div className={s.emptyBlock}>{label}</div>
}

function kpiCard(title, value, note, accent) {
  return { title, value, note, accent }
}

function riskScore(level) {
  if (level === '高') return 88
  if (level === '中') return 62
  return 28
}

export default function GuidelineMetricsPanel({ data }) {
  const payload = data?.data || data || {}
  const runoff = payload.runoff_erosion || {}
  const water = payload.water_quality || {}
  const pest = payload.pest_management || {}
  const weather = payload.weather_support || {}
  const historySummary = weather.history_summary || {}
  const waterSourceSupport = payload.water_source_support || {}
  const matrix = payload.implementation_matrix || {}

  const stationMetrics = runoff.station_metrics || []
  const waterMetrics = water.metrics || []
  const foundation = matrix.current_foundation || []
  const closureItems = matrix.management_closure || []
  const rules = matrix.confirmed_rules || []

  const kpis = [
    kpiCard('估算减蚀率', valueText(runoff.estimated_reduction_rate, '%'), '次生林参照口径', 'cyan'),
    kpiCard('污染削减综合率', valueText(water.composite_reduction_rate, '%'), '4项指标阶段结果', 'gold'),
    kpiCard('虫害风险等级', valueText(pest.risk_level), '虫情 + 孢子协同研判', 'rose'),
    kpiCard('系统基准期', valueText(water.baseline_period?.days, '天'), '不足30天按已有天数', 'green'),
  ]

  const erosionOption = stationMetrics.length
    ? {
        backgroundColor: 'transparent',
        animation: false,
        grid: { top: 12, right: 18, bottom: 12, left: 80, containLabel: true },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          backgroundColor: 'rgba(3,17,46,0.96)',
          borderColor: 'rgba(56,189,248,0.45)',
          textStyle: { color: '#e0f2fe', fontSize: 11 },
        },
        xAxis: {
          type: 'value',
          axisLabel: { color: '#86b9d6', fontSize: 11 },
          splitLine: { lineStyle: { color: 'rgba(56,189,248,0.08)', type: 'dotted' } },
          axisLine: { show: false },
          axisTick: { show: false },
        },
        yAxis: {
          type: 'category',
          data: stationMetrics.map((item) => item.name),
          axisLabel: { color: '#d9ecff', fontSize: 11 },
          axisLine: { show: false },
          axisTick: { show: false },
        },
        series: [
          {
            type: 'bar',
            data: stationMetrics.map((item) => ({
              value: item.erosion_proxy,
              itemStyle: {
                color: item.device_code === runoff.reference_station?.device_code
                  ? '#2dd4bf'
                  : '#38bdf8',
                borderRadius: [0, 8, 8, 0],
              },
            })),
            barWidth: 12,
            label: {
              show: true,
              position: 'right',
              color: '#d9ecff',
              fontSize: 11,
              formatter: ({ value }) => valueText(value),
            },
          },
        ],
      }
    : null

  const reductionOption = waterMetrics.length
    ? {
        backgroundColor: 'transparent',
        animation: false,
        grid: { top: 18, right: 18, bottom: 12, left: 54, containLabel: true },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          backgroundColor: 'rgba(3,17,46,0.96)',
          borderColor: 'rgba(250,204,21,0.35)',
          textStyle: { color: '#fff7d6', fontSize: 11 },
        },
        xAxis: {
          type: 'value',
          axisLabel: { color: '#b8cad9', fontSize: 11, formatter: '{value}%' },
          splitLine: { lineStyle: { color: 'rgba(250,204,21,0.08)', type: 'dotted' } },
          axisLine: { show: false },
          axisTick: { show: false },
        },
        yAxis: {
          type: 'category',
          data: waterMetrics.map((item) => item.label.replace('（按COD替代表达）', '')),
          axisLabel: { color: '#f5fbff', fontSize: 11 },
          axisLine: { show: false },
          axisTick: { show: false },
        },
        series: [
          {
            type: 'bar',
            barWidth: 12,
            data: waterMetrics.map((item) => ({
              value: item.recent_reduction_rate ?? 0,
              itemStyle: {
                color: item.recent_reduction_rate >= 0 ? '#facc15' : '#f87171',
                borderRadius: [0, 8, 8, 0],
              },
            })),
            label: {
              show: true,
              position: 'right',
              color: '#f8fafc',
              fontSize: 11,
              formatter: ({ value }) => valueText(value, '%'),
            },
          },
        ],
      }
    : null

  const riskOption = {
    backgroundColor: 'transparent',
    animation: false,
    series: [
      {
        type: 'gauge',
        startAngle: 220,
        endAngle: -40,
        min: 0,
        max: 100,
        radius: '96%',
        pointer: { show: false },
        progress: {
          show: true,
          width: 14,
          roundCap: true,
          itemStyle: {
            color: pest.risk_level === '高' ? '#f87171' : pest.risk_level === '中' ? '#facc15' : '#2dd4bf',
          },
        },
        axisLine: {
          lineStyle: {
            width: 14,
            color: [[1, 'rgba(255,255,255,0.08)']],
          },
        },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        detail: {
          valueAnimation: false,
          offsetCenter: [0, '4%'],
          formatter: () => `{level|${pest.risk_level || '—'}}\n{score|${riskScore(pest.risk_level)}}`,
          rich: {
            level: {
              fontSize: 28,
              fontWeight: 800,
              color: '#f8fafc',
              lineHeight: 34,
            },
            score: {
              fontSize: 12,
              color: '#8fb6da',
              lineHeight: 20,
            },
          },
        },
        data: [{ value: riskScore(pest.risk_level) }],
      },
    ],
  }

  return (
    <div className={s.wrap}>
      <div className={s.kpiRow}>
        {kpis.map((item) => (
          <div key={item.title} className={`${s.kpiCard} ${s[item.accent]}`}>
            <div className={s.kpiLabel}>{item.title}</div>
            <div className={s.kpiValue}>{item.value}</div>
            <div className={s.kpiNote}>{item.note}</div>
          </div>
        ))}
      </div>

      <div className={s.heroGrid}>
        <section className={s.panel}>
          <div className={s.panelHead}>
            <div>
              <div className={s.title}>水土流失对照评估</div>
              <div className={s.subtitle}>现有径流、含沙量、雨量数据整合后的监测型结果</div>
            </div>
            <StatusTag status="可展示" />
          </div>
          <div className={s.chartArea}>
            {erosionOption ? (
              <ReactECharts option={erosionOption} style={{ width: '100%', height: '100%' }} notMerge opts={{ renderer: 'canvas' }} />
            ) : (
              <EmptyBlock label="暂无径流加工结果" />
            )}
          </div>
          <div className={s.footLine}>
            <span>参照样地：{valueText(runoff.reference_station?.name)}</span>
            <span>工程尺度减蚀：{valueText(runoff.estimated_reduction_rate, '%')}</span>
          </div>
        </section>

        <section className={s.panel}>
          <div className={s.panelHead}>
            <div>
              <div className={s.title}>农业面源污染削减画像</div>
              <div className={s.subtitle}>基准期、近30天与最新值的加工对比结果</div>
            </div>
            <StatusTag status="可展示" />
          </div>
          <div className={s.chartArea}>
            {reductionOption ? (
              <ReactECharts option={reductionOption} style={{ width: '100%', height: '100%' }} notMerge opts={{ renderer: 'canvas' }} />
            ) : (
              <EmptyBlock label="暂无水质加工结果" />
            )}
          </div>
          <div className={s.metricStrip}>
            {waterMetrics.map((item) => (
              <div className={s.metricMini} key={item.field}>
                <div className={s.metricName}>{item.label.replace('（按COD替代表达）', '')}</div>
                <div className={s.metricNumbers}>
                  <span>基准 {valueText(item.baseline_avg)}</span>
                  <span>最新 {valueText(item.latest_value)}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className={s.midGrid}>
        <section className={s.panel}>
          <div className={s.panelHead}>
            <div>
              <div className={s.title}>虫情与孢子协同风险</div>
              <div className={s.subtitle}>基于峰值、主要虫种和预警阈值的阶段研判</div>
            </div>
            <StatusTag status="可展示" />
          </div>
          <div className={s.riskGrid}>
            <div className={s.riskGauge}>
              <ReactECharts option={riskOption} style={{ width: '100%', height: '100%' }} notMerge opts={{ renderer: 'canvas' }} />
            </div>
            <div className={s.riskInfo}>
              <div className={s.riskCard}>
                <div className={s.riskLabel}>虫情峰值</div>
                <div className={s.riskValue}>{valueText(pest.insect_peak?.date)}</div>
                <div className={s.riskText}>{valueText(pest.insect_peak?.count, '只')} / {valueText(pest.top_species?.name)}</div>
              </div>
              <div className={s.riskCard}>
                <div className={s.riskLabel}>孢子峰值</div>
                <div className={s.riskValue}>{valueText(pest.spore_peak?.date)}</div>
                <div className={s.riskText}>{valueText(pest.spore_peak?.count, '个')}</div>
              </div>
              <div className={s.storyBox}>{pest.chain_text || '当前暂无病虫协同研判文本'}</div>
            </div>
          </div>
        </section>

        <section className={s.panel}>
          <div className={s.panelHead}>
            <div>
              <div className={s.title}>加工展示与支撑信息</div>
              <div className={s.subtitle}>只展示当前有数据基础、经整合后可形成的内容</div>
            </div>
            <StatusTag status={weather.enabled && weather.status === 'ok' ? '可加工展示' : '部分补充'} />
          </div>
          <div className={s.supportCards}>
            <div className={s.supportCard}>
              <div className={s.supportLabel}>系统基准期规则</div>
              <div className={s.supportValue}>{valueText(water.baseline_period?.days, '天')}</div>
              <div className={s.supportText}>{water.baseline_period?.note}</div>
            </div>
            <div className={s.supportCard}>
              <div className={s.supportLabel}>水源涵养支撑分析</div>
              <div className={s.supportValue}>
                {weather.enabled && weather.status === 'ok' ? valueText(historySummary.total_precip, 'mm') : '—'}
              </div>
              {waterSourceSupport.message ? <div className={s.supportText}>{waterSourceSupport.message}</div> : null}
            </div>
            <div className={s.supportCard}>
              <div className={s.supportLabel}>污染削减能力提升率</div>
              <div className={s.supportValue}>{valueText(water.composite_reduction_rate, '%')}</div>
              <div className={s.supportText}>当前展示浓度改善率和阶段削减效果，不展示严格负荷削减结果。</div>
            </div>
          </div>
          <div className={s.weatherStrip}>
            <div className={s.weatherChip}>当前天气 {valueText(weather.current?.text)}</div>
            <div className={s.weatherChip}>温度 {valueText(weather.current?.temp, '℃')}</div>
            <div className={s.weatherChip}>湿度 {valueText(weather.current?.humidity, '%')}</div>
            <div className={s.weatherChip}>风速 {valueText(weather.current?.wind_speed, ' km/h')}</div>
          </div>
        </section>
      </div>

      <div className={s.bottomGrid}>
        <section className={s.panel}>
          <div className={s.panelHead}>
            <div>
              <div className={s.title}>现有数据基础整合</div>
              <div className={s.subtitle}>已有监测能力统一转成大屏展示标签</div>
            </div>
          </div>
          <div className={s.foundationWall}>
            {foundation.map((item) => (
              <div className={s.foundationItem} key={item.name}>
                <div className={s.foundationTop}>
                  <strong>{item.name}</strong>
                  <StatusTag status={item.status} />
                </div>
                <div className={s.foundationText}>{item.detail}</div>
              </div>
            ))}
          </div>
        </section>

        <section className={s.sideStack}>
          <section className={s.panel}>
            <div className={s.title}>已确认业务规则</div>
            <div className={s.ruleList}>
              {rules.map((item) => (
                <div className={s.ruleItem} key={item}>{item}</div>
              ))}
            </div>
          </section>

          <section className={s.panel}>
            <div className={s.title}>管理闭环表达</div>
            <div className={s.closureList}>
              {closureItems.map((item) => (
                <div className={s.closureItem} key={item.name}>
                  <div className={s.closureHead}>
                    <strong>{item.name}</strong>
                    <StatusTag status={item.status} />
                  </div>
                  <div className={s.closureText}>{item.current}</div>
                  <div className={s.closureNeed}>{item.needed}</div>
                </div>
              ))}
            </div>
          </section>
        </section>
      </div>
    </div>
  )
}
