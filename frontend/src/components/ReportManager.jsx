import { useEffect, useMemo, useState } from 'react'
import s from './ReportManager.module.css'

const API_BASE = '/api'

const REPORT_TYPE_LABELS = {
  daily: '生态日报',
  weekly: '生态周报',
  monthly: '生态月报',
}

const REPORT_FILTER_OPTIONS = [
  { value: 'all', label: '全部报告' },
  { value: 'daily', label: '生态日报' },
  { value: 'weekly', label: '生态周报' },
  { value: 'monthly', label: '生态月报' },
]

export default function ReportManager() {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [filterType, setFilterType] = useState('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [elapsedTime, setElapsedTime] = useState(0)
  const [estimatedTotal, setEstimatedTotal] = useState(30)
  const [currentTaskLabel, setCurrentTaskLabel] = useState('')

  useEffect(() => {
    fetchReports()
  }, [])

  useEffect(() => {
    setCurrentPage(1)
  }, [filterType])

  useEffect(() => {
    let timer
    if (generating) {
      setElapsedTime(0)
      timer = setInterval(() => {
        setElapsedTime((prev) => prev + 1)
      }, 1000)
    }
    return () => {
      if (timer) {
        clearInterval(timer)
      }
    }
  }, [generating])

  async function fetchReports() {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/report/list`, { credentials: 'include' })
      const json = await parseResponse(res)
      if (json.data) {
        setReports(json.data)
      }
    } catch (error) {
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  async function handleGenerate() {
    const reportTypes = filterType === 'all' ? ['daily', 'weekly', 'monthly'] : [filterType]

    let estimate = 0
    if (reportTypes.includes('daily')) estimate += 150
    if (reportTypes.includes('weekly')) estimate += 180
    if (reportTypes.includes('monthly')) estimate += 240

    setEstimatedTotal(estimate || 30)
    setGenerating(true)
    setCurrentPage(1)

    try {
      for (const reportType of reportTypes) {
        setCurrentTaskLabel(REPORT_TYPE_LABELS[reportType] || reportType)
        const res = await fetch(`${API_BASE}/report/generate?report_type=${reportType}`, {
          method: 'POST',
          credentials: 'include',
        })
        const json = await parseResponse(res)
        if (json.status !== 'ok') {
          throw new Error(json.detail || `${REPORT_TYPE_LABELS[reportType]}生成失败`)
        }
      }
      await fetchReports()
    } catch (error) {
      console.error(error)
      window.alert(`生成失败：${error.message || '请求出错'}`)
    } finally {
      setGenerating(false)
      setCurrentTaskLabel('')
    }
  }

  async function handleDelete(id) {
    if (!window.confirm('确认删除这份报告吗？')) {
      return
    }

    try {
      await fetch(`${API_BASE}/report/${id}`, {
        method: 'DELETE',
        credentials: 'include',
      })
      await fetchReports()
    } catch (error) {
      console.error(error)
    }
  }

  function handleDownload(id, format) {
    window.open(`${API_BASE}/report/download/${id}/${format}`, '_blank')
  }

  const filteredReports = useMemo(() => {
    if (filterType === 'all') {
      return reports
    }
    return reports.filter((report) => report.report_type === filterType)
  }, [filterType, reports])

  const totalPages = Math.max(1, Math.ceil(filteredReports.length / pageSize))
  const currentReports = filteredReports.slice((currentPage - 1) * pageSize, currentPage * pageSize)
  const currentFilterLabel = REPORT_FILTER_OPTIONS.find((item) => item.value === filterType)?.label || '全部报告'
  const generateButtonText = generating
    ? `正在生成${currentTaskLabel || currentFilterLabel}...`
    : filterType === 'all'
      ? '生成全部报告'
      : `生成${currentFilterLabel}`

  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 3600 * 1000)
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 3600 * 1000)
  const latestReportDate = filteredReports.length > 0 ? filteredReports[0].created_at.split(' ')[0] : '暂无'

  return (
    <div className={s.container}>
      {generating ? (
        <div className={s.overlay}>
          <div className={s.overlayPanel}>
            <div className={s.loaderOrb} />
            <div className={s.overlayTitle}>正在生成分析报告</div>
            <div className={s.overlaySubtitle}>
              当前任务：{currentTaskLabel || currentFilterLabel}
              <br />
              日报按单日、周报按最近 7 天、月报按最近 30 天自动切换统计范围。
            </div>
            <div className={s.timerRow}>
              <div className={s.timerValue}>{elapsedTime}s</div>
              <div className={s.timerText}>已耗时 / 预计 {estimatedTotal}s</div>
            </div>
            <div className={s.progressTrack}>
              <div
                className={s.progressFill}
                style={{ width: `${Math.min(100, (elapsedTime / estimatedTotal) * 100)}%` }}
              />
            </div>
          </div>
        </div>
      ) : null}

      <div className={s.header}>
        <div>
          <div className={s.title}>报告生成与管理</div>
          <div className={s.subtitle}>
            报告数据会随周期口径自动切换：日报读取单日，周报读取最近 7 天，月报读取最近 30 天。
          </div>
        </div>

        <div className={s.controls}>
          <label className={s.filterGroup}>
            <span className={s.filterLabel}>报告类型</span>
            <div className={s.selectWrap}>
              <select
                className={s.typeSelect}
                value={filterType}
                onChange={(event) => setFilterType(event.target.value)}
                disabled={generating}
              >
                {REPORT_FILTER_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <span className={s.selectIcon} aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M7 10l5 5 5-5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
            </div>
          </label>

          <button
            className={`${s.btnGenerate} ${generating ? s.loading : ''}`}
            onClick={handleGenerate}
            disabled={generating}
          >
            {generateButtonText}
          </button>
        </div>
      </div>

      <div className={s.statsGrid}>
        <StatCard label={`${currentFilterLabel}数量`} value={filteredReports.length} meta="当前筛选结果" />
        <StatCard
          label="近 7 天生成"
          value={filteredReports.filter((report) => new Date(report.created_at.replace(' ', 'T')) > sevenDaysAgo).length}
          meta="最近一周新增"
        />
        <StatCard
          label="近 30 天生成"
          value={filteredReports.filter((report) => new Date(report.created_at.replace(' ', 'T')) > thirtyDaysAgo).length}
          meta="最近一月新增"
        />
        <StatCard label="最近一次生成" value={latestReportDate} meta="按创建时间排序" large />
      </div>

      <div className={s.tableShell}>
        <div className={s.tableWrap}>
          <table className={s.table}>
            <thead>
              <tr>
                <th className={s.idCol}>ID</th>
                <th>报告标题</th>
                <th>统计周期</th>
                <th>类型</th>
                <th>生成时间</th>
                <th className={s.actionsCol}>操作</th>
              </tr>
            </thead>
            <tbody>
              {loading && reports.length === 0 ? (
                <tr>
                  <td colSpan="6" className={s.empty}>正在加载报告列表...</td>
                </tr>
              ) : null}

              {!loading && filteredReports.length === 0 ? (
                <tr>
                  <td colSpan="6" className={s.empty}>
                    当前筛选条件下暂无报告，请点击上方按钮生成。
                  </td>
                </tr>
              ) : null}

              {currentReports.map((report) => (
                <tr key={report.id}>
                  <td className={s.idCol}>{report.id}</td>
                  <td className={s.titleCol}>{report.title}</td>
                  <td className={s.periodCol}>{report.period_start} - {report.period_end}</td>
                  <td className={s.typeCol}>
                    <span className={`${s.tag} ${s[report.report_type]}`}>
                      {REPORT_TYPE_LABELS[report.report_type] || report.report_type}
                    </span>
                  </td>
                  <td className={s.timeCol}>{report.created_at}</td>
                  <td className={s.actionsCol}>
                    <div className={s.actions}>
                      {report.has_html ? (
                        <button className={s.btnHtml} onClick={() => handleDownload(report.id, 'html')}>
                          HTML
                        </button>
                      ) : null}
                      {report.has_docx ? (
                        <button className={s.btnDocx} onClick={() => handleDownload(report.id, 'docx')}>
                          Word
                        </button>
                      ) : null}
                      <button className={s.btnDelete} onClick={() => handleDelete(report.id)}>
                        删除
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {filteredReports.length > 0 ? (
        <div className={s.pagination}>
          <div className={s.pageSizer}>
            <span className={s.pageLabel}>每页显示</span>
            <select
              value={pageSize}
              onChange={(event) => {
                setPageSize(Number(event.target.value))
                setCurrentPage(1)
              }}
              className={s.pageSelect}
            >
              <option value={5}>5 条</option>
              <option value={10}>10 条</option>
              <option value={20}>20 条</option>
              <option value={50}>50 条</option>
            </select>
          </div>

          <div className={s.pageControls}>
            <button disabled={currentPage === 1} onClick={() => setCurrentPage((page) => page - 1)}>
              上一页
            </button>
            <span>{currentPage} / {totalPages}</span>
            <button disabled={currentPage >= totalPages} onClick={() => setCurrentPage((page) => page + 1)}>
              下一页
            </button>
          </div>
        </div>
      ) : null}
    </div>
  )
}

function StatCard({ label, value, meta, large = false }) {
  return (
    <div className={s.statCard}>
      <div className={s.statLabel}>{label}</div>
      <div className={`${s.statValue} ${large ? s.largeValue : ''}`}>{value}</div>
      <div className={s.statMeta}>{meta}</div>
    </div>
  )
}

async function parseResponse(res) {
  const contentType = res.headers.get('content-type') || ''
  const bodyText = await res.text()
  let data = null

  if (bodyText) {
    if (contentType.includes('application/json')) {
      data = JSON.parse(bodyText)
    } else {
      try {
        data = JSON.parse(bodyText)
      } catch {
        data = null
      }
    }
  }

  if (!res.ok) {
    const detail =
      data?.detail ||
      data?.message ||
      bodyText ||
      `HTTP ${res.status}`
    throw new Error(detail)
  }

  if (data !== null) {
    return data
  }

  return { status: 'ok' }
}
