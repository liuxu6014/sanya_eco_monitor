import { useEffect, useMemo, useState } from 'react'
import s from './ReportManager.module.css'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '') + '/api'

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

  useEffect(() => {
    fetchReports()
  }, [])

  useEffect(() => {
    setCurrentPage(1)
  }, [filterType])

  const fetchReports = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/report/list`, { credentials: 'include' })
      const json = await res.json()
      if (json.data) {
        setReports(json.data)
      }
    } catch (error) {
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleGenerate = async () => {
    const reportTypes = filterType === 'all' ? ['daily', 'weekly', 'monthly'] : [filterType]
    setGenerating(true)
    setCurrentPage(1)

    try {
      for (const reportType of reportTypes) {
        const res = await fetch(`${API_BASE}/report/generate?report_type=${reportType}`, {
          method: 'POST',
          credentials: 'include',
        })
        const json = await res.json()
        if (json.status !== 'ok') {
          throw new Error(json.detail || `${REPORT_TYPE_LABELS[reportType]}生成失败`)
        }
      }
      await fetchReports()
    } catch (error) {
      console.error(error)
      alert(`生成失败: ${error.message || '请求出错'}`)
    } finally {
      setGenerating(false)
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('确定要删除这篇报告吗？')) {
      return
    }

    try {
      await fetch(`${API_BASE}/report/${id}`, { method: 'DELETE', credentials: 'include' })
      await fetchReports()
    } catch (error) {
      console.error(error)
    }
  }

  const handleDownload = (id, format) => {
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
    ? filterType === 'all'
      ? '正在生成全部报告...'
      : `正在生成${currentFilterLabel}...`
    : '生成报告'
  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 3600 * 1000)
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 3600 * 1000)

  return (
    <div className={s.container}>
      <div className={s.header}>
        <div className={s.title}>报告生成与管理</div>

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

      <div className={s.statsContainer}>
        <div className={s.statCard}>
          <div className={s.statHeader}>
            <div className={s.statLabel}>{currentFilterLabel}数量</div>
            <div className={s.statIcon}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
            </div>
          </div>
          <div className={s.statValue}>
            {filteredReports.length}
            <span style={{ fontSize: 12, fontWeight: 400, color: 'var(--text-muted)', marginLeft: 4 }}>份</span>
          </div>
        </div>

        <div className={s.statCard}>
          <div className={s.statHeader}>
            <div className={s.statLabel}>近 7 天生成数量</div>
            <div className={s.statIcon}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <line x1="16" y1="2" x2="16" y2="6" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="3" y1="10" x2="21" y2="10" />
              </svg>
            </div>
          </div>
          <div className={s.statValue}>
            {filteredReports.filter((report) => new Date(report.created_at.replace(' ', 'T')) > sevenDaysAgo).length}
            <span style={{ fontSize: 12, fontWeight: 400, color: 'var(--text-muted)', marginLeft: 4 }}>份</span>
          </div>
        </div>

        <div className={s.statCard}>
          <div className={s.statHeader}>
            <div className={s.statLabel}>近 30 天生成数量</div>
            <div className={s.statIcon}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M21.21 15.89A10 10 0 1 1 8 2.83" />
                <path d="M22 12A10 10 0 0 0 12 2v10z" />
              </svg>
            </div>
          </div>
          <div className={s.statValue}>
            {filteredReports.filter((report) => new Date(report.created_at.replace(' ', 'T')) > thirtyDaysAgo).length}
            <span style={{ fontSize: 12, fontWeight: 400, color: 'var(--text-muted)', marginLeft: 4 }}>份</span>
          </div>
        </div>

        <div className={s.statCard}>
          <div className={s.statHeader}>
            <div className={s.statLabel}>最近一次生成</div>
            <div className={s.statIcon}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
            </div>
          </div>
          <div className={s.statValue} style={{ fontSize: '18px' }}>
            {filteredReports.length > 0 ? filteredReports[0].created_at.split(' ')[0] : '暂无数据'}
          </div>
        </div>
      </div>

      <div className={s.tableWrap}>
        <div className={s.tableContainer}>
          <table className={s.table}>
            <thead>
              <tr>
                <th className={s.idCol}>ID</th>
                <th>报告标题</th>
                <th>统计周期</th>
                <th>类型</th>
                <th>生成时间</th>
                <th className={s.tr}>操作</th>
              </tr>
            </thead>
            <tbody>
              {loading && reports.length === 0 && (
                <tr>
                  <td colSpan="6" className={s.empty}>加载数据中...</td>
                </tr>
              )}

              {!loading && filteredReports.length === 0 && (
                <tr>
                  <td colSpan="6" className={s.empty}>
                    当前筛选下暂无报告，请点击上方“生成报告”。
                  </td>
                </tr>
              )}

              {currentReports.map((report) => (
                <tr key={report.id}>
                  <td className={s.idCol}>{report.id}</td>
                  <td className={s.titleCol}>{report.title}</td>
                  <td className={s.dateCol}>{report.period_start} ~ {report.period_end}</td>
                  <td className={s.typeCol}>
                    <span className={`${s.tag} ${s[report.report_type]}`}>
                      {REPORT_TYPE_LABELS[report.report_type] || report.report_type}
                    </span>
                  </td>
                  <td className={s.timeCol}>{report.created_at}</td>
                  <td className={s.tr}>
                    <div className={s.actions}>
                      {report.has_html && (
                        <button className={s.btnDownloadHtml} onClick={() => handleDownload(report.id, 'html')}>
                          HTML 版
                        </button>
                      )}
                      {report.has_docx && (
                        <button className={s.btnDownloadDocx} onClick={() => handleDownload(report.id, 'docx')}>
                          Word 版
                        </button>
                      )}
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

      {filteredReports.length > 0 && (
        <div className={s.pagination}>
          <div className={s.pageSizer}>
            <span className={s.pageSizerLabel}>每页显示</span>
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
      )}
    </div>
  )
}
