import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'

const reportCss = readFileSync(new URL('../src/components/ReportManager.module.css', import.meta.url), 'utf8')
const mapCenter = readFileSync(new URL('../src/components/MapCenter.jsx', import.meta.url), 'utf8')
const weatherSupport = readFileSync(new URL('../src/components/WeatherSupportPanel.jsx', import.meta.url), 'utf8')
const analyticsCss = readFileSync(new URL('../src/components/AnalyticsPage.module.css', import.meta.url), 'utf8')
const analyticsPage = readFileSync(new URL('../src/components/AnalyticsPage.jsx', import.meta.url), 'utf8')
const combinedTrend = readFileSync(new URL('../src/components/CombinedTrendChart.jsx', import.meta.url), 'utf8')
const deepInsightPanel = readFileSync(new URL('../src/components/DeepInsightPanel.jsx', import.meta.url), 'utf8')
const waterPanel = readFileSync(new URL('../src/components/WaterPanel.jsx', import.meta.url), 'utf8')
const app = readFileSync(new URL('../src/App.jsx', import.meta.url), 'utf8')
const insectPanel = readFileSync(new URL('../src/components/InsectPanel.jsx', import.meta.url), 'utf8')
const sporePanel = readFileSync(new URL('../src/components/SporePanel.jsx', import.meta.url), 'utf8')
const deviceStatusPanel = readFileSync(new URL('../src/components/DeviceStatusPanel.jsx', import.meta.url), 'utf8')
const waterQualityDailyChart = readFileSync(new URL('../src/components/WaterQualityDailyChart.jsx', import.meta.url), 'utf8')
const runoffDailyChart = readFileSync(new URL('../src/components/RunoffDailyChart.jsx', import.meta.url), 'utf8')
const runoffPanel = readFileSync(new URL('../src/components/RunoffPanel.jsx', import.meta.url), 'utf8')
const insectHeatmapChart = readFileSync(new URL('../src/components/InsectHeatmapChart.jsx', import.meta.url), 'utf8')
const weatherSupportPanel = readFileSync(new URL('../src/components/WeatherSupportPanel.jsx', import.meta.url), 'utf8')
const reportManager = readFileSync(new URL('../src/components/ReportManager.jsx', import.meta.url), 'utf8')
const specialAnalysisPage = readFileSync(new URL('../src/components/SpecialAnalysisPage.jsx', import.meta.url), 'utf8')
const header = readFileSync(new URL('../src/components/Header.jsx', import.meta.url), 'utf8')
const headerCss = readFileSync(new URL('../src/components/Header.module.css', import.meta.url), 'utf8')
const viteConfig = readFileSync(new URL('../vite.config.js', import.meta.url), 'utf8')
const echartAutoResizeHook = readFileSync(new URL('../src/hooks/useEChartAutoResize.js', import.meta.url), 'utf8')
const deviceSeriesExplorer = readFileSync(new URL('../src/components/DeviceSeriesExplorer.jsx', import.meta.url), 'utf8')
const responsiveEChartUrl = new URL('../src/components/ResponsiveEChart.jsx', import.meta.url)
const responsiveEChart = existsSync(responsiveEChartUrl) ? readFileSync(responsiveEChartUrl, 'utf8') : ''

test('report type select options keep dark high-contrast colors', () => {
  assert.match(reportCss, /\.typeSelect option\s*\{[^}]*background:\s*#07162e/im)
  assert.match(reportCss, /\.typeSelect option\s*\{[^}]*color:\s*#f8fbff/im)
})

test('leader report view uses review-focused heading copy', () => {
  assert.match(reportManager, /const headerTitle = role === 'leader' \? '报告批阅' : '报告生成与管理'/)
  assert.match(reportManager, /const leaderSubtitle = '已为您聚合所有合规有效的报告，方便您快速批阅与决策'/)
  assert.match(reportManager, /已为您聚合所有合规有效的报告，方便您快速批阅与决策/)
  assert.doesNotMatch(reportManager, /当前为领导查看权限，仅显示审核通过并开放可见的报告。/)
})

test('report manager filter does not show report type label text', () => {
  assert.doesNotMatch(reportManager, />\s*报告类型\s*</)
})

test('overview map invalidates leaflet size when returning to tab', () => {
  assert.match(mapCenter, /function MapVisibilityController\(\{\s*active,\s*onVisible/)
  assert.match(mapCenter, /map\.invalidateSize\(\)/)
})

test('overview map device stats normalize timeout as abnormal instead of online', () => {
  assert.match(mapCenter, /function normalizeDeviceStatus\(/)
  assert.match(mapCenter, /status === 'timeout'/)
  assert.match(mapCenter, /const onlineDeviceCount = devices\.filter\(\(dev\) => getDeviceStatusValue\(dev,\s*data\) === 'online'\)\.length/)
  assert.match(mapCenter, /const abnormalDeviceCount = devices\.filter\(\(dev\) => getDeviceStatusValue\(dev,\s*data\) !== 'online'\)\.length/)
})

test('overview map renders insect and spore count labels as integers', () => {
  assert.match(mapCenter, /function formatMapLabelValue\(/)
  assert.match(mapCenter, /unit === '只' \|\| unit === '个'/)
  assert.match(mapCenter, /Math\.round\(numericValue\)/)
  assert.doesNotMatch(mapCenter, /const formattedValue = typeof main\.value === 'number' \? main\.value\.toFixed\(2\) : main\.value/)
})

test('map labels do not open floating detail cards on click', () => {
  assert.doesNotMatch(mapCenter, /<DraggableLabel[\s\S]*?onClick=\{\(\) => \{[\s\S]*?setOpenCards/)
})

test('weather chart tooltip escapes clipped chart container', () => {
  assert.match(weatherSupport, /appendToBody:\s*true/)
  assert.match(weatherSupport, /confine:\s*true/)
})

test('analytics card titles center icon and title text', () => {
  assert.match(analyticsCss, /\.cardHeader\s*\{[^}]*align-items:\s*center/im)
  assert.match(analyticsCss, /\.cardHeading\s*\{[^}]*align-items:\s*center/im)
})

test('combined trend chart only renders insect series', () => {
  assert.doesNotMatch(combinedTrend, /sporeData/)
  assert.doesNotMatch(combinedTrend, /name:\s*['"]孢子['"]/)
  assert.doesNotMatch(combinedTrend, /yAxisIndex:\s*1/)
  assert.doesNotMatch(analyticsPage, /虫情与孢子协同趋势/)
})

test('overview water quality panel displays data time beside panel title', () => {
  assert.match(app, /formatWaterUpdatedAt/)
  assert.match(app, /overview\.data\?\.data\?\.water_quality\?\.updated_at/)
  assert.doesNotMatch(waterPanel, /更新时间/)
})

test('device status panel displays concrete device code from backend', () => {
  assert.match(deviceStatusPanel, /\{dev\.code\}/)
  assert.doesNotMatch(deviceStatusPanel, /\{dev\.type\}/)
  assert.match(deviceStatusPanel, /const shouldLoop = d\.length >= 6/)
  assert.match(deviceStatusPanel, /trackRef/)
  assert.match(deviceStatusPanel, /singleGroupRef/)
  assert.match(deviceStatusPanel, /track\.style\.transform/)
  assert.match(deviceStatusPanel, /ResizeObserver/)
  assert.match(deviceStatusPanel, /\{shouldLoop \? \(/)
  assert.match(deviceStatusPanel, /DeviceCard key=\{`\$\{dev\.code\}-clone-\$\{index\}`\}/)
  assert.doesNotMatch(deviceStatusPanel, /scrollTop \+= 0\.5/)
})

test('analytics charts use Chinese-safe axis fonts and visible axis names', () => {
  const chartSources = [
    waterQualityDailyChart,
    runoffDailyChart,
    combinedTrend,
    insectHeatmapChart,
    weatherSupportPanel,
  ]

  for (const source of chartSources) {
    assert.doesNotMatch(source, /fontFamily:\s*['"]monospace['"]/)
    assert.match(source, /CHART_FONT_FAMILY/)
  }

  assert.match(waterQualityDailyChart, /nameTextStyle:\s*\{[^}]*fontFamily:\s*CHART_FONT_FAMILY/s)
  assert.match(runoffDailyChart, /nameTextStyle:\s*\{[^}]*fontFamily:\s*CHART_FONT_FAMILY/s)
  assert.match(combinedTrend, /nameTextStyle:\s*\{[^}]*fontFamily:\s*CHART_FONT_FAMILY/s)
  assert.match(weatherSupportPanel, /nameTextStyle:\s*\{[^}]*fontFamily:\s*CHART_FONT_FAMILY/s)
})

test('analytics charts fill their card bodies and resize with container changes', () => {
  assert.match(analyticsPage, /bodyClassName=\{s\.chartBody\}/)
  assert.match(analyticsCss, /\.chartBody\s*\{[^}]*height:\s*clamp\(330px,\s*32vh,\s*430px\)/im)
  assert.match(analyticsCss, /\.chartBody\s*\{[^}]*overflow:\s*hidden/im)

  for (const source of [waterQualityDailyChart, runoffDailyChart, combinedTrend, insectHeatmapChart]) {
    assert.match(source, /ResponsiveEChart/)
    assert.match(source, /resizeDeps/)
  }

  assert.match(responsiveEChart, /style=\{\{\s*width:\s*'100%',\s*height:\s*'100%'\s*\}\}/)
  assert.match(echartAutoResizeHook, /ResizeObserver/)
  assert.match(echartAutoResizeHook, /getEchartsInstance/)
  assert.match(echartAutoResizeHook, /\.resize\(\)/)
})

test('deep insight radar uses a readable scale for fixed 0-100 indicators', () => {
  assert.match(deepInsightPanel, /indicator:\s*\[[\s\S]*max:\s*100/)
  assert.match(deepInsightPanel, /splitNumber:\s*5/)
})

test('overview insect and spore charts wait for measurable hosts before initializing ECharts', () => {
  assert.match(insectPanel, /ResponsiveEChart/)
  assert.match(sporePanel, /ResponsiveEChart/)
  assert.match(responsiveEChart, /ResizeObserver/)
  assert.match(responsiveEChart, /clientWidth\s*>\s*0/)
  assert.match(responsiveEChart, /clientHeight\s*>\s*0/)
  assert.match(responsiveEChart, /useEChartAutoResize/)
})

test('analytics charts defer ECharts init until their tab hosts have measurable size', () => {
  const analyticsChartSources = [
    waterQualityDailyChart,
    runoffDailyChart,
    combinedTrend,
    insectHeatmapChart,
    weatherSupportPanel,
    deepInsightPanel,
  ]

  for (const source of analyticsChartSources) {
    assert.match(source, /ResponsiveEChart/)
  }

  assert.match(responsiveEChart, /clientWidth\s*>\s*0/)
  assert.match(responsiveEChart, /clientHeight\s*>\s*0/)
})

test('analytics dashboard avoids persisted session cache after refresh', () => {
  assert.match(analyticsPage, /const ECO_INDEX_CACHE_KEY = 'analytics-eco-index'/)
  assert.match(analyticsPage, /const GUIDELINE_CACHE_KEY = 'analytics-guideline-metrics'/)
  assert.match(analyticsPage, /const WQ_DAILY_CACHE_KEY = 'analytics-water-quality-daily'/)
  assert.match(analyticsPage, /const RUNOFF_DAILY_CACHE_KEY = 'analytics-runoff-daily'/)
  assert.match(analyticsPage, /const COMBINED_TREND_CACHE_KEY = 'analytics-combined-trend'/)
  assert.match(analyticsPage, /const HEATMAP_CACHE_KEY = 'analytics-insect-heatmap'/)
  assert.match(analyticsPage, /const POLL = 30_000/)
  assert.match(analyticsPage, /cacheKey:\s*ECO_INDEX_CACHE_KEY/)
  assert.match(analyticsPage, /cacheKey:\s*GUIDELINE_CACHE_KEY/)
  assert.match(analyticsPage, /cacheKey:\s*WQ_DAILY_CACHE_KEY/)
  assert.match(analyticsPage, /cacheKey:\s*RUNOFF_DAILY_CACHE_KEY/)
  assert.match(analyticsPage, /cacheKey:\s*COMBINED_TREND_CACHE_KEY/)
  assert.match(analyticsPage, /cacheKey:\s*HEATMAP_CACHE_KEY/)
  assert.match(analyticsPage, /persist:\s*false/)
  assert.match(analyticsPage, /clearRequestCache\('analysis-dashboard-runtime'\)/)
  assert.match(analyticsPage, /clearRequestCache\('analysis-dashboard'\)/)
})

test('overview polling avoids persisted session cache for live panels', () => {
  assert.match(app, /const pollingOptions = useCallback\(\(cacheKey\) => \(\{/)
  assert.match(app, /persist:\s*false/)
  assert.doesNotMatch(app, /persist:\s*true/)
  assert.match(app, /clearRequestCache\('overview'\)/)
  assert.match(app, /clearRequestCache\('device-status'\)/)
  assert.match(app, /clearRequestCache\('spore-latest'\)/)
  assert.match(app, /clearRequestCache\('spore-trend-7d'\)/)
  assert.doesNotMatch(app, /clearRequestCache\('eco-index'\)/)
})

test('header refresh triggers in-app data refresh instead of full page reload', () => {
  assert.doesNotMatch(app, /window\.location\.reload\(\)/)
  assert.match(app, /window\.dispatchEvent\(new CustomEvent\('app:refresh-data'\)\)/)
  assert.match(app, /overview\.refetch\(\)\.catch\(\(\) => \{\}\)/)
  assert.match(app, /devices\.refetch\(\)\.catch\(\(\) => \{\}\)/)
  assert.doesNotMatch(app, /ecoIndex\.refetch\(\)\.catch\(\(\) => \{\}\)/)
})

test('app lazy-loads non-overview pages and skips unused overview eco index polling', () => {
  assert.match(app, /import \{ lazy, Suspense, useCallback, useEffect, useRef, useState \} from 'react'/)
  assert.match(app, /const AnalyticsPage = lazy\(\(\) => import\('\.\/components\/AnalyticsPage\.jsx'\)\)/)
  assert.match(app, /const SpecialAnalysisPage = lazy\(\(\) => import\('\.\/components\/SpecialAnalysisPage\.jsx'\)\)/)
  assert.match(app, /const ReportManager = lazy\(\(\) => import\('\.\/components\/ReportManager\.jsx'\)\)/)
  assert.doesNotMatch(app, /import AnalyticsPage from '\.\/components\/AnalyticsPage\.jsx'/)
  assert.doesNotMatch(app, /import SpecialAnalysisPage from '\.\/components\/SpecialAnalysisPage\.jsx'/)
  assert.doesNotMatch(app, /import ReportManager from '\.\/components\/ReportManager\.jsx'/)
  assert.doesNotMatch(app, /const ecoIndex = usePolling\(useCallback\(\(\) => api\.ecoIndex\(\), \[\]\), POLL, pollingOptions\('eco-index'\)\)/)
  assert.doesNotMatch(app, /api\.ecoIndex\(\)/)
  assert.match(app, /<Suspense fallback=\{<TabLoadingState label="数据分析" \/>\}>/)
  assert.match(app, /<Suspense fallback=\{<TabLoadingState label="专项分析" \/>\}>/)
  assert.match(app, /<Suspense fallback=\{<TabLoadingState label="报告管理" \/>\}>/)
})

test('analytics page exposes overview and per-device drilldown for rainfall and runoff', () => {
  assert.match(specialAnalysisPage, /import DeviceSeriesExplorer from '\.\/DeviceSeriesExplorer\.jsx'/)
  assert.match(specialAnalysisPage, /import \{\s*clearRequestCache,\s*readRequestCache,\s*writeRequestCache\s*\} from '\.\.\/utils\/requestCache\.js'/)
  assert.match(specialAnalysisPage, /const PREFETCH_SECTIONS = \{/)
  assert.match(specialAnalysisPage, /prefetchSectionData/)
  assert.match(specialAnalysisPage, /window\.requestIdleCallback/)
  assert.match(specialAnalysisPage, /prefetchTargets\.forEach/)
  assert.match(specialAnalysisPage, /const INITIAL_GALLERY_BATCH = \d+/)
  assert.match(specialAnalysisPage, /const GALLERY_BATCH_STEP = \d+/)
  assert.match(specialAnalysisPage, /const \[visibleCount, setVisibleCount\] = useState\(INITIAL_GALLERY_BATCH\)/)
  assert.match(specialAnalysisPage, /IntersectionObserver/)
  assert.match(specialAnalysisPage, /setVisibleCount\(\(count\) => Math\.min\(rows\.length, count \+ GALLERY_BATCH_STEP\)\)/)
  assert.match(specialAnalysisPage, /images\.slice\(0, visibleCount\)/)
  assert.match(specialAnalysisPage, /data-batch-sentinel/)
  assert.match(specialAnalysisPage, /const analysisCacheKey = useMemo\(/)
  assert.match(specialAnalysisPage, /const cachedAnalysis = analysisCacheKey \? readRequestCache\(analysisCacheKey, \{ persist: false \}\) : null/)
  assert.match(specialAnalysisPage, /if \(cachedAnalysis\) \{/)
  assert.match(specialAnalysisPage, /writeRequestCache\(analysisCacheKey, \{ data: nextData, persist: false \}\)/)
  assert.match(specialAnalysisPage, /else \{\s*setData\(null\)\s*setLoading\(true\)/s)
  assert.match(specialAnalysisPage, /if \(loading && !data\) return <div className=\{s\.state\}>/)
  assert.match(specialAnalysisPage, /const rainfallExplorer = usePolling\(/)
  assert.match(specialAnalysisPage, /const runoffExplorer = usePolling\(/)
  assert.match(specialAnalysisPage, /const refreshSection = useCallback\(\(\) => \{/)
  assert.match(specialAnalysisPage, /clearRequestCache\(analysisCacheKey\)/)
  assert.match(specialAnalysisPage, /setRefreshKey\(\(value\) => value \+ 1\)/)
  assert.match(specialAnalysisPage, /rainfallExplorer\.refetch\(\)\.catch\(\(\) => \{\}\)/)
  assert.match(specialAnalysisPage, /runoffExplorer\.refetch\(\)\.catch\(\(\) => \{\}\)/)
  assert.match(specialAnalysisPage, /overviewMetaRequest\.refetch\(\)\.catch\(\(\) => \{\}\)/)
  assert.match(specialAnalysisPage, /window\.setInterval\(refreshSection,\s*30_000\)/)
  assert.doesNotMatch(specialAnalysisPage, /analysisDashboard\(\)/)
  assert.match(specialAnalysisPage, /const rainfallDaily = rainfallExplorer\.data\?\.data \|\| \[\]/)
  assert.match(specialAnalysisPage, /const rainfallDailyByDevice = rainfallExplorer\.data\?\.by_device \|\| \{\}/)
  assert.match(specialAnalysisPage, /const rainfallDailyAnomalySummary = rainfallExplorer\.data\?\.anomaly_summary \|\| \{\}/)
  assert.match(specialAnalysisPage, /const runoffDaily = runoffExplorer\.data\?\.data \|\| \[\]/)
  assert.match(specialAnalysisPage, /const runoffDailyByDevice = runoffExplorer\.data\?\.by_device \|\| \{\}/)
  assert.match(specialAnalysisPage, /const runoffDailyAnomalySummary = runoffExplorer\.data\?\.anomaly_summary \|\| \{\}/)
  assert.match(specialAnalysisPage, /<DeviceSeriesExplorer/)
  assert.match(specialAnalysisPage, /rainfallOverview=\{rainfallDaily\}/)
  assert.match(specialAnalysisPage, /rainfallByDevice=\{rainfallDailyByDevice\}/)
  assert.match(specialAnalysisPage, /rainfallAnomalySummary=\{rainfallDailyAnomalySummary\}/)
  assert.match(specialAnalysisPage, /runoffOverview=\{runoffDaily\}/)
  assert.match(specialAnalysisPage, /runoffByDevice=\{runoffDailyByDevice\}/)
  assert.match(specialAnalysisPage, /runoffAnomalySummary=\{runoffDailyAnomalySummary\}/)
  assert.match(specialAnalysisPage, /allowedModes=\{\['runoff'\]\}/)
  assert.match(specialAnalysisPage, /defaultMode="runoff"/)
  assert.match(specialAnalysisPage, /title="径流设备"/)
  assert.equal((specialAnalysisPage.match(/className=\{s\.fullRow\}/g) || []).length, 2)
  assert.match(specialAnalysisPage, /className=\{s\.fullRow\}/)
  assert.match(specialAnalysisPage, /雨量设备分站趋势/)
  assert.match(specialAnalysisPage, /分设备视图/)
  assert.doesNotMatch(specialAnalysisPage, /title="雨量统计"/)
  assert.doesNotMatch(specialAnalysisPage, /name="日降雨量"/)
  assert.doesNotMatch(specialAnalysisPage, /name="月累计降雨"/)
  assert.doesNotMatch(specialAnalysisPage, /趋势 \$\{summary\.trend/)
  assert.doesNotMatch(specialAnalysisPage, /最大小时雨量 \$\{summary\.max_hourly/)
  assert.doesNotMatch(specialAnalysisPage, /站点峰值 \$\{summary\.station_peak/)
  assert.doesNotMatch(specialAnalysisPage, /仅径流设备/)
  assert.match(specialAnalysisPage, /累计径流/)
  assert.match(specialAnalysisPage, /平均含沙量/)
  assert.match(specialAnalysisPage, /专项分析结论与应对策略/)
})

test('analytics page removes duplicate runoff chart and renames device drilldown card', () => {
  assert.match(analyticsPage, /<RunoffDailyChart data=\{runoffDaily\} \/>/)
  assert.equal((analyticsPage.match(/<RunoffDailyChart data=\{runoffDaily\} \/>/g) || []).length, 1)
  assert.doesNotMatch(analyticsPage, /<DeviceSeriesExplorer/)
  assert.doesNotMatch(analyticsPage, /<DeviceSeriesExplorer/)
})

test('analytics page loads cards through parallel polling endpoints instead of one dashboard bundle', () => {
  assert.match(analyticsPage, /const ecoIndexRequest = usePolling\(/)
  assert.match(analyticsPage, /const guidelineMetricsRequest = usePolling\(/)
  assert.match(analyticsPage, /const waterQualityDailyRequest = usePolling\(/)
  assert.match(analyticsPage, /const runoffDailyRequest = usePolling\(/)
  assert.match(analyticsPage, /const combinedTrendRequest = usePolling\(/)
  assert.match(analyticsPage, /const insectHeatmapRequest = usePolling\(/)
  assert.doesNotMatch(analyticsPage, /analysisDashboardRequest/)
  assert.doesNotMatch(analyticsPage, /api\.analysisDashboard\(/)
  assert.match(analyticsPage, /dashboardRequests\.forEach\(\(request\) => \{/)
})

test('analytics page labels weather support card as external interface data', () => {
  assert.match(analyticsPage, /外部接口/)
})

test('device series explorer warns that anomaly values are shown raw without filtering', () => {
  assert.ok(deviceSeriesExplorer.includes('原始值'))
  assert.ok(deviceSeriesExplorer.includes('未做过滤'))
  assert.match(deviceSeriesExplorer, /anomalySummaryForMode/)
})

test('device series explorer unwraps overview payloads passed as data objects', () => {
  assert.match(deviceSeriesExplorer, /function normalizeRows/)
  assert.match(deviceSeriesExplorer, /Array\.isArray\(rows\?\.data\)/)
  assert.match(deviceSeriesExplorer, /const rows = normalizeRows\(activeTab\?\.rows\)/)
})

test('device series explorer exposes all seven runoff daily fields in device drilldown', () => {
  assert.match(deviceSeriesExplorer, /item\.runoff/)
  assert.match(deviceSeriesExplorer, /item\.flow/)
  assert.match(deviceSeriesExplorer, /item\.flow_speed/)
  assert.match(deviceSeriesExplorer, /item\.sand/)
  assert.match(deviceSeriesExplorer, /item\.water_level/)
  assert.match(deviceSeriesExplorer, /item\.liquid_pressure/)
  assert.match(deviceSeriesExplorer, /item\.total_flow/)
})

test('device series explorer uses readable Chinese labels and supports runoff-only mode', () => {
  assert.ok(deviceSeriesExplorer.includes('区域总览'))
  assert.ok(deviceSeriesExplorer.includes('雨量设备'))
  assert.ok(deviceSeriesExplorer.includes('径流设备'))
  assert.match(deviceSeriesExplorer, /allowedModes = \['rainfall', 'runoff'\]/)
  assert.match(deviceSeriesExplorer, /defaultMode = allowedModes\[0\] \?\? 'rainfall'/)
  assert.match(deviceSeriesExplorer, /const showModeSwitcher = allowedModes\.length > 1/)
  assert.match(deviceSeriesExplorer, /showModeSwitcher \?/)
  assert.match(deviceSeriesExplorer, /display:\s*'flex'/)
  assert.match(deviceSeriesExplorer, /flexWrap:\s*'wrap'/)
  assert.match(deviceSeriesExplorer, /\.filter\(\(item\) => allowedModes\.includes\(item\.key\)\)/)
  assert.match(deviceSeriesExplorer, /formatter:\s*\(params\)\s*=>/)
  assert.match(deviceSeriesExplorer, /雨量 \(mm\)/)
  assert.ok(deviceSeriesExplorer.includes('日累计径流'))
  assert.ok(deviceSeriesExplorer.includes('日均含沙量'))
  assert.ok(deviceSeriesExplorer.includes('暂无设备维度数据'))
  assert.doesNotMatch(deviceSeriesExplorer, /metaText\(/)
})

test('runoff daily chart includes cumulative total flow alongside other hydrology fields', () => {
  assert.match(runoffDailyChart, /d\.total_flow/)
  assert.match(runoffDailyChart, /d\.runoff_rate/)
  assert.match(runoffDailyChart, /日均径流/)
  assert.match(runoffDailyChart, /m³\/min/)
  assert.match(runoffDailyChart, /当日累计降雨量/)
})

test('overview runoff panel distinguishes cumulative flow from instantaneous runoff units', () => {
  assert.match(runoffPanel, /label:\s*'当前径流',\s*key:\s*'runoff',\s*unit:\s*'m³\/min'/)
  assert.match(runoffPanel, /label:\s*'累计流量',\s*key:\s*'total_flow',\s*unit:\s*'m³'/)
  assert.match(runoffPanel, /label:\s*'当前流速',\s*key:\s*'flow_speed',\s*unit:\s*'m\/s'/)
  assert.match(runoffPanel, /label:\s*'瞬时流量',\s*key:\s*'flow_rate',\s*unit:\s*'m³\/s'/)
  assert.match(runoffPanel, /label:\s*'今日累计降雨量',\s*key:\s*'rainfall',\s*unit:\s*'mm'/)
})

test('runoff legends append units to the displayed latest values', () => {
  assert.match(runoffDailyChart, /legendValueByName/)
  assert.match(runoffDailyChart, /kPa/)
  assert.match(runoffDailyChart, /kg\/L/)
  assert.match(runoffDailyChart, /m³\/s/)
  assert.match(runoffDailyChart, /formatter:\s*\(name\)\s*=>/)

  assert.match(deviceSeriesExplorer, /legendValueByName/)
  assert.match(deviceSeriesExplorer, /m³/)
  assert.match(deviceSeriesExplorer, /m\/s/)
  assert.match(deviceSeriesExplorer, /formatter:\s*\(name\)\s*=>/)
})

test.skip('special analysis hover tooltips append concrete units', () => {
  assert.match(specialAnalysisPage, /function formatTooltipMetric/)
  assert.match(specialAnalysisPage, /unitBySeriesName/)
  assert.match(specialAnalysisPage, /平均流量', color: '#4ade80', unit: 'm³\/s'/)
  assert.match(specialAnalysisPage, /平均含沙量', color: '#facc15', unit: 'kg\/L'/)
  assert.match(specialAnalysisPage, /高锰酸盐指数', color: '#38bdf8', type: 'bar', unit: 'mg\/L'/)
  assert.match(specialAnalysisPage, /tooltip:\s*\{[\s\S]*formatter:\s*\(params\)\s*=>/s)
})

test('report manager table contains overflow inside its local scroller', () => {
  assert.match(reportCss, /\.tableShell\s*\{[^}]*min-width:\s*0/im)
  assert.match(reportCss, /\.tableWrap\s*\{[^}]*overflow-x:\s*auto/im)
  assert.match(reportCss, /\.table\s*\{[^}]*min-width:\s*1040px/im)
})

test('report manager centers split report titles and right-aligns action buttons', () => {
  assert.match(reportManager, /function splitReportTitle/)
  assert.match(reportManager, /<span className=\{s\.reportTitlePeriod\}>\{period\}<\/span>/)
  assert.match(reportCss, /\.table thead th\s*\{[^}]*text-align:\s*center/im)
  assert.match(reportCss, /\.table td\s*\{[^}]*text-align:\s*center/im)
  assert.match(reportCss, /\.titleCol\s*\{[^}]*text-align:\s*center/im)
  assert.match(reportCss, /\.actionsCol\s*\{[^}]*text-align:\s*right/im)
  assert.match(reportCss, /\.actions\s*\{[^}]*grid-template-columns:\s*repeat\(3,\s*72px\)/im)
  assert.match(reportCss, /\.actions\s*\{[^}]*justify-content:\s*end/im)
})

test('report manager removes default pending-review explanatory sentence', () => {
  assert.doesNotMatch(reportManager, /报告生成后默认为待审核，审核通过后领导密码才可以查看/)
})

test('header exposes logout action wired to auth logout', () => {
  assert.match(header, /onLogout/)
  assert.match(header, />\s*退出\s*<\/button>/)
  assert.match(headerCss, /\.logoutBtn\s*\{/)
  assert.match(app, /api\.authLogout\(\)/)
  assert.match(app, /<DashboardApp onLogout=\{\(\) => setAuthenticated\(false\)\} \/>/)
})

test('header avoids fullscreen title and navigation overlap', () => {
  assert.match(headerCss, /\.header\s*\{[^}]*display:\s*grid/im)
  assert.match(headerCss, /grid-template-columns:\s*minmax\(0,\s*1fr\)\s*minmax\(760px,\s*max-content\)\s*minmax\(0,\s*1fr\)/im)
  assert.match(headerCss, /\.center\s*\{[^}]*grid-column:\s*2/im)
  assert.match(headerCss, /\.center\s*\{[^}]*min-width:\s*0/im)
  assert.doesNotMatch(headerCss, /\.title\s*\{[^}]*text-overflow:\s*ellipsis/im)
  assert.match(headerCss, /\.title\s*\{[^}]*font-size:\s*clamp\(22px,\s*1\.85vw,\s*34px\)/im)
  assert.match(headerCss, /\.navActions\s*\{[^}]*justify-content:\s*flex-end/im)
  assert.match(headerCss, /\.rightSide\s*\{[^}]*max-width:\s*420px/im)
  assert.match(headerCss, /\.navActions\s*\{[^}]*flex-wrap:\s*nowrap/im)
  assert.match(headerCss, /\.navActions\s*\{[^}]*max-width:\s*420px/im)
  assert.match(headerCss, /\.btn\s*\{[^}]*letter-spacing:\s*0/im)
  assert.match(headerCss, /@media\s*\(max-width:\s*1720px\)[\s\S]*?\.navActions\s*\{[\s\S]*?flex-wrap:\s*wrap/im)
  assert.match(headerCss, /@media\s*\(max-width:\s*1720px\)[\s\S]*?\.clock\s*\{[\s\S]*?display:\s*none/im)
  assert.match(header, /className=\{s\.navActions\}/)
})

test('overview insect species composition uses all returned species', () => {
  assert.match(app, /api\.insectSpecies\(30\)/)
  assert.match(app, /insect-species-30d/)
  assert.doesNotMatch(insectPanel, /sp\.slice\(0,\s*6\)/)
  assert.match(insectPanel, /sp\.map\(\(d,\s*i\)/)
  assert.match(insectPanel, /COLORS\[i % COLORS\.length\]/)
})

test('special insect quantity chart relies on top period filters only', () => {
  assert.doesNotMatch(specialAnalysisPage, /GRANULARITIES/)
  assert.doesNotMatch(specialAnalysisPage, /trendGranularity/)
  assert.doesNotMatch(specialAnalysisPage, /setGranularity/)
  assert.doesNotMatch(specialAnalysisPage, /trend_30d/)
  assert.match(specialAnalysisPage, /<TrendChart data=\{data\?\.trend\}/)
})

test('special runoff section removes duplicated erosion charts', () => {
  assert.doesNotMatch(specialAnalysisPage, /title="水土流失与径流趋势"/)
  assert.doesNotMatch(specialAnalysisPage, /title="侵蚀代理指标"/)
  assert.doesNotMatch(specialAnalysisPage, /data\?\.erosion_series/)
})

test('vite build splits large vendor chunks', () => {
  assert.match(viteConfig, /manualChunks/)
  assert.match(viteConfig, /chunkSizeWarningLimit:\s*1200/)
  assert.match(viteConfig, /echarts:\s*\[/)
  assert.match(viteConfig, /leaflet:\s*\[/)
  assert.match(viteConfig, /react:\s*\[/)
})

test('special analysis keeps unit-aware tooltip formatter and removes erosion series chart source', () => {
  assert.match(specialAnalysisPage, /function formatTooltipMetric/)
  assert.match(specialAnalysisPage, /unitBySeriesName/)
  assert.match(specialAnalysisPage, /permanganate/)
  assert.match(specialAnalysisPage, /unit: 'mg\/L'/)
  assert.match(specialAnalysisPage, /tooltip:\s*\{[\s\S]*formatter:\s*\(params\)\s*=>/s)
  assert.doesNotMatch(specialAnalysisPage, /data\?\.erosion_series/)
})
