import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react'
import Header from './components/Header.jsx'
import DeviceStatusPanel from './components/DeviceStatusPanel.jsx'
import RainGaugePanel from './components/RainGaugePanel.jsx'
import InsectPanel from './components/InsectPanel.jsx'
import SporePanel from './components/SporePanel.jsx'
import MapCenter from './components/MapCenter.jsx'
import RunoffPanel from './components/RunoffPanel.jsx'
import WaterPanel from './components/WaterPanel.jsx'
import AutoResizer from './components/AutoResizer.jsx'
import LoginGate from './components/LoginGate.jsx'
import { usePolling } from './hooks/usePolling.js'
import { api } from './utils/api.js'
import { clearRequestCache } from './utils/requestCache.js'
import { DEFAULT_TAB, TAB_STORAGE_KEY, resolveInitialTab, tabFromLocation, tabPath } from './utils/navigationTabs.js'
import s from './App.module.css'

const AnalyticsPage = lazy(() => import('./components/AnalyticsPage.jsx'))
const SpecialAnalysisPage = lazy(() => import('./components/SpecialAnalysisPage.jsx'))
const ReportManager = lazy(() => import('./components/ReportManager.jsx'))

const IconWeather = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.5 19A4.5 4.5 0 0 0 18 10c-.8-4.4-5.8-6-9-2.5A5.5 5.5 0 0 0 3.5 12C1.5 12.5 1 15.5 2.5 17c1.5 1.5 3 2 4.5 2h10.5z" /></svg>
const IconPulse = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4ade80" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>;
const IconRunoff = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 8v6a5 5 0 0 1-5 5H8a5 5 0 0 1-5-5V8" /><path d="M3 13l4-4 4 4 4-4 6 6" /></svg>
const IconWater = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#facc15" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-7.5c-.5 3.5-2 5.9-4 7.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z" /><path d="M9 15a3 3 0 0 0 3 3" /></svg>
const IconInsect = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2A4 4 0 0 0 8 6v2h8V6a4 4 0 0 0-4-4z" /><path d="M6 10h12v7a6 6 0 0 1-12 0v-7z" /><path d="M4 14l3-3" /><path d="M20 14l-3-3" /><path d="M4 18l3-3" /><path d="M20 18l-3-3" /><path d="M22 6l-3 3" /><path d="M2 6l3 3" /><path d="M12 22v-5" /></svg>
const IconSpore = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#d946ef" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" /><path d="M12 8v4" /><path d="M12 16h.01" /><path d="M7 11h.01" /><path d="M17 11h.01" /><path d="M9 15h.01" /><path d="M15 15h.01" /></svg>

const POLL = 30_000

function formatWaterUpdatedAt(value) {
  if (!value) return null

  const text = String(value).replace('T', ' ')
  const match = text.match(/^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})/)
  return match ? `${match[1]} ${match[2]}` : text
}

function getInitialTab() {
  if (typeof window === 'undefined') {
    return DEFAULT_TAB
  }

  try {
    return resolveInitialTab(
      window.location.pathname,
      window.location.hash,
      window.localStorage.getItem(TAB_STORAGE_KEY),
    )
  } catch {
    return resolveInitialTab(window.location.pathname, window.location.hash, null)
  }
}

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

function GlobalNotice({ notice, onClose }) {
  if (!notice) {
    return null
  }

  const iconPath = notice.type === 'error'
    ? 'M12 9v4m0 4h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z'
    : notice.type === 'success'
      ? 'M20 6 9 17l-5-5'
      : 'M12 8h.01M11 12h1v4h1'

  return (
    <div className={s.globalNoticeLayer} role="status" aria-live="polite">
      <div className={`${s.globalNotice} ${s[notice.type] || ''}`}>
        <div className={s.noticeIcon} aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
            <path d={iconPath} />
          </svg>
        </div>
        <div className={s.noticeText}>
          <strong>{notice.title}</strong>
          <span>{notice.message}</span>
        </div>
        <button type="button" className={s.noticeClose} onClick={onClose} aria-label="关闭提示">
          关闭
        </button>
      </div>
    </div>
  )
}

function TabLoadingState({ label }) {
  return (
    <div className={s.app} style={{ display: 'grid', placeItems: 'center', minHeight: '100%' }}>
      <div style={{ color: '#dce8ff', fontSize: 16 }}>{label}加载中...</div>
    </div>
  )
}

function DashboardApp({ onLogout }) {
  const [activeTab, setActiveTab] = useState(getInitialTab)
  const [mountedTabs, setMountedTabs] = useState({
    overview: activeTab === 'overview',
    analytics: activeTab === 'analytics',
    special: activeTab === 'special',
    reports: activeTab === 'reports',
  })
  const [globalNotice, setGlobalNotice] = useState(null)
  const noticeTimerRef = useRef(null)
  const pollingOptions = useCallback((cacheKey) => ({
    cacheKey,
    persist: false,
    staleMs: POLL,
  }), [])
  const overview = usePolling(useCallback(() => api.overview(), []), POLL, pollingOptions('overview'))
  const devices = usePolling(useCallback(() => api.deviceStatus(), []), POLL, pollingOptions('device-status'))
  const insectLatest = usePolling(useCallback(() => api.insectLatest(), []), POLL, pollingOptions('insect-latest'))
  const insectTrend = usePolling(useCallback(() => api.insectTrend(7), []), POLL, pollingOptions('insect-trend-7d'))
  const insectSpecies = usePolling(useCallback(() => api.insectSpecies(30), []), POLL, pollingOptions('insect-species-30d'))
  const sporeLatest = usePolling(useCallback(() => api.sporeLatest(), []), POLL, pollingOptions('spore-latest'))
  const sporeTrend = usePolling(useCallback(() => api.sporeTrend(7), []), POLL, pollingOptions('spore-trend-7d'))
  const waterUpdatedAt = formatWaterUpdatedAt(overview.data?.data?.water_quality?.updated_at)

  useEffect(() => {
    clearRequestCache('overview')
    clearRequestCache('device-status')
    clearRequestCache('insect-latest')
    clearRequestCache('insect-trend-7d')
    clearRequestCache('insect-species-30d')
    clearRequestCache('spore-latest')
    clearRequestCache('spore-trend-7d')
  }, [])

  useEffect(() => {
    setMountedTabs((current) => (
      current[activeTab]
        ? current
        : { ...current, [activeTab]: true }
    ))

    if (typeof window === 'undefined') {
      return
    }

    try {
      window.localStorage.setItem(TAB_STORAGE_KEY, activeTab)
    } catch {}

    const nextPath = tabPath(activeTab)
    const currentPath = `${window.location.pathname}${window.location.search}` || '/'
    if (currentPath !== nextPath || window.location.hash) {
      window.history.replaceState(null, '', nextPath)
    }
  }, [activeTab])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined
    }

    const handleLocationChange = () => {
      const nextTab = tabFromLocation(window.location.pathname, window.location.hash)
      if (nextTab) {
        setActiveTab(nextTab)
      }
    }

    window.addEventListener('popstate', handleLocationChange)
    window.addEventListener('hashchange', handleLocationChange)
    return () => {
      window.removeEventListener('popstate', handleLocationChange)
      window.removeEventListener('hashchange', handleLocationChange)
    }
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined
    }

    const handleRefresh = () => {
      overview.refetch().catch(() => {})
      devices.refetch().catch(() => {})
      insectLatest.refetch().catch(() => {})
      insectTrend.refetch().catch(() => {})
      insectSpecies.refetch().catch(() => {})
      sporeLatest.refetch().catch(() => {})
      sporeTrend.refetch().catch(() => {})
    }

    window.addEventListener('app:refresh-data', handleRefresh)
    return () => window.removeEventListener('app:refresh-data', handleRefresh)
  }, [devices, insectLatest, insectSpecies, insectTrend, overview, sporeLatest, sporeTrend])

  const handleTrigger = async () => {
    window.dispatchEvent(new CustomEvent('app:refresh-data'))
  }

  const handleLogout = async () => {
    try {
      await api.authLogout()
    } catch (error) {
      console.error(error)
    } finally {
      onLogout()
    }
  }

  const showGlobalNotice = useCallback((notice) => {
    setGlobalNotice(notice)

    if (typeof window !== 'undefined') {
      window.clearTimeout(noticeTimerRef.current)
      noticeTimerRef.current = window.setTimeout(() => {
        setGlobalNotice(null)
      }, 9000)
    }
  }, [])

  useEffect(() => () => {
    if (typeof window !== 'undefined') {
      window.clearTimeout(noticeTimerRef.current)
    }
  }, [])

  return (
    <AutoResizer>
      <div className={s.app}>
        <GlobalNotice notice={globalNotice} onClose={() => setGlobalNotice(null)} />

        <Header
          onTriggerCollect={handleTrigger}
          onLogout={handleLogout}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />

        {mountedTabs.analytics && (
          <div
            className={s.tabPane}
            style={{ display: activeTab === 'analytics' ? 'flex' : 'none' }}
          >
            <Suspense fallback={<TabLoadingState label="数据分析" />}>
              <AnalyticsPage active={activeTab === 'analytics'} />
            </Suspense>
          </div>
        )}
        {mountedTabs.special && (
          <div
            className={s.tabPane}
            style={{ display: activeTab === 'special' ? 'flex' : 'none' }}
          >
            <Suspense fallback={<TabLoadingState label="专项分析" />}>
              <SpecialAnalysisPage active={activeTab === 'special'} />
            </Suspense>
          </div>
        )}
        {mountedTabs.reports && (
          <div
            className={s.tabPane}
            style={{ display: activeTab === 'reports' ? 'flex' : 'none' }}
          >
            <Suspense fallback={<TabLoadingState label="报告管理" />}>
              <ReportManager onNotice={showGlobalNotice} />
            </Suspense>
          </div>
        )}

        <div className={s.body} style={{ display: activeTab === 'overview' ? undefined : 'none' }}>
          <div className={s.col}>
            <Panel title="设备物联网络状态" icon={<IconPulse />} style={{ flex: '1.4' }}>
              <DeviceStatusPanel devices={devices.data} />
            </Panel>

            <Panel title="区域降雨" icon={<IconWeather />} style={{ flex: '1' }}>
              <RainGaugePanel
                rainData={overview.data?.data?.rain_gauges}
                deviceMeta={overview.data?.data?.device_meta?.rain_gauges}
              />
            </Panel>

            <Panel title="水土流失与径流" icon={<IconRunoff />} style={{ flex: '1' }}>
              <RunoffPanel
                runoffStations={overview.data?.data?.runoff_stations}
                deviceMeta={overview.data?.data?.device_meta?.runoff_devices}
              />
            </Panel>
          </div>

          <div className={s.mapWrap}>
            <MapCenter
              overview={overview.data?.data}
              deviceMeta={overview.data?.data?.device_meta}
              active={activeTab === 'overview'}
            />
          </div>

          <div className={s.col}>
            <Panel title="面源水质污染负荷" extra={waterUpdatedAt} icon={<IconWater />} style={{ flex: '1.2' }}>
              <WaterPanel water={overview.data?.data?.water_quality} />
            </Panel>

            <Panel title="虫情预警" icon={<IconInsect />} style={{ flex: '2.2' }}>
              <InsectPanel latest={insectLatest.data} trend={insectTrend.data} species={insectSpecies.data} />
            </Panel>

            <Panel title="空气孢子捕捉分析" icon={<IconSpore />} style={{ flex: '0.8' }}>
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

  return <DashboardApp onLogout={() => setAuthenticated(false)} />
}
