import { useEffect, useMemo, useRef, useState } from 'react'
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

const SUCCESS_STATUSES = new Set(['ok', 'accepted'])
const REVIEW_STATUS_LABELS = {
  pending: '待审核',
  approved: '已通过',
  rejected: '已驳回',
}
const TASK_STATUS_LABELS = {
  queued: '排队中',
  running: '生成中',
  completed: '已完成',
  failed: '生成失败',
}

const ACTIVE_TASK_STATUSES = new Set(['queued', 'running'])

export default function ReportManager() {
  const [reports, setReports] = useState([])
  const [role, setRole] = useState('')
  const [reviewReminder, setReviewReminder] = useState({ pending: 0, overdue: 0 })
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [filterType, setFilterType] = useState('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [messageNotice, setMessageNotice] = useState(null)
  const trackedTaskIdsRef = useRef(new Set())
  const notifiedTaskIdsRef = useRef(new Set())
  const noticeTimerRef = useRef(null)

  useEffect(() => {
    fetchReports()
  }, [])

  useEffect(() => {
    setCurrentPage(1)
  }, [filterType])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined
    }

    const timer = window.setInterval(() => {
      const hasActiveTask = reports.some((report) => ACTIVE_TASK_STATUSES.has(report.status))
      if (hasActiveTask) {
        fetchReports({ silent: true })
      }
    }, 5000)

    return () => {
      window.clearInterval(timer)
    }
  }, [reports])

  useEffect(() => {
    reports.forEach((report) => {
      if (!report.task_id || notifiedTaskIdsRef.current.has(report.task_id)) {
        return
      }

      if (ACTIVE_TASK_STATUSES.has(report.status)) {
        trackedTaskIdsRef.current.add(report.task_id)
        return
      }

      if (!trackedTaskIdsRef.current.has(report.task_id)) {
        return
      }

      if (report.status === 'completed') {
        notifiedTaskIdsRef.current.add(report.task_id)
        showMessage({
          type: 'success',
          title: '报告生成完成',
          message: `${report.title} 已生成完成，请及时审核。`,
        })
      }

      if (report.status === 'failed') {
        notifiedTaskIdsRef.current.add(report.task_id)
        showMessage({
          type: 'error',
          title: '报告生成失败',
          message: `${report.title} 生成失败：${report.error_message || '请稍后重试'}`,
        })
      }
    })
  }, [reports])

  async function fetchReports(options = {}) {
    if (!options.silent) {
      setLoading(true)
    }
    try {
      const res = await fetch(`${API_BASE}/report/list`, { credentials: 'include' })
      const json = await parseResponse(res)
      if (json.data) {
        setReports(json.data)
      }
      setRole(json.role || '')
      setReviewReminder(json.review_reminder || { pending: 0, overdue: 0 })
    } catch (error) {
      console.error(error)
    } finally {
      if (!options.silent) {
        setLoading(false)
      }
    }
  }

  function showMessage(nextNotice) {
    setMessageNotice(nextNotice)

    if (typeof window !== 'undefined') {
      window.clearTimeout(noticeTimerRef.current)
      noticeTimerRef.current = window.setTimeout(() => {
        setMessageNotice(null)
      }, 8000)
    }

    if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'granted') {
      new Notification(nextNotice.title, { body: nextNotice.message })
    }
  }

  async function handleGenerate() {
    const reportTypes = filterType === 'all' ? ['daily', 'weekly', 'monthly'] : [filterType]

    setSubmitting(true)
    setCurrentPage(1)
    setMessageNotice(null)

    if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'default') {
      const permissionRequest = Notification.requestPermission()
      if (permissionRequest?.catch) {
        permissionRequest.catch(() => {})
      }
    }

    try {
      const acceptedReports = []
      for (const reportType of reportTypes) {
        const res = await fetch(`${API_BASE}/report/generate?report_type=${reportType}`, {
          method: 'POST',
          credentials: 'include',
        })
        const json = await parseResponse(res)
        if (!SUCCESS_STATUSES.has(json.status)) {
          throw new Error(json.detail || `${REPORT_TYPE_LABELS[reportType]}生成失败`)
        }
        if (json.data) {
          acceptedReports.push(json.data)
          if (json.data.task_id) {
            trackedTaskIdsRef.current.add(json.data.task_id)
          }
        }
      }
      await fetchReports()
      showMessage({
        type: 'info',
        title: '已提交后台生成',
        message: `${acceptedReports.length || reportTypes.length} 个报告任务已提交，生成完成后会自动提醒。`,
      })
    } catch (error) {
      console.error(error)
      window.alert(`生成失败：${error.message || '请求出错'}`)
    } finally {
      setSubmitting(false)
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

  async function handleReview(id, action) {
    const actionText = action === 'approve' ? '审核通过' : '驳回'
    if (!window.confirm(`确认${actionText}这份报告吗？`)) {
      return
    }

    try {
      await fetch(`${API_BASE}/report/${id}/${action}`, {
        method: 'POST',
        credentials: 'include',
      })
      await fetchReports()
    } catch (error) {
      console.error(error)
      window.alert(`${actionText}失败：${error.message || '请求出错'}`)
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
  const activeTasks = reports.filter((report) => ACTIVE_TASK_STATUSES.has(report.status))
  const generateButtonText = submitting
    ? '正在提交...'
    : filterType === 'all'
      ? '生成全部报告'
      : `生成${currentFilterLabel}`

  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 3600 * 1000)
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 3600 * 1000)
  const latestReportDate = filteredReports.length > 0 ? filteredReports[0].created_at.split(' ')[0] : '暂无'
  const isAdmin = role !== 'leader'

  return (
    <div className={s.container}>
      {messageNotice ? (
        <div className={`${s.messageNotice} ${s[messageNotice.type] || ''}`}>
          <strong>{messageNotice.title}</strong>
          <span>{messageNotice.message}</span>
          <button type="button" onClick={() => setMessageNotice(null)}>知道了</button>
        </div>
      ) : null}

      <div className={s.header}>
        <div>
          <div className={s.title}>报告生成与管理</div>
          <div className={s.subtitle}>
            {role === 'leader'
              ? '当前为区领导查看权限，仅显示审核通过并开放可见的报告。'
              : '报告生成后默认为待审核，审核通过后区领导密码才可以查看。'}
          </div>
        </div>

        {isAdmin ? (
          <div className={s.controls}>
            <label className={s.filterGroup}>
              <span className={s.filterLabel}>报告类型</span>
              <div className={s.selectWrap}>
                <select
                  className={s.typeSelect}
                  value={filterType}
                  onChange={(event) => setFilterType(event.target.value)}
                  disabled={submitting}
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
              className={`${s.btnGenerate} ${submitting ? s.loading : ''}`}
              onClick={handleGenerate}
              disabled={submitting}
            >
              {generateButtonText}
            </button>
          </div>
        ) : null}
      </div>

      {isAdmin ? (
        <div className={`${s.reviewNotice} ${reviewReminder.overdue > 0 ? s.reviewOverdue : ''}`}>
          <strong>审核提醒</strong>
          <span>待审核 {reviewReminder.pending || 0} 份</span>
          <span>逾期 {reviewReminder.overdue || 0} 份</span>
          {activeTasks.length > 0 ? <span>后台生成 {activeTasks.length} 份</span> : null}
          <em>报告生成后 1 天内需完成审核，审核通过后区领导可见。</em>
        </div>
      ) : null}

      <div className={s.statsGrid}>
        <StatCard label={`${currentFilterLabel}数量`} value={filteredReports.length} />
        <StatCard
          label="近 7 天生成"
          value={filteredReports.filter((report) => new Date(report.created_at.replace(' ', 'T')) > sevenDaysAgo).length}
        />
        <StatCard
          label="近 30 天生成"
          value={filteredReports.filter((report) => new Date(report.created_at.replace(' ', 'T')) > thirtyDaysAgo).length}
        />
        <StatCard label="最近一次生成" value={latestReportDate} large />
        {isAdmin ? <StatCard label="待审核报告" value={reviewReminder.pending || 0} /> : null}
        {isAdmin && activeTasks.length > 0 ? <StatCard label="后台生成中" value={activeTasks.length} /> : null}
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
                <th>审核状态</th>
                <th>生成时间</th>
                <th className={s.actionsCol}>操作</th>
              </tr>
            </thead>
            <tbody>
              {loading && reports.length === 0 ? (
                <tr>
                  <td colSpan="7" className={s.empty}>正在加载报告列表...</td>
                </tr>
              ) : null}

              {!loading && filteredReports.length === 0 ? (
                <tr>
                  <td colSpan="7" className={s.empty}>
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
                  <td className={s.reviewCol}>
                    <span className={`${s.reviewTag} ${s[report.review_status] || ''} ${s[report.status] || ''} ${report.review_overdue ? s.overdue : ''}`}>
                      {ACTIVE_TASK_STATUSES.has(report.status) || report.status === 'failed'
                        ? TASK_STATUS_LABELS[report.status] || report.status
                        : report.review_overdue
                          ? '审核逾期'
                          : REVIEW_STATUS_LABELS[report.review_status] || report.review_status || '待审核'}
                    </span>
                    {report.status === 'failed' && report.error_message ? (
                      <small>{report.error_message}</small>
                    ) : report.review_status === 'approved' && report.reviewed_at ? (
                      <small>{report.reviewed_at}</small>
                    ) : isAdmin && report.review_deadline ? (
                      <small>截止 {report.review_deadline}</small>
                    ) : null}
                  </td>
                  <td className={s.timeCol}>{report.created_at}</td>
                  <td className={s.actionsCol}>
                    <div className={s.actions}>
                      {report.has_html && report.status === 'completed' ? (
                        <button className={s.btnHtml} onClick={() => handleDownload(report.id, 'html')}>
                          HTML
                        </button>
                      ) : null}
                      {report.has_docx && report.status === 'completed' ? (
                        <button className={s.btnDocx} onClick={() => handleDownload(report.id, 'docx')}>
                          Word
                        </button>
                      ) : null}
                      {isAdmin && report.status === 'completed' && report.review_status !== 'approved' ? (
                        <button className={s.btnApprove} onClick={() => handleReview(report.id, 'approve')}>
                          通过
                        </button>
                      ) : null}
                      {isAdmin && report.status === 'completed' && report.review_status !== 'rejected' ? (
                        <button className={s.btnReject} onClick={() => handleReview(report.id, 'reject')}>
                          驳回
                        </button>
                      ) : null}
                      {isAdmin ? (
                        <button className={s.btnDelete} onClick={() => handleDelete(report.id)}>
                          删除
                        </button>
                      ) : null}
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

function StatCard({ label, value, large = false }) {
  return (
    <div className={s.statCard}>
      <div className={s.statLabel}>{label}</div>
      <div className={`${s.statValue} ${large ? s.largeValue : ''}`}>{value}</div>
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
