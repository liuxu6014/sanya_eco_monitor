import { useCallback } from 'react'
import { usePolling } from '../hooks/usePolling.js'
import { api } from '../utils/api.js'
import WeatherDailyChart from './WeatherDailyChart.jsx'
import WindRoseChart from './WindRoseChart.jsx'
import SoilDailyChart from './SoilDailyChart.jsx'
import InsectHeatmapChart from './InsectHeatmapChart.jsx'
import CombinedTrendChart from './CombinedTrendChart.jsx'
import WaterQualityDailyChart from './WaterQualityDailyChart.jsx'
import RunoffDailyChart from './RunoffDailyChart.jsx'
import DeepInsightPanel from './DeepInsightPanel.jsx'
import s from './AnalyticsPage.module.css'

// Professional Dashboard Icons (copied for standalone page usage)
const IconDeep = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.29 7 12 12 20.71 7"/><line x1="12" y1="22" x2="12" y2="12"/></svg>;
const IconWeather = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.5 19A4.5 4.5 0 0 0 18 10c-.8-4.4-5.8-6-9-2.5A5.5 5.5 0 0 0 3.5 12C1.5 12.5 1 15.5 2.5 17c1.5 1.5 3 2 4.5 2h10.5z"/></svg>;
const IconSoil = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00ff9d" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2.5 12c4 0 6-3 8-3s4 3 8 3c1.5 0 2-1 2-2.5S19 7 12 7 2.5 9 2.5 12z"/><path d="M2.5 17c4 0 6-3 8-3s4 3 8 3"/></svg>;
const IconRunoff = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 8v6a5 5 0 0 1-5 5H8a5 5 0 0 1-5-5V8"/><path d="M3 13l4-4 4 4 4-4 6 6"/></svg>;
const IconWater = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#facc15" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-7.5c-.5 3.5-2 5.9-4 7.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z"/><path d="M9 15a3 3 0 0 0 3 3"/></svg>;
const IconInsect = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2A4 4 0 0 0 8 6v2h8V6a4 4 0 0 0-4-4z"/><path d="M6 10h12v7a6 6 0 0 1-12 0v-7z"/><path d="M4 14l3-3"/><path d="M20 14l-3-3"/><path d="M4 18l3-3"/><path d="M20 18l-3-3"/><path d="M22 6l-3 3"/><path d="M2 6l3 3"/><path d="M12 22v-5"/></svg>;
const IconHeat = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f97316" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>;

const POLL = 60_000

function ChartCard({ title, icon, extra, children, style }) {
  return (
    <div className={s.card} style={style}>
      <span className="panel-tr" /><span className="panel-bl" />
      <div className={s.cardTitle}>
        <span className="stripe" />
        {icon && <span style={{ marginRight: 4 }}>{icon}</span>}
        {title}
        {extra && <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-muted)' }}>{extra}</span>}
      </div>
      <div className={s.cardBody}>{children}</div>
    </div>
  )
}

export default function AnalyticsPage() {
  const weatherDaily   = usePolling(useCallback(() => api.weatherDaily(30), []), POLL)
  const windRose       = usePolling(useCallback(() => api.weatherWindRose(7), []), POLL)
  const soilDaily      = usePolling(useCallback(() => api.soilDaily(30), []), POLL)
  const wqDaily        = usePolling(useCallback(() => api.waterQualityDaily(30), []), POLL)
  const runoffDaily    = usePolling(useCallback(() => api.runoffDaily(30), []), POLL)
  const ecoIndex       = usePolling(useCallback(() => api.ecoIndex(), []), POLL)
  const insectHeatmap  = usePolling(useCallback(() => api.insectHeatmap(14), []), POLL)
  const combinedTrend  = usePolling(useCallback(() => api.insectCombinedTrend(30), []), POLL)

  return (
    <div className={s.page}>
      {/* Strategic Insight Row */}
      <div className={s.rowStrategic}>
        <ChartCard title="决策支持：多源数据深度挖掘" icon={<IconDeep />} extra="生态大脑模型实时输出" style={{ flex: 1 }}>
          <DeepInsightPanel ecoIndex={ecoIndex.data} />
        </ChartCard>
      </div>

      {/* Row 1: Weather & Wind */}
      <div className={s.row}>
        <ChartCard title="30日气象趋势" icon={<IconWeather />} extra="温度 / 湿度 / 降雨" style={{ flex: 2 }}>
          <WeatherDailyChart data={weatherDaily.data} />
        </ChartCard>
        <ChartCard title="风向频率分布" icon={<IconWeather />} extra="近7日" style={{ flex: 1 }}>
          <WindRoseChart data={windRose.data} />
        </ChartCard>
      </div>

      {/* Row 2: Soil & Pests */}
      <div className={s.row}>
        <ChartCard title="30日土壤分析" icon={<IconSoil />} extra="土壤肥力与含水率监测" style={{ flex: 1 }}>
          <SoilDailyChart data={soilDaily.data} />
        </ChartCard>
        <ChartCard title="虫情·孢子联合" icon={<IconInsect />} extra="近30日双轴关联" style={{ flex: 1 }}>
          <CombinedTrendChart data={combinedTrend.data} />
        </ChartCard>
      </div>

      {/* Row 3: Water & Runoff (NEW Professional sections) */}
      <div className={s.row}>
        <ChartCard title="30日水质负荷趋势" icon={<IconWater />} extra="COD / 氨氮 / 总磷分析" style={{ flex: 1 }}>
          <WaterQualityDailyChart data={wqDaily.data} />
        </ChartCard>
        <ChartCard title="30日水土流失动态" icon={<IconRunoff />} extra="含沙量 / 流量对比" style={{ flex: 1 }}>
          <RunoffDailyChart data={runoffDaily.data} />
        </ChartCard>
      </div>

      {/* Row 4: Species Heatmap */}
      <div className={s.rowFull}>
        <ChartCard title="全区虫种分布热力" icon={<IconHeat />} extra="近14日多点聚合">
          <InsectHeatmapChart data={insectHeatmap.data} />
        </ChartCard>
      </div>
    </div>
  )
}
