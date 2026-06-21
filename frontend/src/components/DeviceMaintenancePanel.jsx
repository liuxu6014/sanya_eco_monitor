import { useCallback, useEffect, useMemo, useState } from 'react'
import dayjs from 'dayjs'
import { api, maintenanceExportUrl } from '../utils/api.js'
import DeviceSelect from './DeviceSelect.jsx'
import DateRangePicker from './DateRangePicker.jsx'
import TypeChip from './TypeChip.jsx'
import { LOW_FREQ_TYPES } from '../utils/deviceTypes.js'
import s from './DeviceMaintenancePanel.module.css'

function formatDuration(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0))
  const days = Math.floor(total / 86400)
  const hours = Math.floor((total % 86400) / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const parts = []
  if (days) parts.push(`${days}天`)
  if (hours) parts.push(`${hours}小时`)
  if (minutes || !parts.length) parts.push(`${minutes}分钟`)
  return parts.join('')
}

// 低频设备（虫情/孢子）精确到小时即可：显示"天+小时"，不足 1 小时退回分钟。
function formatDaysHours(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0))
  const days = Math.floor(total / 86400)
  const hours = Math.floor((total % 86400) / 3600)
  if (days || hours) {
    return `${days ? `${days}天` : ''}${hours}小时`
  }
  return `${Math.floor((total % 3600) / 60)}分钟`
}

function formatRowDuration(seconds, deviceType) {
  return LOW_FREQ_TYPES.has(deviceType) ? formatDaysHours(seconds) : formatDuration(seconds)
}

function formatTime(iso) {
  if (!iso) return '—'
  return dayjs(iso).format('YYYY-MM-DD HH:mm')
}

function defaultRange() {
  return {
    start: dayjs().subtract(30, 'day').format('YYYY-MM-DD'),
    end: dayjs().format('YYYY-MM-DD'),
  }
}

function Kpi({ label, value, accent, hint }) {
  return (
    <div className={s.kpi} style={accent ? { '--accent': accent } : undefined}>
      <span className={s.kpiLabel}>{label}</span>
      <span className={s.kpiValue}>{value}</span>
      {hint ? <span className={s.kpiHint}>{hint}</span> : null}
    </div>
  )
}

export default function DeviceMaintenancePanel({ active = true }) {
  const [devices, setDevices] = useState([])
  const [device, setDevice] = useState('')
  const initial = useMemo(defaultRange, [])
  const [start, setStart] = useState(initial.start)
  const [end, setEnd] = useState(initial.end)
  const [applied, setApplied] = useState({ device: '', start: initial.start, end: initial.end })
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [loaded, setLoaded] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    let alive = true
    api.maintenanceDevices()
      .then((res) => { if (alive) setDevices(res?.data || []) })
      .catch(() => {})
    return () => { alive = false }
  }, [])

  const fetchReport = useCallback((params) => {
    setLoading(true)
    setError('')
    api.maintenanceOutages(params)
      .then((res) => setReport(res?.data || null))
      .catch((err) => setError(err?.message || '加载失败'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (active && !loaded) {
      setLoaded(true)
      fetchReport(applied)
    }
  }, [active, loaded, applied, fetchReport])

  const onQuery = () => {
    if (start && end && start > end) {
      setError('开始日期不能晚于结束日期')
      return
    }
    const next = { device, start, end }
    setApplied(next)
    fetchReport(next)
  }

  const totals = report?.totals
  const rows = report?.rows || []
  const perDevice = report?.per_device || []

  // 程序化下载：避免 <a target="_blank"> 给附件响应开空白页（白屏），并自定义中文文件名。
  const handleExport = async () => {
    setExporting(true)
    setError('')
    try {
      const res = await fetch(maintenanceExportUrl(applied), { credentials: 'include' })
      if (!res.ok) throw new Error(`导出失败（${res.status}）`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `监测平台设备状态运维-${dayjs().format('YYYYMMDDHHmmss')}.xlsx`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err?.message || '导出失败')
    } finally {
      setExporting(false)
    }
  }

  const ongoingKeys = useMemo(
    () => new Set(rows.filter((r) => r.ongoing).map((r) => r.device_key)),
    [rows],
  )

  // 明细表客户端分页
  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize))
  const pageSafe = Math.min(page, totalPages)
  const pagedRows = rows.slice((pageSafe - 1) * pageSize, pageSafe * pageSize)

  useEffect(() => { setPage(1) }, [report, pageSize])

  return (
    <div className={s.panel}>
      <section className={s.filterCard}>
        <div className={s.filters}>
          <label className={s.field}>
            <span>设备</span>
            <DeviceSelect devices={devices} value={device} onChange={setDevice} />
          </label>
          <label className={s.field}>
            <span>时间范围</span>
            <DateRangePicker
              start={start}
              end={end}
              onChange={(nextStart, nextEnd) => { setStart(nextStart); setEnd(nextEnd) }}
            />
          </label>
          <button type="button" className={s.primaryBtn} onClick={onQuery} disabled={loading}>
            {loading ? '查询中…' : '查询'}
          </button>
          <button type="button" className={s.exportBtn} onClick={handleExport} disabled={exporting}>
            <span className={s.exportIcon}>⭳</span> {exporting ? '导出中…' : '导出 Excel'}
          </button>
        </div>
        {error ? <div className={s.error}>{error}</div> : null}
      </section>

      <div className={s.kpis}>
        <Kpi label="监控设备" value={totals ? perDevice.length : '—'} accent="#38bdf8" hint="台" />
        <Kpi
          label="当前掉线"
          value={totals ? ongoingKeys.size : '—'}
          accent={ongoingKeys.size > 0 ? '#f87171' : '#34d399'}
          hint="台 · 仍在异常"
        />
        <Kpi label="近7天异常次数" value={totals ? totals.week_count : '—'} accent="#facc15" hint="次" />
        <Kpi label="近30天异常次数" value={totals ? totals.month_count : '—'} accent="#fb923c" hint="次" />
      </div>

      <section className={s.block}>
        <header className={s.blockHeader}>
          <h3>各设备掉线统计</h3>
          <span className={s.blockSub}>次数 / 累计时长（按设备分列，避免跨设备求和失真）</span>
        </header>
        <div className={s.tableWrap}>
          <table className={s.table}>
            <thead>
              <tr>
                <th>设备</th>
                <th>状态</th>
                <th>近7天次数</th>
                <th>近7天时长</th>
                <th>近30天次数</th>
                <th>近30天时长</th>
                <th>所选范围次数</th>
                <th>所选范围时长</th>
              </tr>
            </thead>
            <tbody>
              {perDevice.length === 0 ? (
                <tr><td className={s.empty} colSpan={8}>{loading ? '加载中…' : '暂无设备数据'}</td></tr>
              ) : perDevice.map((d) => (
                <tr key={d.device_key}>
                  <td className={s.deviceCell}>
                    <TypeChip type={d.device_type} />
                    <span>{d.device_name}</span>
                  </td>
                  <td>
                    <span className={ongoingKeys.has(d.device_key) ? s.ongoing : s.recovered}>
                      {ongoingKeys.has(d.device_key) ? '掉线中' : '正常'}
                    </span>
                  </td>
                  <td className={d.week_count ? s.warnNum : ''}>{d.week_count}</td>
                  <td>{formatRowDuration(d.week_duration_seconds, d.device_type)}</td>
                  <td className={d.month_count ? s.warnNum : ''}>{d.month_count}</td>
                  <td>{formatRowDuration(d.month_duration_seconds, d.device_type)}</td>
                  <td className={d.range_count ? s.warnNum : ''}>{d.range_count}</td>
                  <td>{formatRowDuration(d.range_duration_seconds, d.device_type)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className={s.block}>
        <header className={s.blockHeader}>
          <h3>掉线明细</h3>
          <span className={s.blockSub}>共 {rows.length} 条</span>
        </header>
        <div className={s.tableWrap}>
          <table className={s.table}>
            <thead>
              <tr>
                <th>设备名称</th>
                <th>异常开始时间</th>
                <th>异常结束时间</th>
                <th>持续时长</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr><td className={s.empty} colSpan={5}>{loading ? '加载中…' : '所选范围内暂无异常记录'}</td></tr>
              ) : pagedRows.map((row, idx) => (
                <tr key={`${row.device_key}-${row.start}-${(pageSafe - 1) * pageSize + idx}`}>
                  <td className={s.deviceCell}>
                    <TypeChip type={row.device_type} />
                    <span>{row.device_name}</span>
                  </td>
                  <td>{formatTime(row.start)}</td>
                  <td>{row.ongoing ? '—' : formatTime(row.end)}</td>
                  <td>{formatRowDuration(row.duration_seconds, row.device_type)}</td>
                  <td>
                    <span className={row.ongoing ? s.ongoing : s.recovered}>
                      {row.ongoing ? '仍在异常' : '已恢复'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {rows.length > 0 ? (
          <div className={s.pagination}>
            <label className={s.pageSize}>
              <span>每页</span>
              <select value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))}>
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
              <span>条 · 共 {rows.length} 条</span>
            </label>
            <div className={s.pager}>
              <button type="button" className={s.pageBtn} disabled={pageSafe <= 1} onClick={() => setPage(pageSafe - 1)}>上一页</button>
              <span className={s.pageInfo}>第 {pageSafe} / {totalPages} 页</span>
              <button type="button" className={s.pageBtn} disabled={pageSafe >= totalPages} onClick={() => setPage(pageSafe + 1)}>下一页</button>
            </div>
          </div>
        ) : null}
      </section>

      <p className={s.note}>
        说明：虫情、孢子设备约一天一报，仅识别连续多日掉线，掉线时长精确到小时；水质、雨量、径流为高频上报（约5分钟一条），可精确到分钟。径流站内置雨量计已按物理设备合并，掉线不重复计。
      </p>
    </div>
  )
}
