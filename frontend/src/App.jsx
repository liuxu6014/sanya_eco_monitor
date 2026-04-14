import { useCallback, useEffect, useState } from 'react'
import Header from './components/Header.jsx'
import WeatherPanel from './components/WeatherPanel.jsx'
import SoilPanel from './components/SoilPanel.jsx'
import InsectPanel from './components/InsectPanel.jsx'
import SporePanel from './components/SporePanel.jsx'
import MapCenter from './components/MapCenter.jsx'
import RunoffPanel from './components/RunoffPanel.jsx'
import WaterPanel from './components/WaterPanel.jsx'
import AnalyticsPage from './components/AnalyticsPage.jsx'
import ReportManager from './components/ReportManager.jsx'
import AutoResizer from './components/AutoResizer.jsx'
import LoginGate from './components/LoginGate.jsx'
import { usePolling } from './hooks/usePolling.js'
import { api } from './utils/api.js'
import s from './App.module.css'

const IconWeather = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.5 19A4.5 4.5 0 0 0 18 10c-.8-4.4-5.8-6-9-2.5A5.5 5.5 0 0 0 3.5 12C1.5 12.5 1 15.5 2.5 17c1.5 1.5 3 2 4.5 2h10.5z" /></svg>
const IconSoil = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00ff9d" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2.5 12c4 0 6-3 8-3s4 3 8 3c1.5 0 2-1 2-2.5S19 7 12 7 2.5 9 2.5 12z" /><path d="M2.5 17c4 0 6-3 8-3s4 3 8 3" /></svg>
const IconRunoff = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 8v6a5 5 0 0 1-5 5H8a5 5 0 0 1-5-5V8" /><path d="M3 13l4-4 4 4 4-4 6 6" /></svg>
const IconWater = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#facc15" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-7.5c-.5 3.5-2 5.9-4 7.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z" /><path d="M9 15a3 3 0 0 0 3 3" /></svg>
const IconInsect = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2A4 4 0 0 0 8 6v2h8V6a4 4 0 0 0-4-4z" /><path d="M6 10h12v7a6 6 0 0 1-12 0v-7z" /><path d="M4 14l3-3" /><path d="M20 14l-3-3" /><path d="M4 18l3-3" /><path d="M20 18l-3-3" /><path d="M22 6l-3 3" /><path d="M2 6l3 3" /><path d="M12 22v-5" /></svg>
const IconSpore = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#d946ef" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" /><path d="M12 8v4" /><path d="M12 16h.01" /><path d="M7 11h.01" /><path d="M17 11h.01" /><path d="M9 15h.01" /><path d="M15 15h.01" /></svg>

const POLL = 30_000

function Panel({ title, extra, icon, children, style }) {
  return (
    <div className="panel" style={style}>
      <span className="panel-tr" />
      <span className="panel-bl" />
      <div className="panel-title">
        <span className="stripe" />
        {icon && <span>{icon}</span>}
        {title}
        {extra && <span className="extra">{extra}</span>}
      </div>
      <div className="panel-body">{children}</div>
    </div>
  )
}

function DashboardApp() {
  const [activeTab, setActiveTab] = useState('overview')
  const overview = usePolling(useCallback(() => api.overview(), []), POLL)
  const devices = usePolling(useCallback(() => api.deviceStatus(), []), POLL)
  const insectLatest = usePolling(useCallback(() => api.insectLatest(), []), POLL)
  const insectTrend = usePolling(useCallback(() => api.insectTrend(7), []), POLL)
  const insectSpecies = usePolling(useCallback(() => api.insectSpecies(7), []), POLL)
  const sporeLatest = usePolling(useCallback(() => api.sporeLatest(), []), POLL)
  const sporeTrend = usePolling(useCallback(() => api.sporeTrend(7), []), POLL)
  const weatherLatest = usePolling(useCallback(() => api.weatherLatest(), []), POLL)
  const weatherTrend = usePolling(useCallback(() => api.weatherTrend(24), []), POLL)
  const soilLatest = usePolling(useCallback(() => api.soilLatest(), []), POLL)
  const soilTrend = usePolling(useCallback(() => api.soilTrend(24), []), POLL)

  const handleTrigger = async () => {
    try {
      await api.triggerCollect()
      setTimeout(() => {
        [
          overview,
          devices,
          insectLatest,
          insectTrend,
          insectSpecies,
          sporeLatest,
          sporeTrend,
          weatherLatest,
          weatherTrend,
          soilLatest,
          soilTrend,
        ].forEach((hook) => hook.refetch())
      }, 3000)
    } catch {}
  }

  return (
    <AutoResizer>
      <div className={s.app}>
        <Header onTriggerCollect={handleTrigger} activeTab={activeTab} onTabChange={setActiveTab} />

        {activeTab === 'analytics' && <AnalyticsPage />}
        {activeTab === 'reports' && <ReportManager />}

        <div className={s.body} style={{ display: activeTab === 'overview' ? undefined : 'none' }}>
          <div className={s.col}>
            <Panel title="微气象与光照" icon={<IconWeather />} extra="实时" style={{ flex: '1.2' }}>
              <WeatherPanel weather={weatherLatest.data} trend={weatherTrend.data} />
            </Panel>

            <Panel title="智慧土壤与肥力" icon={<IconSoil />} extra="实时" style={{ flex: '1.2' }}>
              <SoilPanel soil={overview.data?.soil} trend={soilTrend.data} />
            </Panel>

            <Panel title="水土流失与径流" icon={<IconRunoff />} extra="监测网络" style={{ flex: '1' }}>
              <RunoffPanel runoffStations={overview.data?.runoff_stations} />
            </Panel>
          </div>

          <div className={s.mapWrap}>
            <MapCenter overview={overview.data} />
          </div>

          <div className={s.col}>
            <Panel title="面源水质污染负荷" icon={<IconWater />} extra="告警监控" style={{ flex: '1.2' }}>
              <WaterPanel water={overview.data?.water_quality} />
            </Panel>

            <Panel title="虫情预警网络" icon={<IconInsect />} extra="7日" style={{ flex: '1.4' }}>
              <InsectPanel latest={insectLatest.data} trend={insectTrend.data} species={insectSpecies.data} />
            </Panel>

            <Panel title="空气孢子捕捉分析" icon={<IconSpore />} extra="状态监测" style={{ flex: '0.8' }}>
              <SporePanel latest={sporeLatest.data} trend={sporeTrend.data} />
            </Panel>
          </div>
        </div>
      </div>
    </AutoResizer>
  )
}

export default function App() {
  const [authLoading, setAuthLoading] = useState(true)
  const [authenticated, setAuthenticated] = useState(false)

  const checkAuth = useCallback(async () => {
    try {
      const result = await api.authStatus()
      setAuthenticated(Boolean(result?.authenticated))
    } catch {
      setAuthenticated(false)
    } finally {
      setAuthLoading(false)
    }
  }, [])

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  useEffect(() => {
    const handleUnauthorized = () => {
      setAuthenticated(false)
      setAuthLoading(false)
    }

    window.addEventListener('auth:unauthorized', handleUnauthorized)
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized)
  }, [])

  if (authLoading) {
    return (
      <div className={s.app} style={{ display: 'grid', placeItems: 'center' }}>
        <div style={{ color: '#dce8ff', fontSize: 16 }}>正在校验访问权限...</div>
      </div>
    )
  }

  if (!authenticated) {
    return <LoginGate onSuccess={() => setAuthenticated(true)} />
  }

  return <DashboardApp />
}
