import ReactECharts from 'echarts-for-react'
import s from './WeatherSupportPanel.module.css'

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

function formatWind(item) {
  if (!item) {
    return '--'
  }

  const speed = valueText(item.wind_speed_max, ' km/h')
  const direction = item.wind_direction_text || valueText(item.wind_direction, '°')
  return direction === '--' ? speed : `${speed} / ${direction}`
}

function formatWindSpeed(value) {
  return valueText(value, ' km/h')
}

function OverviewCard({ label, value, meta, wide = false, strong = false }) {
  return (
    <div className={`${s.metricCard} ${wide ? s.metricWide : ''} ${strong ? s.metricStrong : ''}`.trim()}>
      <div className={s.metricLabel}>{label}</div>
      <div className={s.metricValue}>{value}</div>
      {meta ? <div className={s.metricMeta}>{meta}</div> : null}
    </div>
  )
}

export default function WeatherSupportPanel({ data }) {
  const payload = data?.data || data || {}
  const weather = payload.weather_support || {}
  const current = weather.current || {}
  const historyDaily = weather.history_daily || []
  const historySummary = weather.history_summary || {}
  const historyRange = weather.history_range || {}
  const rangeLabel = rangeText(historyRange.start, historyRange.end)
  const latestHistory = historyDaily[historyDaily.length - 1]

  if (!historyDaily.length) {
    return <div className={s.empty}>{weather.message || '暂无最近 7 天历史气象数据'}</div>
  }

  const overviewMetrics = [
    {
      key: 'condition',
      label: '当前天气',
      value: valueText(current.text),
      meta: `体感温度 ${valueText(current.feels_like, '°C')}`,
      strong: true,
    },
    {
      key: 'temp',
      label: '当前温度',
      value: valueText(current.temp, '°C'),
      meta: `体感 ${valueText(current.feels_like, '°C')}`,
    },
    {
      key: 'humidity',
      label: '当前湿度',
      value: valueText(current.humidity, '%'),
      meta: `风速 ${valueText(current.wind_speed, ' km/h')}`,
    },
    {
      key: 'et0',
      label: '近7天估算蒸散',
      value: valueText(historySummary.total_et0_estimate, ' mm'),
      meta: `日均 ${valueText(historySummary.avg_et0_estimate, ' mm/d')}`,
    },
    {
      key: 'precip',
      label: '近7天累计降水',
      value: valueText(historySummary.total_precip, ' mm'),
      meta: `降水日数 ${valueText(historySummary.rainy_days, ' 天')}`,
    },
    {
      key: 'avgHumidity',
      label: '近7天平均湿度',
      value: valueText(historySummary.avg_humidity, '%'),
      meta: `平均气温 ${valueText(historySummary.avg_temp_mean, '°C')}`,
    },
    {
      key: 'avgWind',
      label: '近7天平均最大风速',
      value: valueText(historySummary.avg_wind_speed, ' km/h'),
      meta: `末日最大风速 ${formatWindSpeed(latestHistory?.wind_speed_max)}`,
    },
    {
      key: 'avgRange',
      label: '近7天平均温差',
      value: valueText(historySummary.avg_temp_range, '°C'),
      meta: '昼夜温差参考',
    },
  ]

  const option = {
    backgroundColor: 'transparent',
    animation: false,
    grid: { top: 42, right: 20, bottom: 34, left: 40, containLabel: true },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(4, 18, 44, 0.96)',
      borderColor: 'rgba(56, 189, 248, 0.45)',
      textStyle: { color: '#dbeeff' },
      formatter(params) {
        const point = historyDaily[params?.[0]?.dataIndex ?? -1]
        const rows = [
          point?.date || '--',
          `最高温: ${valueText(point?.temp_max, '°C')}`,
          `最低温: ${valueText(point?.temp_min, '°C')}`,
          `平均湿度: ${valueText(point?.humidity_mean, '%')}`,
          `降水: ${valueText(point?.precip, ' mm')}`,
          `风力: ${formatWind(point)}`,
          `估算蒸散: ${valueText(point?.et0_estimate, ' mm')}`,
        ]
        return rows.join('<br/>')
      },
    },
    legend: {
      top: 8,
      textStyle: { color: '#b0d8f0', fontSize: 11 },
      icon: 'circle',
    },
    xAxis: {
      type: 'category',
      data: historyDaily.map((item) => shortDate(item.date)),
      axisLabel: { color: '#93c5fd', fontSize: 12 },
      axisLine: { lineStyle: { color: 'rgba(56, 189, 248, 0.3)' } },
      axisTick: { show: false },
    },
    yAxis: [
      {
        type: 'value',
        name: '温度 (°C)',
        nameTextStyle: { color: '#38bdf8', fontSize: 10 },
        axisLabel: { color: '#93c5fd', fontSize: 11 },
        axisLine: { show: true, lineStyle: { color: '#38bdf8' } },
        splitLine: { lineStyle: { color: 'rgba(56, 189, 248, 0.08)' } },
      },
      {
        type: 'value',
        name: '降水 (mm)',
        nameTextStyle: { color: '#4ade80', fontSize: 10 },
        axisLabel: { color: '#86efac', fontSize: 11 },
        axisLine: { show: true, lineStyle: { color: '#4ade80' } },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '最高温',
        type: 'line',
        smooth: true,
        data: historyDaily.map((item) => item.temp_max),
        lineStyle: { color: '#38bdf8', width: 2.4 },
        itemStyle: { color: '#38bdf8' },
        showSymbol: false,
      },
      {
        name: '最低温',
        type: 'line',
        smooth: true,
        data: historyDaily.map((item) => item.temp_min),
        lineStyle: { color: '#facc15', width: 2.4 },
        itemStyle: { color: '#facc15' },
        showSymbol: false,
      },
      {
        name: '降水',
        type: 'bar',
        yAxisIndex: 1,
        barMaxWidth: 16,
        data: historyDaily.map((item) => item.precip),
        itemStyle: {
          color: 'rgba(74, 222, 128, 0.48)',
          borderColor: 'rgba(74, 222, 128, 0.85)',
          borderWidth: 1,
          borderRadius: [4, 4, 0, 0],
        },
      },
    ],
  }

  return (
    <div className={s.wrap}>
      <section className={s.overview}>
        <div className={s.overviewHead}>
          <div className={s.sectionEyebrow}>气象概览</div>
          <div className={s.rangePill}>{rangeLabel}</div>
        </div>

        <div className={s.overviewBody}>
          <div className={s.overviewGrid}>
            {overviewMetrics.map((item) => (
              <OverviewCard
                key={item.key}
                label={item.label}
                value={item.value}
                meta={item.meta}
                wide={item.wide}
                strong={item.strong}
              />
            ))}
          </div>
        </div>
      </section>

      <div className={s.chartWrap}>
        <ReactECharts
          option={option}
          style={{ width: '100%', height: '100%' }}
          notMerge
          opts={{ renderer: 'canvas' }}
        />
      </div>
    </div>
  )
}
