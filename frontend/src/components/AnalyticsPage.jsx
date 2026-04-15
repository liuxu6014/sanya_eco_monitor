import { useCallback } from 'react'
import { usePolling } from '../hooks/usePolling.js'
import { api } from '../utils/api.js'
import InsectHeatmapChart from './InsectHeatmapChart.jsx'
import CombinedTrendChart from './CombinedTrendChart.jsx'
import WaterQualityDailyChart from './WaterQualityDailyChart.jsx'
import RunoffDailyChart from './RunoffDailyChart.jsx'
import DeepInsightPanel from './DeepInsightPanel.jsx'
import s from './AnalyticsPage.module.css'

// Professional Dashboard Icons (copied for standalone page usage)
const IconDeep = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.29 7 12 12 20.71 7"/><line x1="12" y1="22" x2="12" y2="12"/></svg>;
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

      <div className={s.row}>
        <ChartCard title="30日水质负荷趋势" icon={<IconWater />} extra="COD / 氨氮 / 总磷 / 溶解氧 / 水温" style={{ flex: 1 }}>
          <WaterQualityDailyChart data={wqDaily.data} />
        </ChartCard>
        <ChartCard title="30日水土流失动态" icon={<IconRunoff />} extra="含沙量 / 降雨 / 流量动态" style={{ flex: 1 }}>
          <RunoffDailyChart data={runoffDaily.data} />
        </ChartCard>
      </div>

      <div className={s.row}>
        <ChartCard title="虫情·孢子联合走势" icon={<IconInsect />} extra="近30日双轴关联" style={{ flex: 1 }}>
          <CombinedTrendChart data={combinedTrend.data} />
        </ChartCard>
        <ChartCard title="全区虫种分布热力" icon={<IconHeat />} extra="多点实时聚合" style={{ flex: 1 }}>
          <InsectHeatmapChart data={insectHeatmap.data} />
        </ChartCard>
      </div>
    </div>
  )
}
